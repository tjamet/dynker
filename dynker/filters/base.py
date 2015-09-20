__all__ = ["Filter", "ChainFilter"]
import itertools

class Filter(object) :
  Prio = 0
  # TODO: set it to False and reset it to True for subclasses when not provided
  AutoFilter=True

  def _getObjPrio(self,obj) :
    if isinstance(obj,(int,long, float)) :
      return obj
    try :
        return obj.prio
    except AttributeError :
        return getattr(obj, "Prio", float("-inf"))

  def iterFilters(self, withTemplates=False, sort=False) :
    if sort :
      # b, a: reverse order, larger prio first
      for f in sorted(self.iterFilters(withTemplates, False), cmp=lambda b,a:cmp(self._getObjPrio(a),self._getObjPrio(b))) :
        yield f
    else :
        for f in self.filters :
            yield f

  def __init__(self) :
    self.filters = []

  def __iter__(self) :
    return self.iterFilters(withTemplates=False, sort=True)

  def setPrio(self,prio) :
    self.prio = prio

  def withFilter(self,filter) :
    self.filters.append(filter)
    return self

  def filter(*args,**kwds) :
    raise NotImplementedError("Cannot run a filter on the base filter please use Implementation instead")

  def withAllFilters(self, **kwds) :
    for c in self.__class__.__subclasses__() :
        if c.AutoFilter :
            self.withFilter(c(**kwds))

class ChainFilter(Filter) :
    Prio = float("-inf")
    def __init__(self,*iterables) :
        self.iterables = iterables
    def filter(self, it) :
        return itertools.chain(it, *self.iterables)
