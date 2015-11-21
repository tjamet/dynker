import os, sys
import re
from itertools import chain
import unittest

srcRe = re.compile("^([^/.]+)\.py$")

def isImportable(self, module_name) :
    __import__(module_name)

def iterFiles(dsc) :
    base, dirnames, filenames = dsc
    baseL = os.path.normpath(base).split(os.path.sep)
    def add(baseL,match) :
        moduleL = list(baseL)
        if f != '__init__.py' :
            moduleL.append(match.group(1))
        def test(self) :
            return isImportable(self, '.'.join(moduleL))
        test.__name__ = 'test_'+('_'.join(moduleL))
        return test.__name__, test
    for f in filenames :
        if base == '.' and f == "setup.py" :
            # worth not testing the setuptools stuff
            continue
        match = srcRe.match(f)
        if match :
            yield add(baseL, match)

TestImportable = type("TestImportable", (unittest.TestCase,), dict(chain(*map(iterFiles, os.walk('.')))))
