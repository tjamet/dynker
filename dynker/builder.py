import sys
import os
import itertools
import logging
import glob
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
        self.config = config

    def getImage(self, image_name):
        try:
            return self.images[image_name]
        except KeyError:
            self.logger.debug('image builder cache miss, try to find it')
            for img_cfg in self.config.get('images', []):
                dockerfile = img_cfg.get('Dockerfile', 'Dockerfile')
                pattern = os.path.join(
                    img_cfg['path'],
                    dockerfile
                )
                for path in glob.glob(pattern):
                    pre = img_cfg.get('pattern', pattern).split('*', 1)[0]
                    post = img_cfg.get('pattern', pattern).rsplit('*', 1)[1]
                    context_path = path[:-len(dockerfile)-1]
                    found_image_name = context_path
                    if pre and found_image_name.startswith(pre):
                        found_image_name = found_image_name[len(pre):]
                    if post and found_image_name.endswith(post):
                        found_image_name = found_image_name[-len(post):]
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

    def build(self, client, names=None) :
        if isinstance(names, (str, unicode)):
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
        deps = list(
            itertools.chain(*itertools.imap(
                iter_buildable_deps,
                names)
            )
        )
        self.logger.debug("Will build parent images %r", deps)

        if deps:
            self.build(client, deps)
        for name in names:
            self.getImage(name).build(client)

def main(argv=sys.argv) :
    import sys, os
    import yaml
    from optparse import OptionParser
    from docker import Client
    from . import addCommonOptions, commonSetUp
    from .dockerfile import addDockerfileOptions
    from .image import addImageOptions
    parser = OptionParser()
    parser.add_option("-t", "--tag", dest="tag", default="",
                      help="Repository name (and optionally a tag) to be applied to the resulting image in case of success")
    addCommonOptions(parser)
    addDockerfileOptions(parser)
    addImageOptions(parser)
    (options, args) = parser.parse_args(argv[1:])
    commonSetUp(options)
    builder = Builder()
    builder.build(Client.from_env(), args)

if __name__ == "__main__" :
    main()
