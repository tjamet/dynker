import dynker.dockerfile as tested_module
import sure
import six
import sys
import unittest
import tempfile

from .. import mock

class tempDockerfile(object):
    def __init__(self, content, name=None):
        self.content = content

    def __enter__(self):
        fd = tempfile.NamedTemporaryFile()
        self.fd = fd
        fd.write(six.b('\n'.join(self.content)))
        fd.seek(0)
        return fd

    def __exit__(self, exc_type, exc_value, tb):
        self.fd.close()

class TestDockerfile(unittest.TestCase):
    content = [
        'FROM image',
        'ADD  file /folder/',
        'RUN  yum install package',
        'RUN  apt-get install package',
        'FROM other-image:some.tag',
        'ADD  some.file /other.folder/',
        'RUN  something',
    ]

    def test_deps(self):
        with tempDockerfile(self.content) as fd:
            dockerfile = tested_module.Dockerfile(fd.name)
            dockerfile.deps.when.called_with().should.return_value([
                fd.name,
                'file',
                'some.file',
            ])

    def test_imageDeps(self):
        with tempDockerfile(self.content) as fd:
            dockerfile = tested_module.Dockerfile(fd.name)
            dockerfile.imageDeps.when.called_with().should.return_value([
                ('image', None),
                ('other-image', 'some.tag'),
            ])

    def test_str(self):
        with tempDockerfile(self.content) as fd:
            dockerfile = tested_module.Dockerfile(fd.name)
            dockerfile.__str__.when.called_with().should.return_value('\n'.join([
                'FROM image',
                'ADD  file /folder/',
                'RUN touch /var/lib/rpm/* &&  yum install package && yum clean all',
                'RUN apt-get update &&  apt-get install package && apt-get clean',
                'FROM other-image:some.tag',
                'ADD  some.file /other.folder/',
                'RUN  something',
            ]))

            dockerfile = tested_module.Dockerfile(fd.name, optimizeLayers=True)
            dockerfile.__str__.when.called_with().should.return_value('\n'.join([
                'FROM image',
                'ADD  file /folder/',
                'RUN touch /var/lib/rpm/* && apt-get update &&  '
                'yum install package &&  apt-get install package '
                '&& apt-get clean && yum clean all',
                'FROM other-image:some.tag',
                'ADD  some.file /other.folder/',
                'RUN  something',
            ]))

    @mock.patch('sys.stdout.write')
    def test_main(self, stdout):
        sys.stdout = stdout
        with tempDockerfile(self.content) as fd:
            args = ['dockerfile', '-f', fd.name, '-o', '-t', 'new.tag']
            tested_module.main(args)
            stdout.write.mock_calls.should.eql([
                mock.call(
                    '\n'.join([
                        'FROM image:new.tag',
                        'ADD  file /folder/',
                        'RUN touch /var/lib/rpm/* && apt-get update &&  '
                        'yum install package &&  apt-get install package '
                        '&& apt-get clean && yum clean all',
                        'FROM other-image:new.tag',
                        'ADD  some.file /other.folder/',
                        'RUN  something',
                    ])
                ),
                mock.call('\n'),
            ])

    @mock.patch('dynker.dockerfile.Dockerfile')
    def test_main(self, dockerfile):
        tested_module.main(['dockerfile', '-f', 'some.folder/file'])
        dockerfile.assert_called_with(
            ['some.folder/file'],
            newTag=mock.ANY, optimizeLayers=mock.ANY, single=mock.ANY
        )
        dockerfile.reset_mock()

        tested_module.main(['dockerfile', 'some.file'])
        dockerfile.assert_called_with(
            ['some.file'],
            newTag=mock.ANY, optimizeLayers=mock.ANY, single=mock.ANY
        )
        dockerfile.reset_mock()

        tested_module.main(['dockerfile'])
        dockerfile.assert_called_with(
            ['Dockerfile'],
            newTag=mock.ANY, optimizeLayers=mock.ANY, single=mock.ANY
        )
