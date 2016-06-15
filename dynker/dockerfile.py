import dynker.filters
import logging
import six
import sys

class Dockerfile(object) :
    def __init__(self, paths, single=False, optimizeLayers=False, tagResolver=None, newTag=None):
        if isinstance(paths, six.string_types) :
            paths = [paths]
        self.paths = paths
        self.tagResolver = tagResolver if tagResolver is not None else self
        self.single = single
        self.optimizeLayers = optimizeLayers
        self.newTag = newTag
    @property
    def filter(self) :
        return dynker.filters.DockerfileFilter(optimizeLayers=self.optimizeLayers, keepFirstFrom=self.single, tagResolver=self.tagResolver)
    @property
    def depsFilter(self) :
        return dynker.filters.DockerfileDepExtractor(optimizeLayers=self.optimizeLayers, keepFirstFrom=self.single)
    def imageTag(self, imgName) :
        return self.newTag
    def lines(self) :
        for path in self.paths :
            for line in open(path) :
                yield line
    def __str__(self) :
        return "\n".join(self.filter.filter(self.lines()))
    def deps(self) :
        return self.paths + self.listBuildFiles()
    def imageDeps(self) :
        return list( self.depsFilter.filter(self.lines()) )
    def listBuildFiles(self):
        '''Returns the list of files and glob pattern to be added in the build context
        '''
        return list(dynker.filters.DockerfileAddExtractor().filter(self.lines()))

def addDockerfileOptions(parser) :
    parser.add_argument("-s", "--single", dest="single", action="store_true",
        help="Filters the Dockerfile FROM directives so that they are concatenated to produce a single image")
    parser.add_argument("-o", "--optimize", dest="optimize", action="store_true",
                      help="Conatenate consecutive RUN directives to reduce layer number")
def add_options(parser):
    from . import addCommonOptions
    parser.add_argument("file", default=[], nargs="*",
                      help="Path to the Dockerfile to use. If the path is a relative path then it must be relative to the current directory. The file must be within the build context. The default is Dockerfile.", metavar="FILE")
    parser.add_argument("-f", "--file", dest="files", default=[], action="append",
                      help="Path to the Dockerfile to use. If the path is a relative path then it must be relative to the current directory. The file must be within the build context. The default is Dockerfile.", metavar="FILE")
    parser.add_argument("-t", "--tag", dest="tag", default=None,
                      help="Rewrites FROM directives with TAG", metavar="TAG")
    addCommonOptions(parser)
    addDockerfileOptions(parser)

def main(argv=sys.argv, args=None) :
    from . import commonSetUp
    if not args:
        import argparse
        parser = argparse.ArgumentParser()
        add_options(parser)
        args = parser.parse_args(argv[1:])
    commonSetUp(args)
    files = args.files + args.file
    if not files :
        files = ["Dockerfile"]
    dockerfile = Dockerfile(files, single=args.single, optimizeLayers=args.optimize, newTag=args.tag)
    dockerfile.tag = args.tag
    sys.stdout.write(str(dockerfile))
    sys.stdout.write('\n')
