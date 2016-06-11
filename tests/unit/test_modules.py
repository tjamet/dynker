import os, sys
import re
from itertools import chain
import unittest
import importlib

srcRe = re.compile("^([^/.]+)\.py$")

def iterFiles(dsc) :
    base, dirnames, filenames = dsc
    baseL = os.path.normpath(base).split(os.path.sep)
    def add(baseL,match) :
        moduleL = list(baseL)
        if f != '__init__.py' :
            moduleL.append(match.group(1))
        def test(self) :
            importlib.import_module('.'.join(moduleL))
        test.__name__ = 'test_'+('_'.join(moduleL))
        return test.__name__, test

    for f in filenames :
        match = srcRe.match(f)
        if match :
            yield add(baseL, match)

TestImportable = type("TestImportable", (unittest.TestCase,), dict(chain(*map(iterFiles, os.walk('dynker')))))
