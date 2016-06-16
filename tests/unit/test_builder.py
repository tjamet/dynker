import dynker.builder as tested_module
import dynker.config
import unittest
import six

from .. import mock


class TestBuilder(unittest.TestCase):

    @mock.patch('docker.Client')
    def test_main(self, client):
        cl = mock.Mock()
        cl.inspect_image = mock.Mock(return_value={})
        cl.tag = mock.Mock(return_value=1)

        client.from_env = mock.Mock(return_value=cl)
        command = ['build', 'layer10', '-v', '--registry', 'docker.my-company.com']
        tested_module.main(command)
        cl.inspect_image.call_count.should.eql(12)
        cl.tag.call_count.should.eql(3)
        cl.tag.mock_calls.should.contain(
            mock.call(mock.ANY, 'layer10', 'latest', force=True)
        )
        cl.tag.mock_calls.should.contain(
            mock.call(mock.ANY, 'docker.my-company.com/layer10', 'latest', force=True)
        )

    def test_build_order(self):
        class ImageBuilder(object):
            build_order = []
            def __init__(self, image, deps=[]):
                self.image = image
                self.deps = deps
            def imageDeps(self):
                return map(lambda x: (x,'latest'), self.deps)
            def build(self, client):
                self.build_order.append(self.image)
        images = {}
        for i in range(11):
            images['image%d' % i] = ImageBuilder('image%d' % i, ['image%d' % (i-1) if i > 0 else 'alpine'])
        builder = tested_module.Builder()
        for key, val in six.iteritems(images):
            builder.images[key] = val
        client = object()
        builder.build(client, 'image10')
        ImageBuilder.build_order.should.be.eql([
            'image%d' % i for i in range(11)
        ])

        # introduce a dependency loop
        builder.images['alpine'] = ImageBuilder('alpine', ['image10'])
        builder.build.when.called_with(client, 'image10').should.throw(
            RuntimeError, 'dependency loop detected'
        )

    def test_pattern_precomputation(self):
        config = dynker.config.Node(images=[
            {'path': 'docker/*', 'Dockerfile': '*/Dockerfile'}
        ])
        tested_module.Builder.when.called_with(config=config).should.throw(
            ValueError, 'either in "Dockerfile" or "path"'
        )
        # Any other setting is tested more globally with test_get_image

    @mock.patch('os.path.exists', return_value=False)
    def test_default_config(self, exists):
        builder = tested_module.Builder()
        builder.config.get('images').should.be.eql([
            {'path': 'docker/*'}
        ])

    def test_image_tag(self):
        imgBuilder = mock.Mock()
        imgBuilder.buildTag = mock.Mock(return_value="build.tag")
        builder = tested_module.Builder()
        builder.images['image'] = imgBuilder
        builder.imageTag("unknown-image").should.be(None)
        builder.imageTag("image").should.be('build.tag')

    def test_get_image(self):
        config = dynker.config.Node(
            images = [
                {'path': 'docker/*'},
                {'path': 'tests/fixtures/docker/*'},
                {'path': 'tests/', 'Dockerfile':'tests/fix*/*/*st/Dockerfile'},
                {'path': 'tests/', 'Dockerfile':'te*/fix*/*/test/Dockerfile'},
                {'name': 'dummy', 'Dockerfile':'docker/dynker/Dockerfile'},
            ],
        )
        builder = tested_module.Builder(config=config)
        image = builder.getImage('dynker')
        image.name.should.be.eql('dynker')
        image.contextPath.should.be.eql('docker/dynker')

        image = builder.getImage('test')
        image.name.should.be.eql('test')
        image.contextPath.should.be.eql('tests/fixtures/docker/test')

        image = builder.getImage('fixtures/docker/test')
        image.name.should.be.eql('fixtures/docker/test')
        image.contextPath.should.be.eql('tests/')

        image = builder.getImage('tests/fixtures/docker')
        image.name.should.be.eql('tests/fixtures/docker')
        image.contextPath.should.be.eql('tests/')

        image = builder.getImage('dummy')
        image.name.should.be.eql('dummy')
        image.contextPath.should.be.eql('.')

        builder.getImage.when.called_with('some-image-from-mars').should.throw(
            KeyError, 'Cannot find image some-image-from-mars'
        )
