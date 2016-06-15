import itertools
import logging
import six
__all__ = ["Filter", "ChainFilter"]


def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

class Filter(object) :
  Prio = 0
  # TODO: set it to False and reset it to True for subclasses when not provided
  AutoFilter=True

  def _getObjPrio(self,obj) :
    if isinstance(obj, six.integer_types) or isinstance(obj, float):
      return obj
    try :
        return obj.prio
    except AttributeError :
        return getattr(obj, "Prio", float("-inf"))

  def iterFilters(self, withTemplates=False, sort=False) :
    if sort :
      # b, a: reverse order, larger prio first
      for f in sorted(
        self.iterFilters(withTemplates, False),
        key=lambda x:self._getObjPrio(x),
        reverse=True
      ) :
        yield f
    else :
        for f in self.filters :
            yield f

  def __init__(self) :
    self.filters = []
    self.logger = logging.getLogger(self.__class__.__name__)

  def __iter__(self) :
    return self.iterFilters(withTemplates=False, sort=True)

  def withFilter(self,filter) :
    self.filters.append(filter)
    return self

  def filter(*args,**kwds) :
    raise NotImplementedError("Cannot run a filter on the base filter please use Implementation instead")

  def withAllFilters(self, *args, **kwds) :
    def addFilters(cls) :
        for c in cls.__subclasses__() :
            if c.AutoFilter :
                self.withFilter(c(*args, **kwds))
            addFilters(c)
    addFilters(self.__class__)

class ChainFilter(Filter) :
    Prio = float("-inf")
    def __init__(self,*iterables) :
        self.iterables = iterables
    def filter(self, it) :
        return itertools.chain(it, *self.iterables)
