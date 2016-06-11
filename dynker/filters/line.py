import logging
import re
from .base import Filter
import itertools

class LineFilter(Filter):

  def filter(self,input) :
    tpe = type(input)
    if isinstance(input, (str,unicode)) :
      input = input.splitlines(False)
    it = iter(input)
    for f in self :
      it = f.filter(it)
    if tpe in (str,unicode) :
      return tpe("\n").join(it)
    return it

class PatternMatch(object) :
  def __init__(self,pattern=None, patternRe=None, prio=0, flags=0):
    self.prio = prio
    self.pattern = pattern
    self.patternRe = patternRe if patternRe else re.compile(pattern, flags)
    self.logger = logging.getLogger(self.__class__.__name__)
    super(PatternMatch, self).__init__()

class MatchingLineFilter(PatternMatch, LineFilter) :

  def filter(self, it) :
    return itertools.ifilter(lambda x : bool(self.patternRe.match(x)),it)

class NotMatchingLineFilter(PatternMatch, LineFilter) :

  def filter(self, it) :
    return itertools.ifilterfalse(lambda x : bool(self.patternRe.match(x)),it)

class ReplaceLineReFilter(PatternMatch, LineFilter) :

  def __init__(self, pattern, patternRe=None, sub="", count=0, prio=0) :
    super(ReplaceLineReFilter,self).__init__(pattern, patternRe)
    self.prio = prio
    self.sub = sub
    self.count = count

  def filter(self,it) :
    return itertools.imap(lambda x : self.patternRe.sub(self.sub, x, self.count),it)

class StripLinesFilter(LineFilter) :
    def __init__(self,prio=0) :
        self.prio = prio
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(self, it) :
        return itertools.imap(lambda x : x.strip(), it)
