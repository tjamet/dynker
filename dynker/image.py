import os
import glob
from filters import Filter
from tools import GitMTime
import logging
import docker
import yaml
import tarfile
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
                    tarinfo.mtime = GitMTime.Get().getMTime(name)
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
