import logging
from .base import Filter
from .line import *

__all__ = [ "DockerfileFilter", "DockerfileDepExtractor" ]

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

class DockerfileFromFilter(PatternMatch, LineFilter) :
    Prio = 20

    def __init__(self, newTag=None, keepFirst=False, prio=None) :
        super(DockerfileFromFilter,self).__init__("^(FROM[\s]*([^:]*))(:(.*)|)$")
        if prio :
            self.prio = prio
        self.newTag = newTag
        self.keepFirst = keepFirst

    def getLine(self, match, line) :
        if match :
            if self.newTag :
                line = "%s:%s"%(match.group(1), self.newTag)
            else:
                line = "%s%s"%(match.group(1), match.group(3),)
        return line

    def filter(self, it) :
        dumpFROM = True
        for line in it :
            match = self.patternRe.match(line)
            logging.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if dumpFROM :
                line = self.getLine(match, line)
            else :
                line = None
            if line :
                logging.debug("Producing output line %r", line)
                yield line
            else :
                logging.debug("No line to be produced")

class DockerfileDepExtractorFilter(DockerfileFromFilter) :
    def __init__(self, prio=float("-inf"), **kwds) :
        return super(DockerfileDepExtractorFilter, self).__init__(prio=prio, **kwds)
    def getLine(self, match, line) :
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

class DockerfileFilter(LineFilter, Filter) :
    #simply declare the root class
    def __init__(self, optimizeLayers=False, keepFirstFrom=False, newTag=None, **args) :
        super(DockerfileFilter, self).__init__()
        self.withFilter(StripLinesFilter())
        self.withFilter(NotMatchingLineFilter("^(#.*|[\s]*)$", prio = 9))
        self.withFilter(ReplaceLineReFilter(r"(.*[^\\])#.*", prio = 8))
        if optimizeLayers :
            self.withFilter(DockerfileOptLayers())
        self.withFilter(DockerfileOptApt())
        self.withFilter(DockerfileOptYum())
        self.withFilter(DockerfileFromFilter(newTag, keepFirst=keepFirstFrom))
        # add all userdefined filters
        self.withAllFilters(optimizeLayers=optimizeLayers, keepFirstFrom=keepFirstFrom, newTag=newTag, **args)

class DockerfileDepExtractor(DockerfileFilter) :
    AutoFilter=False
    def __init__(self, keepFirstFrom=False, **kwds) :
        super(DockerfileDepExtractor, self).__init__(**kwds)
        self.withFilter(DockerfileDepExtractorFilter(keepFirst=keepFirstFrom))
