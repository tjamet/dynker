import unittest

class TestBaseFilter(unittest.TestCase):

  def setUp(self) :
    import dynker.filters.base
    dynker.filters.base = reload(dynker.filters.base)
    self.module = dynker.filters.base

  def test_import(self) :
    self.assertEqual(self.module.__all__, ["Filter", "ChainFilter"])

  def test_sorting(self) :
    class MyFilter(self.module.Filter):
      Prio = 10
    class Other(object) :
      pass
    other = Other()
    self.assertEqual(MyFilter()._getObjPrio(other),float("-inf"))
    for p in 10, long(199), float(100) :
        other.Prio = p
        self.assertEqual(MyFilter()._getObjPrio(other),p)
    a = MyFilter()
    b = MyFilter()
    a.prio = 1
    b.prio = 10
    m = self.module.Filter()
    m.withFilter(a).withFilter(b)
    self.assertEqual(list(iter(m)),[b,a])

  def test_filterRaises(self) :
    with self.assertRaises(NotImplementedError) :
      self.module.Filter().filter()

class TestChainFilter(unittest.TestCase) :

  def setUp(self) :
    import dynker.filters.base
    dynker.filters.base = reload(dynker.filters.base)
    self.module = dynker.filters.base

  def testChainFilter(self) :
    myFilter = self.module.ChainFilter(["d","e"], ["f","g","h"])
    self.assertEqual(["a","b","c","d","e","f","g","h"], list(myFilter.filter(["a","b","c"])))

if __name__ == '__main__':
    unittest.main()
