import collections
import docker
import hashlib
import glob
import json
import logging
import os
import six
import sys
import tarfile
import tempfile
import termcolor
import yaml

from copy import copy
from .filters.file import ResolveSymLink, ExpandDirectoryFilter, FileMapFilter, ExpandFileMapFilter
from .dockerfile import Dockerfile

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
        fileListFilter.withFilter(ExpandFileMapFilter())
        fileListFilter.withFilter(ExpandDirectoryFilter())
        if self.followSymLinks :
            fileListFilter.withFilter(ResolveSymLink())
        def iterContext():
            for arcPattern in self.getDockerfile().listBuildFiles() :
                repoPattern = os.path.join(self.contextPath,arcPattern)
                yield arcPattern, repoPattern
        return collections.OrderedDict(fileListFilter.filter(iterContext()))

    def getContext(self):
        gzip = six.BytesIO()
        tar = tarfile.open(fileobj=gzip,mode="w|gz")
        mapping = self.expandContextMap()
        for dest, src in six.iteritems(mapping) :
            tar.add(src, dest)
        dockerfile = tempfile.NamedTemporaryFile()
        self.getDockerfile().write(dockerfile)
        dockerfile.seek(0)
        tar.addfile(tar.gettarinfo(arcname="Dockerfile", fileobj=dockerfile), fileobj=dockerfile)
        dockerfile.close()
        tar.close()
        return gzip.getvalue()

    def getDockerfile(self) :
        return Dockerfile(self.dockerfile, **self.dockerfileKwds)

    def deps(self) :
        return self.expandContextMap().values()

    def imageDeps(self) :
        return self.getDockerfile().imageDeps()

    def buildTag(self) :
        h = hashlib.sha1()
        h.update(str(self.getDockerfile()).encode('utf-8'))
        mapping = self.expandContextMap()
        for destination, source in six.iteritems(mapping):
            h.update(destination.encode('utf-8'))
            # the important bits are permissions
            # and set uid bits. The others are less useful
            permissions = int(os.stat(source).st_mode & 0o6777)
            h.update(repr(permissions).encode('utf-8'))
            h.update(open(source, 'rb').read())
        return h.hexdigest()
    def build(self, client, out_fd=sys.stdout) :
        tag = self.buildTag()
        imageName = "%s:%s"%(self.name, tag)
        try:
            client.inspect_image(imageName)
        except docker.errors.NotFound:
            context = self.getContext()
            self.listenStream(client.build(fileobj=context, custom_context=True, tag=imageName, encoding='gzip'), fd=out_fd)
        else:
            self.logger.info("image %s already exist, use it rather than rebuilding it", imageName)
    def tag(self, client, tags, registries=[], force=True):
        if not isinstance(tags, (list, tuple)):
            tags = [tags]
        buildTag = self.buildTag()
        tags = [buildTag] + tags
        for registry in [None]+registries:
            for tag in tags:
                image_name = self.name
                if registry:
                    image_name = '%s/%s' % (registry, image_name)
                if self.name!=image_name or buildTag !=tag:
                    self.logger.info('tagging image %s:%s to %s:%s', self.name, buildTag, image_name, tag)
                    if not client.tag('%s:%s' % (self.name, buildTag), image_name, tag, force=force):
                        raise RuntimeError("Failed to tag image %s" % image_name)
    def listenStream(self,stream, fd=sys.stdout) :
        head = termcolor.colored('[{name}]:', 'cyan').format(name=self.name)
        for l in  stream:
            try :
                l = json.loads(str(l))
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
            fd.write('{head} {line}'.format(head=head, line=line))

def addImageOptions(parser) :
    parser.add_argument("--force-rm", dest="single", action="store_true",
                      help="Always remove intermediate containers, even after unsuccessful builds. The default is false.")
    parser.add_argument("--pull", dest="pull", action="store_true",
                      help="Always attempt to pull a newer version of the image. The default is false.")
    parser.add_argument("--rm", dest="keep", action="store_false",
                      help="Remove intermediate containers after a successful build. The default is true.")
    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true",
                      help="Suppress the verbose output generated by the containers. The default is false.")
