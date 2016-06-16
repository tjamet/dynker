import dynker.image as tested_module
import docker.errors
import json
import os
import six
import unittest
import tarfile

from .. import mock

class TestImage(unittest.TestCase):


    def test_listensteam(self):
        image = tested_module.ImageBuilder('dynker', 'tests/fixtures/docker/test')
        fd = six.StringIO()
        image.listenStream(fd=fd, stream=list(map(json.dumps,[
            {'stream': 'streamed-value\n'},
            {'status': 'done'},
        ]))+[
            "some non-json line",
        ])
        fd.getvalue().should.eql(
            '\x1b[36m[dynker]:\x1b[0m streamed-value\n'
            '\x1b[36m[dynker]:\x1b[0m done\n'
            "\x1b[36m[dynker]:\x1b[0m some non-json line",
        )
        image.listenStream.when.called_with([json.dumps(
            {'errorDetail':{'message': 'error message\n'}},
        )]).should.throw(ValueError, 'error message')
        image.listenStream.when.called_with([json.dumps(
            {},
        )]).should.throw(RuntimeError, '{}')

    def test_tag(self):
        image = tested_module.ImageBuilder('dynker', 'tests/fixtures/docker/test')
        client = mock.Mock()
        client.tag = mock.Mock(return_value=1)
        image.tag(client, ['latest', 'dev'], registries=['docker.my-company.com'])
        client.tag.call_count.should.eql(5)
        for call in [
            mock.call(mock.ANY, 'dynker', 'latest', force=True),
            mock.call(mock.ANY, 'dynker', 'dev', force=True),
            mock.call(mock.ANY, 'docker.my-company.com/dynker', 'latest', force=True),
            mock.call(mock.ANY, 'docker.my-company.com/dynker', 'dev', force=True),
            mock.call(mock.ANY, 'docker.my-company.com/dynker', image.buildTag(), force=True),
        ]:
            client.tag.mock_calls.should.contain(call)

    def test_build(self):
        client = mock.Mock()
        client.inspect_image = mock.Mock()
        client.build = mock.Mock()
        image = tested_module.ImageBuilder('dynker', 'tests/fixtures/docker/test')

        client.inspect_image.return_value = {'Id': 'fake image id'}

        image.build(client)
        client.build.assert_not_called()
        client.build.reset_mock()

        def inspect_image(*args, **kwds):
            raise docker.errors.NotFound("message", "response", "explanation")

        client.inspect_image.side_effect = inspect_image
        client.build.return_value = [
            json.dumps({'stream': 'build in progress1\r'}),
            json.dumps({'stream': 'build in progress2\r'}),
            json.dumps({'stream': 'build in progress3\033[K\r'}),
            json.dumps({'stream': 'build in progress4\033[K\r'}),
            json.dumps({'stream': 'build done\033[K\n'}),
        ]
        image.build(client)
        list(client.build.mock_calls).should.be.eql([
            mock.call(
                fileobj=image.getContext(),
                custom_context=True,
                encoding='gzip',
                tag='%s:%s' % ('dynker', image.buildTag()),
            )
        ])

    def test_deps(self):
        with mock.patch.object(tested_module.ImageBuilder,
                'expandContextMap',
                return_value={'file1': 'some/path/file1', 'file2': 'some/path/file2'}):
            image = tested_module.ImageBuilder('test-image', 'some/path')
            deps = image.deps()
            deps.should.contain('some/path/file1')
            deps.should.contain('some/path/file2')
            deps.should.have.length_of(2)

    def test_build_context(self):
        image = tested_module.ImageBuilder('dynker', '.', dockerfile='docker/dynker/Dockerfile', expandDirectory=True)
        context = six.BytesIO(image.getContext())
        tar = tarfile.open(fileobj=context, mode='r|gz')
        # just check if the Dockerfile has been created.
        tar.getmember('Dockerfile')

    def test_buildtag(self):
        original_stat = os.stat
        with mock.patch('os.stat') as stat:
            def _stat(path):
                r = original_stat(path)
                def iter_stat(r):
                    for attr in dir(r):
                        if attr.startswith('st_'):
                            yield attr, getattr(r,attr)
                kwds = dict(iter_stat(r))
                # freeze user permissions
                # even if the developer gave extra permissions
                # on the folders, pretend he didn't to ensure the
                # sha1 test to pass
                kwds['st_mode'] &= ~0o7777
                return mock.Mock(**kwds)
            stat.side_effect = _stat
            image = tested_module.ImageBuilder('dynker', 'tests/fixtures/docker/test')
            image.buildTag().should.be.eql('927c634d55087e483f4965ec76b0c5259493240e')

    def test_image_deps(self):
        with mock.patch.object(tested_module.Dockerfile,
                'imageDeps',
                return_value=[('image_name', None)]):
            image = tested_module.ImageBuilder('test-image', 'some/path')
            image.imageDeps.when.called_with().should.return_value([
                ('image_name', None),
            ])

    def test_contextmap(self):
        files = [
            "file1",
            "file2",
        ]
        with mock.patch.object(
                tested_module.Dockerfile,
                'listBuildFiles',
                return_value=files):
            with mock.patch.object(
                    tested_module.ExpandFileMapFilter,
                    'filter',
                    side_effect=lambda x: x) as filemap:
                with mock.patch.object(
                        tested_module.ExpandDirectoryFilter,
                        'filter',
                        side_effect=lambda x: x) as directory:
                    with mock.patch.object(
                            tested_module.ResolveSymLink,
                            'filter',
                            side_effect=lambda x: x) as symlink:

                        image = tested_module.ImageBuilder('test-image', 'some/path')
                        dict(image.expandContextMap()).should.be.eql({
                            "file1": "some/path/file1",
                            "file2": "some/path/file2",
                        })
                        filemap.call_count.should.be.eql(1)
                        directory.call_count.should.be.eql(1)
                        symlink.assert_not_called()

                        filemap.reset_mock()
                        directory.reset_mock()
                        symlink.reset_mock()

                        image = tested_module.ImageBuilder('test-image', 'some/path', followSymLinks=True)
                        dict(image.expandContextMap()).should.be.eql({
                            "file1": "some/path/file1",
                            "file2": "some/path/file2",
                        })
                        filemap.call_count.should.be.eql(1)
                        directory.call_count.should.be.eql(1)
                        symlink.call_count.should.be.eql(1)

                        filemap.reset_mock()
                        directory.reset_mock()
                        symlink.reset_mock()

                        image = tested_module.ImageBuilder('test-image', 'some/path', expandDirectory=True)
                        dict(image.expandContextMap()).should.be.eql({
                            "file1": "some/path/file1",
                            "file2": "some/path/file2",
                        })
                        filemap.call_count.should.be.eql(1)
                        directory.call_count.should.be.eql(1)
                        symlink.assert_not_called()

                        filemap.reset_mock()
                        directory.reset_mock()
                        symlink.reset_mock()

                        image = tested_module.ImageBuilder('test-image', 'some/path', followSymLinks=True, expandDirectory=True)
                        dict(image.expandContextMap()).should.be.eql({
                            "file1": "some/path/file1",
                            "file2": "some/path/file2",
                        })
                        filemap.call_count.should.be.eql(1)
                        directory.call_count.should.be.eql(1)
                        symlink.call_count.should.be.eql(1)
