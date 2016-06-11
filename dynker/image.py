import sys
import os
import glob
import logging
import docker
import hashlib
import yaml
import tarfile
import json
import tempfile
import termcolor

from copy import copy
from cStringIO import StringIO
from filters import Filter
from .dockerfile import Dockerfile

class FileMapFilter(Filter) :
    def __init__(self, *args, **kwds) :
        self.filters = []
        self.withAllFilters(*args, **kwds)
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(self, it) :
        for f in self :
            it = f.filter(it)
        return it

class ExpandFileMapFilter(FileMapFilter) :
    Prio = 20
    AutoFilter = False
    def __init__(self,*args,**kwds) :
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(self, it) :
        for dest, src in it :
            try :
                offset = src.index("*")
                self.logger.debug("glob pattern implies multiple files, destination must be a directory")
            except ValueError :
                srcs = glob.glob(src)
                if srcs :
                    self.logger.debug("found source %s will link it to destination %s", srcs[0], dest)
                    yield dest, srcs[0]
            else :
                for f in glob.iglob(src) :
                    destFile = os.path.join(dest,f[offset:])
                    self.logger.debug("found source %s will link it to destination %s", f, destFile)
                    yield destFile, f

class ExpandDirectoryFilter(FileMapFilter) :
    Prio=10
    def __init__(self,*args,**kwds) :
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(self, it) :
        for dest, src in it :
            if os.path.isdir(src) :
                self.logger.debug("%s is a directory, globbing its content",src)
                for pattern in os.path.join(src,"**"), os.path.join(src,".**") :
                    for path in glob.iglob(pattern) :
                        destFile = os.path.join(dest, os.path.relpath(path,src))
                        self.logger.debug("found source %s will match it to destination %s", path, dest)
                        yield destFile, path
            else :
                self.logger.debug("%s is not a directory, will map %s to %s", src, dest, src)
                yield dest, src

class ResolveSymLink(ExpandFileMapFilter) :
    Prio = 0
    AutoFilter = False
    def __init__(self,*args,**kwds) :
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(it) :
        for dest, src in it :
            while os.path.islink(src) :
                src = os.readlink(src)
            yield dest, src

class ImageBuilder(object) :
    def __init__(self, name, contextPath, dockerfile=None, followSymLinks=False, expandDirectory=False, **kwds) :
        if not dockerfile:
            dockerfile = os.path.join(contextPath, 'Dockerfile')
        self.name = name
        self.dockerfile = dockerfile
        self.dockerfileKwds = kwds
        self.contextPath = contextPath
        self.logger = logging.getLogger(self.__class__.__name__)
        self.followSymLinks = followSymLinks
        self.expandDirectory = expandDirectory

    def expandContextMap(self) :
        fileListFilter = FileMapFilter()
        self.logger.debug("getting content")
        if self.expandDirectory :
            fileListFilter.withFilter(ExpandDirectoryFilter())
        if self.followSymLinks :
            fileListFilter.withFilter(ResolveSymLink())
        def iterContext():
            for arcPattern in self.getDockerfile().listBuildFiles() :
                repoPattern = os.path.join(self.contextPath,arcPattern)
                for repoName in glob.glob(repoPattern) :
                    arcName = os.path.normpath(
                        os.path.relpath(
                            repoName,
                            self.contextPath
                        )
                    )
                    yield (arcName, repoName)
        return dict(fileListFilter.filter(iterContext()))

    def getContext(self):
        gzip = StringIO()
        tar = tarfile.open(fileobj=gzip,mode="w|gz")
        mapping = self.expandContextMap()
        for dest, src in mapping.iteritems() :
            tar.add(src, dest)
        dockerfile = tempfile.TemporaryFile()
        dockerfile.write(str(self.getDockerfile(mapping)))
        dockerfile.seek(0)
        tar.addfile(tar.gettarinfo(arcname="Dockerfile", fileobj=dockerfile), fileobj=dockerfile)
        dockerfile.close()
        tar.close()
        return gzip.getvalue()

    def getDockerfile(self, mapping=None) :
        return Dockerfile(self.dockerfile, **self.dockerfileKwds)

    def deps(self) :
        return self.expandContextMap().values()

    def imageDeps(self) :
        return self.getDockerfile().imageDeps()

    def buildTag(self) :
        h = hashlib.sha1()
        h.update(str(self.getDockerfile()))
        for destination, source in self.expandContextMap():
            h.update(source)
            h.update(os.stat(source).st_mode)
            h.update(file(source).read())
        return h.hexdigest()
    def build(self, client) :
        tag = self.buildTag()
        imageName = "%s:%s"%(self.name, tag)
        try:
            client.inspect_image(imageName)
        except docker.errors.NotFound:
            context = self.getContext()
            self.listenStream(client.build(fileobj=context, custom_context=True, tag=imageName, encoding='gzip'))
        else:
            self.logger.info("image %s already exist, use it rather than rebuilding it", imageName)
    def listenStream(self,stream) :
        head = termcolor.colored('[{name}]:', 'cyan').format(name=self.name)
        for l in  stream:
            try :
                l = json.loads(l)
                if "status" in l :
                    line = '%s\n' % l["status"]
                else :
                    line = l["stream"]
            except KeyError:
                try:
                    raise ValueError(l["errorDetail"]["message"])
                except KeyError:
                    raise RuntimeError("failed to get error message in line %r"%l)
            except UnicodeEncodeError:
                self.logger.error("Failed to decode stream %s",l)
            except ValueError:
                line = l
            sys.stdout.write('{head} {line}'.format(head=head, line=line))

def addImageOptions(parser) :
    parser.add_option("--force-rm", dest="single", action="store_true",
                      help="Always remove intermediate containers, even after unsuccessful builds. The default is false.")
    parser.add_option("--pull", dest="pull", action="store_true",
                      help="Always attempt to pull a newer version of the image. The default is false.")
    parser.add_option("--rm", dest="keep", action="store_false",
                      help="Remove intermediate containers after a successful build. The default is true.")
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true",
                      help="Suppress the verbose output generated by the containers. The default is false.")
