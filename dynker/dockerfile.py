from filters import *
import logging

class DockerfileOptLayers(PatternMatch, LineFilter) :
    Prio = -10

    def __init__(self, prio=0) :
        super(DockerfileOptLayers,self).__init__("^RUN[\s](.*)")
        self.prio = prio

    def filter(self, it) :
        curLine = ""
        sep = "RUN "
        for line in it :
            match = self.patternRe.match(line)
            logging.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if match :
                curLine+= sep+match.group(1)
                sep = " && "
            else :
                if curLine :
                    logging.debug("Producing output line %r", curLine)
                    yield curLine
                curLine = ""
                sep = "RUN "
                logging.debug("Producing output line %r", line)
                yield line
        if curLine :
            logging.debug("Producing output line %r", curLine)
            yield curLine
                    
class DockerfileOptYum(PatternMatch, LineFilter) :
    Prio = -20

    def __init__(self, prio=0) :
        super(DockerfileOptYum,self).__init__("^RUN[\s](.*yum.*install.*)")
        self.prio = prio

    def filter(self, it) :
        for line in it :
            match = self.patternRe.match(line)
            logging.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if match :
                line = "RUN touch /var/lib/rpm/* && %s && yum clean all"%match.group(1)
            logging.debug("Producing output line %r", line)
            yield line
                    
class DockerfileOptApt(PatternMatch, LineFilter) :
    Prio = -20

    def __init__(self, prio=0) :
        super(DockerfileOptApt,self).__init__("^RUN[\s](.*apt-get.*install.*)")
        self.prio = prio

    def filter(self, it) :
        for line in it :
            match = self.patternRe.match(line)
            logging.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if match :
                line = "RUN apt-get update && %s && apt-get clean"%match.group(1)
            logging.debug("Producing output line %r", line)
            yield line

class DockerfileFrom(PatternMatch, LineFilter) :
    Prio = 20

    def __init__(self, newTag=None, keepFirst=False, prio=0, depsOnly=False) :
        super(DockerfileFrom,self).__init__("^(FROM[\s]*([^:]*))(:(.*)|)$")
        self.prio = prio
        self.newTag = newTag
        self.keepFirst = keepFirst
        self.depsOnly = depsOnly

    def filter(self, it) :
        dumpFROM = True
        for line in it :
            match = self.patternRe.match(line)
            logging.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if self.depsOnly :
                def getLine(match, line) :
                    if match :
                        image = match.group(2)
                        image = image.strip()
                        if self.newTag :
                            tag = self.newTag
                        else :
                            tag = match.group(4)
                            if isinstance(tag,(str,unicode)) :
                                tag = tag.strip()
                        return image, tag
                    return None
            else :
                def getLine(match, line) :
                    if match :
                        if self.newTag :
                            line = "%s:%s"%(match.group(1), self.newTag)
                        else:
                            line = "%s%s"%(match.group(1), match.group(3),)
                    return line
                    
            if dumpFROM :
                line = getLine(match, line)
            else :
                line = None
            if line :
                logging.debug("Producing output line %r", line)
                yield line
            else :
                logging.debug("No line to be produced")

class Dockerfile(object) :
    def __init__(self, paths, newTag=None, single=False, optimizeLayers=False):
        self.paths = paths
        self.filter = LineFilter()
        self.filter.withFilter(StripLinesFilter())
        self.filter.withFilter(NotMatchingLineFilter("^(#.*|[\s]*)$", prio = 9))
        self.filter.withFilter(ReplaceLineReFilter(r"(.*[^\\])#.*", prio = 8))
        self.filter.withFilter(DockerfileFrom(newTag, keepFirst=single))
        if optimizeLayers :
            self.filter.withFilter(DockerfileOptLayers())
        self.filter.withFilter(DockerfileOptApt())
        self.filter.withFilter(DockerfileOptYum())
        self.depsFilter = LineFilter()
        self.depsFilter = DockerfileFrom(newTag, keepFirst=single, depsOnly=True)
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

