import logging
from .base import Filter
from .line import *

__all__ = [ "DockerfileFilter", "DockerfileDepExtractor", "DockerfileAddExtractor" ]

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
            self.logger.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if match :
                curLine+= sep+match.group(1)
                sep = " && "
            else :
                if curLine :
                    self.logger.debug("Producing output line %r", curLine)
                    yield curLine
                curLine = ""
                sep = "RUN "
                self.logger.debug("Producing output line %r", line)
                yield line
        if curLine :
            self.logger.debug("Producing output line %r", curLine)
            yield curLine
                    
class DockerfileOptYum(PatternMatch, LineFilter) :
    Prio = -20

    def __init__(self, prio=0) :
        super(DockerfileOptYum,self).__init__("^RUN[\s](.*yum.*install.*)")
        self.prio = prio

    def filter(self, it) :
        for line in it :
            match = self.patternRe.match(line)
            self.logger.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if match :
                line = "RUN touch /var/lib/rpm/* && %s && yum clean all"%match.group(1)
            self.logger.debug("Producing output line %r", line)
            yield line
                    
class DockerfileOptApt(PatternMatch, LineFilter) :
    Prio = -20

    def __init__(self, prio=0) :
        super(DockerfileOptApt,self).__init__("^RUN[\s](.*apt-get.*install.*)")
        self.prio = prio

    def filter(self, it) :
        for line in it :
            match = self.patternRe.match(line)
            self.logger.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            if match :
                line = "RUN apt-get update && %s && apt-get clean"%match.group(1)
            self.logger.debug("Producing output line %r", line)
            yield line

class DockerfileFromFilter(PatternMatch, LineFilter) :
    Prio = 20

    def __init__(self, keepFirst=False, prio=None, tagResolver=None) :
        super(DockerfileFromFilter, self).__init__('from[\s]{1,}([^\s:]{1,})(?::([^\s]{1,})|)', flags=re.IGNORECASE)
        if prio :
            self.prio = prio
        self.keepFirst = keepFirst
        self.tagResolver = tagResolver

    def getImageTag(self, image, tag) :
        if self.tagResolver :
            newTag = self.tagResolver.imageTag(image)
        else :
            newTag = None
        if newTag :
            return (image, newTag)
        else:
            return (image, tag)

    def getLine(self, match, line) :
        if match :
            if not self.dumpFROM :
                return None
            image, tag = self.getImageTag(match.group(2), match.group(4))
            line = "FROM %s%s"%(image, ":%s"%tag if tag else "")
            self.logger.debug("line: %s, keep first : %r", line, self.keepFirst)
            if self.keepFirst :
                self.dumpFROM = False
        return line

    def filter(self, it) :
        self.dumpFROM = True
        for line in it :
            match = self.patternRe.match(line)
            self.logger.debug("Filtering line %r, pattern matched: %r", line, match is not None)
            line = self.getLine(match, line)
            if line :
                self.logger.debug("Producing output line %r", line)
                yield line
            else :
                self.logger.debug("No line to be produced")

class DockerfileDepExtractorFilter(DockerfileFromFilter) :
    def __init__(self, prio=float("-inf"), **kwds) :
        return super(DockerfileDepExtractorFilter, self).__init__(prio=prio, **kwds)
    def getLine(self, match, line) :
        if match :
            image, tag = self.getImageTag(match.group(2), match.group(4))
            return image
        return None

class DockerfileAddExtractorFilter(PatternMatch, LineFilter):
    def __init__(self, prio=float("-inf"), **kwds):
        return super('add[\s]{1,}([^\s]{1,})[\s]{1,}([^\s]{1,})', re.IGNORECASE, **kwds)
    def getLine(self, match, line) :
        if match :
            return match.group(1)
        return None

class DockerfileFilter(LineFilter, Filter) :
    #simply declare the root class
    def __init__(self, optimizeLayers=False, keepFirstFrom=False, tagResolver=None, **args) :
        super(DockerfileFilter, self).__init__()
        self.withFilter(StripLinesFilter())
        self.withFilter(NotMatchingLineFilter("^(#.*|[\s]*)$", prio = 9))
        self.withFilter(ReplaceLineReFilter(r"(.*[^\\])#.*", prio = 8))
        if optimizeLayers :
            self.withFilter(DockerfileOptLayers())
        self.withFilter(DockerfileOptApt())
        self.withFilter(DockerfileOptYum())
        self.withFilter(DockerfileFromFilter(tagResolver=tagResolver, keepFirst=keepFirstFrom))
        # add all userdefined filters
        self.withAllFilters(optimizeLayers=optimizeLayers, keepFirstFrom=keepFirstFrom, tagResolver=tagResolver, **args)

class DockerfileDepExtractor(DockerfileFilter) :
    AutoFilter=False
    def __init__(self, keepFirstFrom=False, **kwds) :
        super(DockerfileDepExtractor, self).__init__(**kwds)
        self.withFilter(DockerfileDepExtractorFilter(keepFirst=keepFirstFrom))
