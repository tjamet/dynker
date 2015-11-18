import sys
from .dockerfile import Dockerfile
from .image import ImageBuilder

class Builder(object) :
    def __init__(self, **images) :
        self.images = {}
        self.addImages(*images.iteritems())
    def addImages(self, *images) :
        for imgName, desc in images:
            desc = dict(desc)
            contextMap = desc.pop('context',{'/':'.'})
            dockerfile = desc.pop('dockerfile','Dockerfile')
            imgName = desc.pop("imageName", imgName)
            if not isinstance(dockerfile,dict) :
                dockerfile = {
                    'paths' : [dockerfile],
                }
            dockerfile['tagResolver'] = self
            dockerfile = Dockerfile(**dockerfile)
            self.images[imgName] = ImageBuilder(imgName, dockerfile=dockerfile, contextMap=contextMap)
    def imageTag(self, imgName) :
        imgBuilder = self.images.get(imgName, None)
        if imgBuilder :
            return imgBuilder.buildTag()
        return None
    def build(self, client, followSymLinks=False, restoreMTime=False, names=None) :
        # we don't expect to have large number of image sto build for now,
        # thus, we can handle a simple lookup table
        if names is None :
            names = self.images.keys()
        rDepLookup = {}
        for imgName in names :
            imgDeps = self.images[imgName].imageDeps()
            for imgDep in imgDeps :
                if imgDep not in rDepLookup :
                    rDepLookup[imgDep] = []
                rDepLookup[imgDep].append(imgName)
        # start building images depending on a foreign image
        leafs = set(rDepLookup.keys()) - set(self.images.keys())
        def getAllDepOn(*imgs) :
            r=[]
            for img in imgs :
                r+= rDepLookup.get(img,[])
            return r
        toBuild = getAllDepOn(*leafs)
        while toBuild :
            for img in toBuild :
                builder = self.images[img]
                builder.build(client, followSymLinks, restoreMTime)
            toBuild=getAllDepOn(*toBuild)

def main(argv=sys.argv) :
    import sys, os
    import yaml
    from optparse import OptionParser
    from docker import Client
    from . import addCommonOptions, commonSetUp
    from .dockerfile import addDockerfileOptions
    from .image import addImageOptions
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="file", default="dynker.yml",
                      help="Path to the FILE containing container definitions.", metavar="FILE")
    parser.add_option("-t", "--tag", dest="tag", default="",
                      help="Repository name (and optionally a tag) to be applied to the resulting image in case of success")
    addCommonOptions(parser)
    addDockerfileOptions(parser)
    addImageOptions(parser)
    (options, args) = parser.parse_args(argv)
    commonSetUp(options)
    images = yaml.load(file(options.file))
    builder = Builder(**images)
    builder.build(Client(base_url=os.environ.get("DOCKER_HOST", None)))


if __name__ == "__main__" :
    main()
