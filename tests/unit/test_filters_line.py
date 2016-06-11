import unittest
import sure
import dynker.filters.line

class TestLineFilter(unittest.TestCase):

  def test_noFilter(self):
    self.assertEqual(dynker.filters.line.LineFilter().filter("Hello World"),"Hello World")
    self.assertEqual(list(dynker.filters.line.LineFilter().filter(["Hello"])), ["Hello"])
    self.assertEqual(dynker.filters.line.LineFilter().filter("Hello \nWorld"),"Hello \nWorld")
    self.assertEqual(list(dynker.filters.line.LineFilter().filter(["Hello", "World"])), ["Hello", "World"])
    
  def test_PatternFilterRe(self):
    filter = dynker.filters.line.LineFilter()
    filter.withFilter(dynker.filters.MatchingLineFilter("^World$"))
    self.assertEqual(filter.filter("Hello World"),"")
    self.assertEqual(list(filter.filter(["Hello"])), [])
    self.assertEqual(filter.filter("Hello \nWorld"),"World")
    self.assertEqual(list(filter.filter(["Hello", "World"])), ["World"])
    
    filter = dynker.filters.line.LineFilter()
    filter.withFilter(dynker.filters.NotMatchingLineFilter("^World$"))
    self.assertEqual(filter.filter("Hello World"),"Hello World")
    self.assertEqual(list(filter.filter(["Hello"])), ["Hello"])
    self.assertEqual(filter.filter("Hello \nWorld"),"Hello ")
    self.assertEqual(list(filter.filter(["Hello", "World"])), ["Hello"])
    
  def test_ReplaceLineRe(self):
    filter = dynker.filters.line.LineFilter()
    filter.withFilter(dynker.filters.line.ReplaceLineReFilter("orld"))
    self.assertEqual(filter.filter("Hello World"),"Hello W")
    self.assertEqual(list(filter.filter(["Hello"])), ["Hello"])
    self.assertEqual(filter.filter("Hello \nWorld"),"Hello \nW")
    self.assertEqual(list(filter.filter(["Hello", "World"])), ["Hello", "W"])

    filter = dynker.filters.line.LineFilter()
    filter.withFilter(dynker.filters.line.ReplaceLineReFilter("o(rl)d", sub=lambda match:match.group(1)))
    self.assertEqual(filter.filter("Hello World"),"Hello Wrl")
    self.assertEqual(list(filter.filter(["Hello"])), ["Hello"])
    self.assertEqual(filter.filter("Hello \nWorld"),"Hello \nWrl")
    self.assertEqual(list(filter.filter(["Hello", "World"])), ["Hello", "Wrl"])

    filter = dynker.filters.line.LineFilter()
    filter.withFilter(dynker.filters.line.ReplaceLineReFilter("orld", sub="repl"))
    self.assertEqual(filter.filter("Hello World"),"Hello Wrepl")
    self.assertEqual(list(filter.filter(["Hello"])), ["Hello"])
    self.assertEqual(filter.filter("Hello \nWorld"),"Hello \nWrepl")
    self.assertEqual(list(filter.filter(["Hello", "World"])), ["Hello", "Wrepl"])

  def test_ReplaceLineRePrio(self):
    filter = dynker.filters.line.LineFilter()
    for f in dynker.filters.line.ReplaceLineReFilter("orl", prio = 1), dynker.filters.line.ReplaceLineReFilter("Wd", sub="ok") :
        filter.withFilter(f)
    self.assertEqual(filter.filter("Hello World"), "Hello ok")

    filter = dynker.filters.line.LineFilter()
    for f in dynker.filters.line.ReplaceLineReFilter("orl", prio = 1), dynker.filters.line.ReplaceLineReFilter("Wd", sub="ok", prio=3) :
        filter.withFilter(f)
    self.assertEqual(filter.filter("Hello World"), "Hello Wd")

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
