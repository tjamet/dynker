import itertools
import logging
import re
import six

from .base import Filter

class LineFilter(Filter):

  def remove_nones(self, it):
    for line in it:
      if line is not None:
        yield line

  def filter(self,input, restore_type=False) :
    if isinstance(input, six.string_types) :
      lines = input.splitlines(False)
    else:
      lines = input
    it = iter(lines)
    for f in self :
      it = f.filter(it)
    it = self.remove_nones(it)
    if restore_type and isinstance(input, six.string_types) :
      return type(input)("\n").join(it)
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
    if six.PY3:
      f = filter
    else:
      f = itertools.ifilter
    return f(lambda x : bool(self.patternRe.match(x)),it)

class NotMatchingLineFilter(PatternMatch, LineFilter) :

  def filter(self, it) :
    if six.PY3:
      f = itertools.filterfalse
    else:
      f = itertools.ifilterfalse
    return f(lambda x : bool(self.patternRe.match(x)),it)

class ReplaceLineReFilter(PatternMatch, LineFilter) :

  def __init__(self, pattern, patternRe=None, sub="", count=0, prio=0) :
    super(ReplaceLineReFilter,self).__init__(pattern, patternRe)
    self.prio = prio
    self.sub = sub
    self.count = count

  def filter(self,it) :
    if six.PY3:
      f = map
    else:
      f = itertools.imap
    return f(lambda x : self.patternRe.sub(self.sub, x, self.count),it)

class StripLinesFilter(LineFilter) :
    def __init__(self,prio=0) :
        self.prio = prio
        self.logger = logging.getLogger(self.__class__.__name__)
    def filter(self, it) :
        if six.PY3:
          f = map
        else:
          f = itertools.imap
        return f(lambda x : x.strip(), it)
