import dynker.filters.file as tested_module
import unittest

from .. import mock

def filterFactory(base, *args, **kwds):
    class TestFilter(base):
        """
        A small class that converts filter output
        into list for easier asserts
        """
        def filter(self, *args, **kwds):
            return list(base.filter(self, *args, **kwds))
    return TestFilter(*args, **kwds)

class TestFileFilters(unittest.TestCase):

    def test_base_file_filter(self):
        filter = filterFactory(tested_module.FileMapFilter)
        class custom_filter(object):
            @staticmethod
            def filter(it):
                for line in it:
                    yield 'filtered '+ line
        filter.filters = [custom_filter]
        filter.filter.when.called_with([
            'line 1',
            'line 2',
        ]).should.return_value([
            'filtered line 1',
            'filtered line 2',
        ])

    @mock.patch('glob.iglob')
    @mock.patch('glob.glob')
    def test_expand_map(self, glob, iglob):
        filter = filterFactory(tested_module.ExpandFileMapFilter)
        glob.return_value = []
        filter.filter.when.called_with([
            ('destination', 'source'),
            ('other/destination', 'other/src'),
        ]).should.return_value([
        ])
        glob.side_effect = [
            ['resolved/source'],
            ['resolved/other.source'],
        ]
        filter.filter.when.called_with([
            ('destination', 'source'),
            ('other/destination', 'other/src'),
        ]).should.return_value([
            ('destination', 'resolved/source'),
            ('other/destination', 'resolved/other.source'),
        ])
        
        iglob.side_effect = [
            [ 'source/source1', 'source/source2' ],
            [ 'other/src/src1', 'other/src/src2' ],
        ]
        filter.filter.when.called_with([
            ('destination/', 'source/*'),
            ('other/destination/', 'other/src/*'),
        ]).should.return_value([
            ('destination/source1', 'source/source1'),
            ('destination/source2', 'source/source2'),
            ('other/destination/src1', 'other/src/src1'),
            ('other/destination/src2', 'other/src/src2'),
        ])

        iglob.side_effect = [
            [ 'source1', 'source2' ],
            [ 'other/src1', 'other/src2' ],
        ]
        filter.filter.when.called_with([
            ('destination/', 'source*'),
            ('other/destination/', 'other/src*'),
        ]).should.return_value([
            ('destination/1', 'source1'),
            ('destination/2', 'source2'),
            ('other/destination/1', 'other/src1'),
            ('other/destination/2', 'other/src2'),
        ])

        iglob.side_effect = [
            [ 'source1', 'source2' ],
            [ 'other/src1', 'other/src2' ],
        ]
        filter.filter.when.called_with([
            ('destination', 'source*'),
            ('other/destination', 'other/src*'),
        ]).should.return_value([
            ('destination1', 'source1'),
            ('destination2', 'source2'),
            ('other/destination1', 'other/src1'),
            ('other/destination2', 'other/src2'),
        ])

    def test_expand_dir(self):
        filter = filterFactory(tested_module.ExpandDirectoryFilter)
        # expanding directories does not mean
        # dropping other files
        filter.filter.when.called_with([
            (__file__, __file__),
            ('file.that/does.not/exist', 'file.that/does-not_exist'),
            ('other/file.that/does.not/exist', 'other/file.that/does-not_exist'),
        ]).should.return_value([
            (__file__, __file__),
            ('file.that/does.not/exist', 'file.that/does-not_exist'),
            ('other/file.that/does.not/exist', 'other/file.that/does-not_exist'),
        ])
        filter.filter.when.called_with([
        ]).should.return_value([
        ])

        expected_content = [
            ("destination/dynker/config.yml",                  "tests/fixtures/config.yml"),
            ("destination/dynker/folder/.hidden/.hidden/file", "tests/fixtures/folder/.hidden/.hidden/file"),
            ("destination/dynker/folder/.hidden/file",         "tests/fixtures/folder/.hidden/file"),
            ("destination/dynker/folder/.hidden-file",         "tests/fixtures/folder/.hidden-file"),
            ("destination/dynker/folder/file",                 "tests/fixtures/folder/file"),
            ("destination/dynker/folder/level1/file",          "tests/fixtures/folder/level1/file"),
            ("destination/dynker/folder/level1/level2/file",   "tests/fixtures/folder/level1/level2/file"),
        ]
        mapping = filter.filter([
            ('destination/dynker', 'tests/fixtures/'),
        ])
        mapping.should.have.length_of(len(expected_content))
        for content in expected_content:
            mapping.should.contain(content)

    @mock.patch('os.path.islink')
    @mock.patch('os.readlink')
    def test_symlink_resolver(self, readlink, islink):
        filter = filterFactory(tested_module.ResolveSymLink)
        islink.side_effect = lambda x: x.startswith('link/')
        filter.filter.when.called_with([
        ]).should.return_value([
        ])
        filter.filter.when.called_with([
            ('destination', 'source'),
        ]).should.return_value([
            ('destination', 'source'),
        ])
        readlink.assert_not_called()
        readlink.side_effect = [
            'link/other',
            'link/some/path',
            'resolved_link',
        ]
        filter.filter.when.called_with([
            ('destination', 'link/somewhere/linked'),
        ]).should.return_value([
            ('destination', 'resolved_link'),
        ])
