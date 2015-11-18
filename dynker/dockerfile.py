import sys
from filters import *
from tools import GitHistory
import logging

class Dockerfile(object) :
    def __init__(self, paths, newTag=None, single=False, optimizeLayers=False):
        self.paths = paths
        self.single = single
        self.optimizeLayers = optimizeLayers
        self.newTag = newTag
    @property
    def filter(self) :
        return DockerfileFilter(optimizeLayers=self.optimizeLayers, keepFirstFrom=self.single)
    @property
    def depsFilter(self) :
        return DockerfileDepExtractor(optimizeLayers=self.optimizeLayers, keepFirstFrom=self.single)
    def lines(self) :
        for path in self.paths :
            for line in file(path) :
                yield line
    def __str__(self) :
        return "\n".join(self.filter.filter(self.lines()))
    def deps(self) :
        return self.paths
    def imageDeps(self) :
        return list( self.depsFilter.filter(self.lines()) )
    def addFilter(self,*filters) :
        for filter in filters :
            self.filter.withFilter(filter)
    @property
    def mtime(self) :
        git = GitHistory.Get()
        return max(map(git.getMTime,self.paths))

if __name__ == "__main__" :
    import sys
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-t", "--tag", dest="tag", default=None,
                      help="Rewrites FROM directives with TAG", metavar="TAG")
    parser.add_option("-s", "--single", dest="single", action="store_true",
                      help="Filters the Dockerfile FROM directives so that they are concatenated to produce a single image")
    parser.add_option("-o", "--optimize", dest="optimize", action="store_true",
                      help="Conatenate consecutive RUN directives to reduce layer number")
    parser.add_option("-v","--verbose",
                      dest="verbose", action="store_true",
                      help="switches the debug mode")
    (options, args) = parser.parse_args()
    if options.verbose :
        logging.basicConfig(level=logging.DEBUG)
    else :
        logging.basicConfig(level=logging.INFO)
    dockerfile = Dockerfile(args, newTag = options.tag, single=options.single, optimizeLayers=options.optimize)
    print dockerfile

