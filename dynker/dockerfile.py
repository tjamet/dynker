import sys
from filters import *
import logging

class Dockerfile(object) :
    def __init__(self, paths, single=False, optimizeLayers=False, tagResolver=None, newTag=None):
        if isinstance(paths, (str,unicode)) :
            paths = [paths]
        self.paths = paths
        self.tagResolver = tagResolver if tagResolver is not None else self
        self.single = single
        self.optimizeLayers = optimizeLayers
        self.newTag = newTag
    @property
    def filter(self) :
        return DockerfileFilter(optimizeLayers=self.optimizeLayers, keepFirstFrom=self.single, tagResolver=self.tagResolver)
    @property
    def depsFilter(self) :
        return DockerfileDepExtractor(optimizeLayers=self.optimizeLayers, keepFirstFrom=self.single, tagResolver=self.tagResolver)
    def imageTag(self, imgName) :
        return self.newTag
    def lines(self) :
        for path in self.paths :
            for line in file(path) :
                yield line
    def __str__(self) :
        return "\n".join(self.filter.filter(self.lines()))
    def deps(self) :
        return self.paths + self.listBuildFiles()
    def imageDeps(self) :
        return list( self.depsFilter.filter(self.lines()) )
    def addFilter(self,*filters) :
        for filter in filters :
            self.filter.withFilter(filter)
    def listBuildFiles(self):
        '''Returns the list of files and glob pattern to be added in the build context
        '''
        return list(DockerfileAddExtractor().filter(self.lines()))

def addDockerfileOptions(parser) :
    parser.add_option("-s", "--single", dest="single", action="store_true",
                      help="Filters the Dockerfile FROM directives so that they are concatenated to produce a single image")
    parser.add_option("-o", "--optimize", dest="optimize", action="store_true",
                      help="Conatenate consecutive RUN directives to reduce layer number")

def main(argv=sys.argv) :
    from optparse import OptionParser
    from . import addCommonOptions, commonSetUp
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="files", default=[], action="append",
                      help="Path to the Dockerfile to use. If the path is a relative path then it must be relative to the current directory. The file must be within the build context. The default is Dockerfile.", metavar="FILE")
    parser.add_option("-t", "--tag", dest="tag", default=None,
                      help="Rewrites FROM directives with TAG", metavar="TAG")
    addCommonOptions(parser)
    addDockerfileOptions(parser)
    (options, args) = parser.parse_args(argv[1:])
    commonSetUp(options)
    if not options.files and not args :
        options.files = ["Dockerfile"]
    dockerfile = Dockerfile(options.files + args, single=options.single, optimizeLayers=options.optimize, newTag=options.tag)
    dockerfile.tag = options.tag
    print dockerfile
    print dockerfile.deps()

if __name__ == "__main__" :
    main()
