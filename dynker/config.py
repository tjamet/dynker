import os
import six
import yaml

class Node(dict):

    def __init__(self, **values):
        super(Node, self).__init__()
        self.update(values)

    def update(self, other):
        for k, v in six.iteritems(other):
            try:
                oldv = self[k]
            except KeyError:
                if isinstance(v, dict):
                    node = Node()
                    node.update(v)
                    self[k] = node
                else:
                    if isinstance(v, (list, tuple)):
                        v = list(v)
                    self[k] = v
            else:
                for kind in (dict, (list, tuple)):
                    if isinstance(oldv, kind) or isinstance(v, kind):
                        if not isinstance(oldv, kind) or not isinstance(v, kind):
                            raise ValueError("Can't update uncoherent values for key %s, old value: %r, new value: %r" % (k, oldv, v))
                if isinstance(oldv, dict):
                    oldv.update(v)
                elif isinstance(oldv, (list, tuple)):
                    for item in v:
                        oldv.append(item)
                else:
                    self[k] = v

class Config(Node):

    def __init__(self, options=[], config_path=None):
        super(Config, self).__init__()
        for path in (
            os.path.join(os.path.expanduser("~"), ".dynker", "config.yml"),
            os.getenv('DYNKER_CONFIG', None),
            '.dynker.yml',
        ):
            if path and os.path.exists(path):
                self.update(yaml.load(open(path, 'r')))
        if config_path is not None:
            self.update(yaml.load(open(config_path, 'r')))
        for opt in options:
            k, v = self.parse_kv(opt)
            node = {}
            child = node
            keys = self.parse_key(k)
            for key in keys[:-1]:
                child[key] = {}
                child = child[key]
            child[keys[-1]] = v
            self.update(node)

    def parse_key(self, key):
        r = key.split('.')
        if r == ['']:
            raise ValueError('Failed to find any key in %r' % key)
        return r

    def parse_kv(self, kv):
        r = kv.split('=', 1)
        if len(r) != 2:
            raise ValueError('Failed to decode <key>=<value> in %r.' % kv)
        return r

    def get(self, path, default=None):
        node = self
        try:
            for key in self.parse_key(path):
                node = node[key]
            return node
        except KeyError:
            return default

