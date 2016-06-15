import glob
import fnmatch
import itertools
import logging
import os
import re
import six
import sys
import yaml

from .dockerfile import Dockerfile
from .image import ImageBuilder
from .config import Config


class Builder(object) :

    def __init__(self, config=None, **kwds) :
        self.logger = logging.getLogger(type(self).__name__)
        self.kwds = kwds
        self.images = {}
        if config is None:
            config = Config()
            config.update(dict(
                images= [
                    {
                        'path': 'docker/*',
                    }
                ],
            ))
        self.patterns = []
        for image in config['images']:
            # When path is provided and globbed, Dockerfile refers to its location
            # When path is provided but not globbed, Dockerfile refers to the current path
            # When Dockerfile is provided and globbed, path must not be globbed, both
            # refers to the current directory
            path = image.get('path', None)
            dockerfile = image.get('Dockerfile', 'Dockerfile')
            name = image.get('name', None)

            if path is None:
                path = '.'

            if '*' in path:
                if '*' in dockerfile:
                    raise ValueError('Ambiguity in your configuration for %r, globbing can'
                        'be done either in "Dockerfile" or "path" key but not both at the'
                        'same time' % image)

                dockerfile = os.path.join(path, dockerfile)
                path = re.compile(re.sub('^.*/([^*]*)$', r'(?P<path>.*)/\1', dockerfile))

            if name is None:
                name = dockerfile
            if '*' in name:
                start = re.sub('^([^*]*/|).*', r'^\1(?P<name>.*)', dockerfile)
                end = re.sub('^.*\*(?:|[^/]*)(/.*)$', r'\1$', dockerfile)
                name = re.compile(start + end)

            pattern = {
                'name': name,
                'path': path,
                'Dockerfile': dockerfile,
            }
            self.patterns.append(pattern)
        self.config = config

    def get_matching_pattern(self, pattern, name, path):
        pattern = pattern[name]
        if isinstance(pattern, six.string_types):
            return pattern
        else:
            match = pattern.match(path)
            if match:
                return match.group(name)
        return None
        

    def getImage(self, image_name):
        try:
            return self.images[image_name]
        except KeyError:
            self.logger.debug('image builder cache miss, try to find it')
            for img_cfg in self.patterns:
                for path in glob.glob(img_cfg['Dockerfile']):
                    found_image_name = self.get_matching_pattern(img_cfg, 'name', path)
                    context_path = self.get_matching_pattern(img_cfg, 'path', path)
                    if found_image_name == image_name:
                        image = ImageBuilder(image_name,
                            contextPath=context_path,
                            dockerfile=path,
                            tagResolver=self,
                            **self.kwds
                        )
                        self.images[image_name] = image
                        return image
        raise KeyError("Cannot find image %s" % image_name)

    def imageTag(self, imgName) :
        imgBuilder = self.images.get(imgName, None)
        if imgBuilder :
            return imgBuilder.buildTag()
        return None

    def build(self, client, names=None, child_images=[]) :
        if isinstance(names, six.string_types):
            names = [names]
        def iter_buildable_deps(name):
            """
            instanciates a builder for each image dependency
            does nothing when the image cannot be build
            """
            for dep_name, _ in self.getImage(name).imageDeps():
                try:
                    self.getImage(dep_name)
                    yield dep_name
                except KeyError:
                    continue
        for name in names:
            if name in child_images:
                raise RuntimeError("dependency loop detected, %s some how depends on itself %s" %
                    (name, ' -> '.join(child_images + [name]))
                )
            for dep_name in iter_buildable_deps(name):
                self.build(client, dep_name, child_images=child_images+[name])

        for name in names:
            self.getImage(name).build(client)

    def tag(self, client, tags, images, **kwds):
        if tags is None:
            tags = ['latest']
        for image in images:
            self.getImage(image).tag(client, tags, **kwds)


COMMAND_NAME='build'
def add_options(parser):
    from . import addCommonOptions, commonSetUp
    from .dockerfile import addDockerfileOptions
    from .image import addImageOptions
    try:
        add = parser.add_argument
    except AttributeError:
        add = parser.add_option
    add("image", nargs="*",
                      help="images to build")
    add("-t", "--tag", dest="tag", default=None, action='append',
                      help="tag(s) to be applied to the resulting image in case of success")
    add("--registry", dest="registry", default=[], action='append',
                      help="Registry on which the image should tagged (<registry>/<name>:<tag>)")
    addCommonOptions(parser)
    addDockerfileOptions(parser)
    addImageOptions(parser)

def main(argv=sys.argv, args=None) :
    """
    Builds a list of images
    """
    from . import commonSetUp
    if not args:
        import argparse
        parser = argparse.ArgumentParser()
        add_options(parser)
        args = parser.parse_args(argv[1:])
    import sys, os
    import yaml
    from docker import Client
    from . import commonSetUp
    commonSetUp(args)
    builder = Builder()
    builder.build(Client.from_env(), args.image)
    builder.tag(Client.from_env(), args.tag, args.image, registries=args.registry)

if __name__ == "__main__" :
    main()
