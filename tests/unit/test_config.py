import dynker.config
import faker
import os
import random
import six
import sure
import unittest
import yaml

from .. import mock

class TestNode(unittest.TestCase):

    def setUp(self):
        self.faker = faker.Faker()

    def test_init_empty(self):
        node = dynker.config.Node()
        node.should.be.empty

    def test_init_with_values(self):
        value = self.faker.text()
        node = dynker.config.Node(someAttribute=value)
        dict(node).should.be.eql({'someAttribute':value})

        dic = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        node = dynker.config.Node(**dic)
        for key, val in six.iteritems(node):
            val.should.be.eql(dic[key])
        dict(node).should.be.eql(dic)

        # ensure Node initializer does not alter source dict
        dic = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        orig = dict(dic)
        dynker.config.Node(**dic)
        dic.should.be.eql(orig)

    def test_flat_update(self):
        base = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        update = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        _base = dict(base)
        _update = dict(update)
        merged = dict(base)
        merged.update(update)

        baseNode = dynker.config.Node(**base)
        updateNode = dynker.config.Node(**update)

        baseNode.update(update)
        # ensure Node update did not alter source
        # dicts
        base.should.eql(_base)
        update.should.eql(_update)
        dict(baseNode).should.eql(merged)

        baseNode = dynker.config.Node(**base)
        baseNode.update(updateNode)
        # ensure Node update did not alter source
        # dicts
        base.should.eql(_base)
        update.should.eql(_update)
        dict(updateNode).should.eql(_update)
        baseNode.should.eql(dynker.config.Node(**merged))

        baseNode = dynker.config.Node(**base)
        for value in [
            self.faker.text(),
            self.faker.pystr(),
            self.faker.pyint(),
            self.faker.pyset(),
            ]:
                key = random.choice(list(base.keys()))
                baseNode.update({key: value})
                baseNode[key].should.eql(value)

    def test_struct_update(self):
        node = dynker.config.Node(key1= {'subkey1': 'value 1'})
        node.update({'key1': {'subkey2': 'value 2'}})
        dict(node).should.be.eql({
            'key1':{
                'subkey1': 'value 1',
                'subkey2': 'value 2',
            }
       })

    def test_struct_override(self):
        dic = {
            'key1': 'string',
            'key2': {'subKey2': 'string'},
            'key3': ['list'],
        }
        node = dynker.config.Node(**dic)
        with self.assertRaises(ValueError):
            node.update({'key1': {'subkey1': 'string'}})
        with self.assertRaises(ValueError):
            node.update({'key2': 'string'})
        with self.assertRaises(ValueError):
            node.update({'key1': ['list']})
        with self.assertRaises(ValueError):
            node.update({'key2': ['list']})
        with self.assertRaises(ValueError):
            node.update({'key3': 'string'})
        with self.assertRaises(ValueError):
            node.update({'key3': {'dict': 'key'}})

    def test_update_appends_to_list(self):
        dic = {
            'key3': ['list'],
        }
        node = dynker.config.Node(**dic)
        node.update({'key3': ['other']})
        dict(node).should.should.be.eql({
            'key3': ['list', 'other'],
        })

    def test_parse_key(self):
        node = dynker.config.Node()
        node.parse_key.when.called_with(
            'some.long.key.with.dots'
        ).should.return_value(
            ['some', 'long', 'key', 'with', 'dots']
        )

    def test_parse_kv(self):
        node = dynker.config.Node()
        node.parse_kv.when.called_with(
            'some.long.key.with.dots=value'
        ).should.return_value(
            ['some.long.key.with.dots', 'value']
        )
        node.parse_kv.when.called_with(
            'some.long.key.with.dots=value=with='
        ).should.return_value(
            ['some.long.key.with.dots', 'value=with=']
        )

    def test_from_kv(self):
        node = dynker.config.Node.from_kv(['some.key=2'])
        dict(node).should.eql({
            'some': {
                'key': '2',
            }
        })

        node = dynker.config.Node.from_kv(['some.other.key=2'])
        dict(node).should.eql({
            'some': {
                'other':{
                    'key': '2',
                }
            }
        })

        node = dynker.config.Node.from_kv(['some.other.key=2', 'some.other.key=5'])
        dict(node).should.eql({
            'some': {
                'other':{
                    'key': '5',
                }
            }
        })

        node = dynker.config.Node.from_kv(['some.other.key=2', 'some.other.key2=5'])
        dict(node).should.eql({
            'some': {
                'other':{
                    'key': '2',
                    'key2': '5',
                }
            }
        })

    def test_node_from_kv_raises_error_with_missing_value(self):
        with self.assertRaises(ValueError):
            node = dynker.config.Node.from_kv(['1'])

    def test_node_from_kv_raises_error_with_missing_key(self):
        with self.assertRaises(ValueError):
            node = dynker.config.Node.from_kv(['=1'])

    def test_get_single_key(self):
        node = dynker.config.Node.from_kv(['some.key=2', 'somevalue=1'])
        node.get.when.called_with('somevalue').should.return_value('1')
        node.get.when.called_with('somevalue', None).should.return_value('1')
        node.get.when.called_with('some.key').should.return_value('2')
        node.get.when.called_with('some.key', None).should.return_value('2')

    def test_get_key_returns_default_value_on_miss(self):
        node = dynker.config.Config(['some.key=2', 'somevalue=1'])
        node.get.when.called_with('some.other.key').should.return_value(None)
        node.get.when.called_with('some.other.key', 'some.default').should.return_value('some.default')

class TestConfig(unittest.TestCase):

    def stub_config(self, homedir='HOME', ospjoin='.', exists=False):
        os.path.expanduser.return_value = homedir
        os.path.join.return_value = ospjoin
        if isinstance(exists, (list, tuple)) or callable(exists):
            os.path.exists.side_effect = exists
        else:
            os.path.exists.return_value = exists

    @property
    def config_path(self):
        return 'tests/fixtures/config.yml'

    @property
    def config_dict(self):
        return yaml.load(open(self.config_path))

    @mock.patch('os.path.expanduser')
    @mock.patch('os.path.join')
    @mock.patch('os.path.exists')
    def test_init_default_path(self, exists, join, expanduser):
        self.stub_config('HOME', '.', False)
        dynker.config.Config([]).should.be.empty
        os.path.expanduser.assert_called_once_with('~')
        os.path.join.assert_called_once_with('HOME', '.dynker', 'config.yml')

    @mock.patch('os.path.expanduser')
    @mock.patch('os.path.join')
    @mock.patch('os.path.exists')
    def test_init_no_arg(self, exists, join, expanduser):
        self.stub_config('HOME', '.', False)
        dynker.config.Config().should.be.empty
        os.path.expanduser.assert_called_once_with('~')
        os.path.join.assert_called_once_with('HOME', '.dynker', 'config.yml')
        os.path.exists.assert_called_with('.dynker.yml')

    @mock.patch('os.path.expanduser')
    @mock.patch('os.path.join')
    @mock.patch('os.path.exists')
    def test_init_named_args(self, exists, join, expanduser):

        self.stub_config()
        cfg = dynker.config.Config(config_path=self.config_path)
        dict(cfg).should.be.eql(self.config_dict)

    @mock.patch('os.path.expanduser')
    @mock.patch('os.path.join')
    @mock.patch('os.path.exists')
    def test_init_empty_config(self, exists, join, expanduser):
        self.stub_config(exists=False)
        dynker.config.Config([]).should.be.empty

    @mock.patch('os.path.expanduser')
    @mock.patch('os.path.join')
    @mock.patch('os.path.exists')
    def test_init_load_yaml(self, exists, join, expanduser):
        self.stub_config(ospjoin=self.config_path, exists=lambda x: x==self.config_path)
        cfg = dynker.config.Config([])
        dict(cfg).should.be.eql(self.config_dict)

        self.stub_config(exists=False)
        cfg = dynker.config.Config([], self.config_path)
        dict(cfg).should.be.eql(self.config_dict)

        

