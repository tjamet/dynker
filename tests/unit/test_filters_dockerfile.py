import dynker.filters.dockerfile as tested_module
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

class TestDockerfile(unittest.TestCase):

    def test_layer_optimisation(self):
        filter = filterFactory(tested_module.DockerfileOptLayers)
        filter.filter.when.called_with([
            "RUN something",
            "RUN something.else",
        ]).should.return_value([
            "RUN something && something.else",
        ])

        filter.filter.when.called_with([
            "RUN something",
            "ADD some /file",
            "RUN something.else",
        ]).should.return_value([
            "RUN something",
            "ADD some /file",
            "RUN something.else",
        ])

    def test_multiline_contatenation(self):
        filter = filterFactory(tested_module.DockerileMultipleLine)
        filter.filter.when.called_with([
            'first line \\',
            'second line',
        ]).should.return_value([
            'first line second line',
        ])

        filter.filter.when.called_with([
            'first line \\',
        ]).should.return_value([
            'first line \\',
        ])

    def test_yum_cache_clean(self):
        filter = filterFactory(tested_module.DockerfileOptYum)
        filter.filter.when.called_with([
            "RUN yum -y install something",
        ]).should.return_value([
            "RUN touch /var/lib/rpm/* && yum -y install something && yum clean all",
        ])
        filter.filter.when.called_with([
            "RUN do sthg && yum -y install something && "
            "do something.else && yum install some other thing",
        ]).should.return_value([
            "RUN touch /var/lib/rpm/* && do sthg && yum -y install something && "
            "do something.else && yum install some other thing && yum clean all",
        ])

    def test_apt_update(self):
        filter = filterFactory(tested_module.DockerfileOptApt)
        filter.filter.when.called_with([
            "RUN apt-get install something",
        ]).should.return_value([
            "RUN apt-get update && apt-get install something && apt-get clean",
        ])
        filter.filter.when.called_with([
            "RUN do.sthg && apt-get install something "
            "&& do.some-more-thing && apt-get install -y pkg",
        ]).should.return_value([
            "RUN apt-get update && do.sthg && apt-get install something "
            "&& do.some-more-thing && apt-get install -y pkg && apt-get clean",
        ])

    def test_from_filter(self):
        filter = filterFactory(tested_module.DockerfileFromFilter)
        filter.filter.when.called_with([
            'FROM base-image',
            'RUN  something',
            'FROM other-image',
        ]).should.return_value([
            'FROM base-image',
            'RUN  something',
            'FROM other-image',
        ])

        filter = filterFactory(tested_module.DockerfileFromFilter, keepFirstFrom=False)
        filter.filter.when.called_with([
            'FROM base-image',
            'RUN  something',
            'FROM other-image',
        ]).should.return_value([
            'FROM base-image',
            'RUN  something',
            'FROM other-image',
        ])

        filter = filterFactory(tested_module.DockerfileFromFilter, keepFirstFrom=True)
        filter.filter.when.called_with([
            'FROM base-image',
            'RUN  something',
            'FROM other-image',
        ]).should.return_value([
            'FROM base-image',
            'RUN  something',
        ])

    def test_from_updates_image_tags(self):
        class Resolver(object): pass
        resolver = Resolver()
        resolver.imageTag = mock.Mock(return_value = 'some.tag')
        filter = filterFactory(tested_module.DockerfileFromFilter, tagResolver=resolver)
        filter.filter.when.called_with([
            'FROM base-image',
        ]).should.return_value([
            'FROM base-image:some.tag',
        ])

        filter.filter.when.called_with([
            'FROM base-image:latest',
        ]).should.return_value([
            'FROM base-image:some.tag',
        ])

        resolver.imageTag.return_value = None

        filter.filter.when.called_with([
            'FROM base-image',
        ]).should.return_value([
            'FROM base-image',
        ])

        filter.filter.when.called_with([
            'FROM base-image:latest',
        ]).should.return_value([
            'FROM base-image:latest',
        ])

    def test_dep_extractor_returns_tags(self):
        for c in tested_module.DockerfileDepExtractorFilter, tested_module.DockerfileDepExtractor:
            filter = filterFactory(c)
            filter.filter.when.called_with([
                'FROM base-image',
                'RUN  something',
                'FROM base-image',
            ]).should.return_value([
                ('base-image', None),
                ('base-image', None),
            ])

            filter.filter.when.called_with([
                'FROM base-image:latest',
                'FROM base-image:latest',
            ]).should.return_value([
                ('base-image', 'latest'),
                ('base-image', 'latest'),
            ])

            filter = filterFactory(c, keepFirstFrom=False)
            filter.filter.when.called_with([
                'FROM base-image',
                'FROM base-image',
            ]).should.return_value([
                ('base-image', None),
                ('base-image', None),
            ])

            filter.filter.when.called_with([
                'FROM base-image:latest',
                'FROM base-image:latest',
            ]).should.return_value([
                ('base-image', 'latest'),
                ('base-image', 'latest'),
            ])

            filter = filterFactory(c, keepFirstFrom=True)
            filter.filter.when.called_with([
                'FROM base-image',
                'FROM base-image',
            ]).should.return_value([
                ('base-image', None),
            ])

            filter.filter.when.called_with([
                'FROM base-image:latest',
                'FROM base-image:latest',
            ]).should.return_value([
                ('base-image', 'latest'),
            ])

    def test_dep_extractor_returns_resolved_tags(self):
        class Resolver(object): pass
        resolver = Resolver()
        resolver.imageTag = mock.Mock(return_value = 'some.tag')
        filter = filterFactory(tested_module.DockerfileDepExtractorFilter, tagResolver=resolver)
        filter.filter.when.called_with([
            'FROM base-image',
        ]).should.return_value([
            ('base-image', 'some.tag'),
        ])

        filter.filter.when.called_with([
            'FROM base-image:latest',
        ]).should.return_value([
            ('base-image', 'some.tag'),
        ])

        resolver.imageTag.return_value = None

        filter.filter.when.called_with([
            'FROM base-image',
        ]).should.return_value([
            ('base-image', None),
        ])

        filter.filter.when.called_with([
            'FROM base-image:latest',
        ]).should.return_value([
            ('base-image', 'latest'),
        ])

    def test_add_extractor(self):
        for c in (tested_module.DockerfileAddExtractorFilter, tested_module.DockerfileAddExtractor):
            filter = filterFactory(c)

            filter.filter.when.called_with([
                'FROM some-image',
                'ADD some /file',
                'RUN something',
                'ADD other /folder/',
            ]).should.return_value([
                'some',
                'other'
            ])


    def test_dockerfile(self):
        filter = filterFactory(tested_module.DockerfileFilter)
        filter.filter.when.called_with([
            'FROM an/image',
            '# a comment describing the image',
            '  # yet another badly indented comment',
            'RUN something # to explain why',
            '  RUN something.else    ',
            'RUN something\\',
            '    on 2 lines',
            '   ',
            '',
            'ADD some file'
        ]).should.return_value([
            'FROM an/image',
            'RUN something',
            'RUN something.else',
            'RUN something    on 2 lines',
            'ADD some file'
        ])

        filter = filterFactory(tested_module.DockerfileFilter, optimizeLayers=True)
        filter.filter.when.called_with([
            'FROM an/image',
            '# a comment describing the image',
            '  # yet another badly indented comment',
            'RUN something # to explain why',
            '  RUN something.else    ',
            'RUN something\\',
            '    on 2 lines',
            '   ',
            '',
            'ADD some file'
        ]).should.return_value([
            'FROM an/image',
            'RUN something && something.else && something    on 2 lines',
            'ADD some file'
        ])
