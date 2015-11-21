# dynker
Multiple docker images builder handling inter images dependencies

## Install

Install the tool by launching `python setup.py install` as root or `python setup.py install --user`
If you do not have root acces or do not want to bother your co-workers on the same host

## Use

The purpose of this tool is to build docker images described on a yaml file (dynker.yml), sequenced in
a way that `FROM` images are built before the images requiring them.

The followings are also handled:
- Tag the built images with the last commit hash on the build context
- On-the-fly update of the `FROM` directives to get the latest build tag
- Dockerfiles are pre-processed in order to purge apt/yum caches after install (https://docs.docker.com/engine/articles/dockerfile_best-practices)
- Dockerfiles are pre-processed in order to work-arround yum bug with overlay driver (see
    https://github.com/docker/docker/issues/10180 and
    https://bugzilla.redhat.com/show_bug.cgi?id=1213602#c13)

### Example
`dynker.yml`
```
---
build:
    imageName: user/baseImageWithBuildTools
    context:
      /src: .
      /Dockerfile: build/Dockerfile
test:
    imageName: testingImage
    context:
      /repo: .
package:
    imageName: user/imageName
    context:
      /packaging: packaging
```

`build/Dockerfile`
```
FROM debian:jessie
RUN  apt-get install -y python-pip
ADD  src /src
WORKDIR /src
```
`test/Dockerfile`
```
FROM user/baseImageWithBuildTools
RUN  python setup.py develop
RUN  python -m unittest discover
```
`package/Dockerfile`
```
FROM user/baseImageWithBuildTools
RUN  python setup.py install
RUN  rm -rf /src
```
Then, `dynker build` will :
 1. build user/baseImageWithBuildTools
 2. Build testingImage and imageName
