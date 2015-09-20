from filters import *
import logging

class Dockerfile(object) :
    def __init__(self, paths, newTag=None, single=False, optimizeLayers=False):
        self.paths = paths
        self.filter = DockerfileFilter(optimizeLayers=optimizeLayers, keepFirstFrom=single, newTag=newTag)
        self.depsFilter = DockerfileDepExtractor(optimizeLayers=optimizeLayers, keepFirstFrom=single, newTag=newTag)
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

