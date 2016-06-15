import glob
import logging
import os
import six
import sys

from . import Filter

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
                    destFile = dest + f[offset:]
                    self.logger.debug("found source %s will link it to destination %s", f, destFile)
                    yield destFile, f

class ExpandDirectoryFilter(FileMapFilter) :
    Prio=10
    AutoFilter = False
    def __init__(self,*args,**kwds) :
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(self, it) :
        for dest, src in it :
            if os.path.isdir(src) :
                self.logger.debug("%s is a directory, globbing its content",src)
                for root, dirs, files in os.walk(src):
                    for f in files:
                        path = os.path.join(root, f)
                        destFile = os.path.join(dest, os.path.relpath(path, src))
                        yield destFile, path
            else :
                self.logger.debug("%s is not a directory, will map %s to %s", src, dest, src)
                yield dest, src

class ResolveSymLink(ExpandFileMapFilter) :
    Prio = 0
    AutoFilter = False
    def __init__(self,*args,**kwds) :
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(self, it) :
        for dest, src in it :
            while os.path.islink(src) :
                src = os.readlink(src)
            yield dest, src
