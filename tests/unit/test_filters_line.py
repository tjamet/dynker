import unittest
import sure
import six
import dynker.filters.line

def factoryFilter(c, *args, **kwds):
    class TestFilter(c):
        def filter(self, *args, **kwds):
            r = c.filter(self, *args, **kwds)
            if isinstance(r, six.string_types):
                return r
            if isinstance(r, (list, tuple)):
                return r
            return list(r)
    return TestFilter(*args, **kwds)

class TestLineFilter(unittest.TestCase):

  def test_noFilter(self):
    filter = factoryFilter(dynker.filters.line.LineFilter)
    filter.filter.when.called_with("Hello World").should.return_value(["Hello World"])
    filter.filter.when.called_with("Hello World", restore_type=True).should.return_value("Hello World")
    filter.filter.when.called_with(["Hello \nWorld"]).should.return_value(["Hello \nWorld"])
    filter.filter.when.called_with("Hello \nWorld", restore_type=True).should.return_value("Hello \nWorld")
    filter.filter.when.called_with("Hello \nWorld").should.return_value(["Hello ", "World"])
    filter.filter.when.called_with(["Hello", "World"]).should.return_value(["Hello", "World"])
    filter.filter.when.called_with(["Hello", None, "World"]).should.return_value(["Hello", "World"])
    
  def test_PatternFilterRe(self):
    filter = factoryFilter(dynker.filters.line.LineFilter)
    filter.withFilter(dynker.filters.MatchingLineFilter("^World$"))
    filter.filter.when.called_with("Hello World").should.return_value([])
    filter.filter.when.called_with(["Hello", "World"]).should.return_value(["World"])
    
    filter = factoryFilter(dynker.filters.line.LineFilter)
    filter.withFilter(dynker.filters.NotMatchingLineFilter("^World$"))
    filter.filter.when.called_with("Hello World").should.return_value(["Hello World"])
    filter.filter.when.called_with(["Hello", "World"]).should.return_value(["Hello"])
    
  def test_ReplaceLineRe(self):
    filter = factoryFilter(dynker.filters.line.LineFilter)
    filter.withFilter(dynker.filters.line.ReplaceLineReFilter("orld"))
    filter.filter.when.called_with("Hello World").should.return_value(["Hello W"])
    filter.filter.when.called_with("Hello Wor").should.return_value(["Hello Wor"])
    filter.filter.when.called_with(["Hello", "World"]).should.return_value(["Hello", "W"])

    filter = factoryFilter(dynker.filters.line.LineFilter)
    filter.withFilter(dynker.filters.line.ReplaceLineReFilter("o(rl)d", sub=lambda match:match.group(1)))
    filter.filter.when.called_with(['Hello', 'World']).should.return_value(['Hello', 'Wrl'])

    filter = factoryFilter(dynker.filters.line.LineFilter)
    filter.withFilter(dynker.filters.line.ReplaceLineReFilter("orld", sub="repl"))
    filter.filter.when.called_with(['Hello', 'World']).should.return_value(['Hello', 'Wrepl'])

  def test_ReplaceLineRePrio(self):
    filter = factoryFilter(dynker.filters.line.LineFilter)
    for f in dynker.filters.line.ReplaceLineReFilter("orl", prio = 1), dynker.filters.line.ReplaceLineReFilter("Wd", sub="ok") :
        filter.withFilter(f)
    filter.filter.when.called_with("Hello World").should.return_value(["Hello ok"])

    filter = factoryFilter(dynker.filters.line.LineFilter)
    for f in dynker.filters.line.ReplaceLineReFilter("orl", prio = 1), dynker.filters.line.ReplaceLineReFilter("Wd", sub="ok", prio=3) :
        filter.withFilter(f)
    filter.filter.when.called_with("Hello World").should.return_value(["Hello Wd"])

class TestStripLinesFilter(unittest.TestCase):
    def test_filter_lines_are_stripped(self):
        filter = dynker.filters.line.StripLinesFilter()
        list(filter.filter([
            " a line with trailing whitespaces should be stripped        ",
            "\t a line with trailing tabs should be stripped  \t\t   ",
        ])).should.be.eql([
            "a line with trailing whitespaces should be stripped",
            "a line with trailing tabs should be stripped",
        ])

if __name__ == '__main__':
    unittest.main()
