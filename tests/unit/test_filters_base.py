import dynker.filters.base
import faker
import os
import random
import six
import sure
import unittest
import yaml

from .. import mock

class TestFilter(unittest.TestCase):

    def setUp(self):
        self.faker = faker.Faker()
        self.module = dynker.filters.base

    def test_obj_prio(self):
        obj = object()

        filter = dynker.filters.base.Filter()
        for prio in [
            self.faker.pyint(),
            self.faker.pyfloat(),
        ]:
            filter._getObjPrio.when.called_with(prio).should.return_value(prio)
        filter._getObjPrio.when.called_with(obj).should.return_value(float('-inf'))

    def test_import(self) :
        self.assertEqual(self.module.__all__, ["Filter", "ChainFilter"])

    def test_sorting(self) :
        class MyFilter(self.module.Filter):
          Prio = 10
        class Other(object) :
          pass
        other = Other()
        self.assertEqual(MyFilter()._getObjPrio(other),float("-inf"))
        for p in 10, float(100) :
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

    def test_withallfilters_adds_all_subsubclasses(self):
        class TopFilter(self.module.Filter):
            instances = []
            def __init__(self, *args, **kwds):
                self.instances.append((self, args, kwds))
                super(TopFilter, self).__init__()

        class MyBaseFilter(TopFilter):
            instances = []
        class MySecondFilter(MyBaseFilter):
            instances = []
        class MyThirdFilter(MyBaseFilter):
            instances = []
            AutoFilter = False
        class MyFourthFilter(MyThirdFilter):
            instances = []
        class MyFifthFilter(MyThirdFilter):
            AutoFilter = True
            instances = []

        for args, kwds in [((),{}), ((object(),), {}), ((), {'key': object()})]:
            filter = TopFilter()
            filter.withAllFilters(*args, **kwds)

            MyBaseFilter.instances.should.have.length_of(1)
            MySecondFilter.instances.should.have.length_of(1)
            MyThirdFilter.instances.should.have.length_of(0)
            MyFourthFilter.instances.should.have.length_of(0)
            MyFifthFilter.instances.should.have.length_of(1)

            for c in (MyBaseFilter, MySecondFilter, MyFifthFilter):
                (args, kwds).should.be.eql(c.instances[0][1:])
                filter.filters.should.contain(c.instances[0][0])

            MyBaseFilter.instances.pop()
            MySecondFilter.instances.pop()
            MyFifthFilter.instances.pop()

class TestChainFilter(unittest.TestCase) :

    def setUp(self) :
        self.module = dynker.filters.base

    def testChainFilter(self) :
        myFilter = self.module.ChainFilter(["d","e"], ["f","g","h"])
        self.assertEqual(["a","b","c","d","e","f","g","h"], list(myFilter.filter(["a","b","c"])))

if __name__ == '__main__':
    unittest.main()
