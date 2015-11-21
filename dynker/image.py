import sys
import os
import glob
from filters import Filter
from tools import GitHistory
import logging
import docker
import yaml
import tarfile
import json
from cStringIO import StringIO
import tempfile

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
    def __init__(self, name, dockerfile=None, contextMap={}) :
        self.name = name
        self.dockerfile = dockerfile
        self.contextMap = contextMap
        self.logger = logging.getLogger(self.__class__.__name__)
    def getContext(self, followSymLinks=False, restoreMTime=False):
        fileListFilter = FileMapFilter()
        self.logger.debug("getting content")
        if restoreMTime :
            fileListFilter.withFilter(ExpandDirectoryFilter())
        if followSymLinks :
            fileListFilter.withFilter(ResolveSymLink())
        gzip = StringIO()
        tar = tarfile.open(fileobj=gzip,mode="w|gz")
        if restoreMTime:
            def add(name, arcname, recursive=True) :
                tarinfo = tar.gettarinfo(name, arcname)
                #TODO: restore git mtime
                if tarinfo.isreg():
                    f = open(name, "rb")
                    tarinfo.mtime = GitHistory.Get().getMTime(name)
                    self.logger.debug("Added file %s=>%s (mtime=%f) to context", name, tarinfo.name, tarinfo.mtime)
                    tar.addfile(tarinfo, f)
                    f.close()
                elif tarinfo.isdir():
                    tar.addfile(tarinfo)
                    if recursive:
                        for f in os.listdir(name):
                            add(os.path.join(name, f), os.path.join(arcname, f), recursive)
                else:
                    tar.addfile(tarinfo)
        else :
            def add(src, dest) :
                tar.add(src, dest)
        for dest, src in fileListFilter.filter(self.contextMap.iteritems()) :
            add(src, dest)
        if self.dockerfile :
            dockerfile = tempfile.TemporaryFile()
            dockerfile.write(str(self.dockerfile))
            dockerfile.seek(0)
            tar.addfile(tar.gettarinfo(arcname="Dockerfile", fileobj=dockerfile), fileobj=dockerfile)
            dockerfile.close()
        tar.close()
        return gzip.getvalue()

    def deps(self, followSymLinks=False, restoreMTime=False) :
        fileListFilter = FileMapFilter()
        self.logger.debug("getting image build depencencies")
        if restoreMTime :
            fileListFilter.withFilter(ExpandDirectoryFilter())
        if followSymLinks :
            fileListFilter.withFilter(ResolveSymLink())
        deps = []
        if self.dockerfile :
            deps+= self.dockerfile.deps()
        deps+= map(lambda x:x[1], fileListFilter.filter(self.contextMap.iteritems()))
        return deps
    def imageDeps(self) :
        if self.dockerfile :
            return self.dockerfile.imageDeps()
        return []

    def buildTag(self, followSymLinks=False, restoreMTime=False) :
        deps = self.deps(followSymLinks=followSymLinks, restoreMTime=restoreMTime)
        self.logger.debug("Resolved dependencies %r for %s"%(deps,self.name))
        tag = GitHistory.Get().getLastCommit(*deps, strict=False)
        if tag is None :
            tag = 'latest'
        elif GitHistory.Get().isDirty(*deps) :
            tag+= "-dirty"
        self.logger.debug("Resolved build tag: %s"%tag)
        return tag
    def build(self, client, followSymLinks=False, restoreMTime=False, **kwds) :
        context = self.getContext(followSymLinks=followSymLinks, restoreMTime=restoreMTime)
        tag = self.buildTag()
        if tag is None :
            tag = 'latest'
        imageName = "%s:%s"%(self.name, tag)
        self.listenStream(client.build(fileobj=context, custom_context=True, tag=imageName, encoding='gzip'))
    def listenStream(self,stream) :
        for l in  stream:
            try :
                l = json.loads(l)
                if "status" in l :
                    print l["status"]
                else :
                    print l["stream"],
            except KeyError:
                try:
                    raise ValueError(l["errorDetail"]["message"])
                except KeyError:
                    raise RuntimeError("failed to get error message in line %r"%l)
            except UnicodeEncodeError:
                self.logger.error("Failed to decode stream %s",l)
            except ValueError:
                print l,
