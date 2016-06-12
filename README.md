# dynker
Multiple docker images builder handling inter images dependencies

## Install

Install the tool by launching `python setup.py install` as root or `python setup.py install --user`
If you do not have root acces or do not want to bother your co-workers on the same host

## Use

The purpose of this tool is to build docker images taking care of image dependencies.
Meaning, `myimage` has a `FROM parent` appears in a Dockerfile, if `parent` is known as buildable
by the tool, it will be built prior to `myimage` build

The followings are also handled:
- Tag the built images with the last commit hash on the build context
- On-the-fly update of the `FROM` directives to get the latest build tag
- Dockerfiles are pre-processed in order to purge apt/yum caches after install (https://docs.docker.com/engine/articles/dockerfile_best-practices)
- Dockerfiles are pre-processed in order to work-arround yum bug with overlay driver (see
    https://github.com/docker/docker/issues/10180 and
    https://bugzilla.redhat.com/show_bug.cgi?id=1213602#c13)

### Example
`~/.dynker/config.yml`
```
---
images:
    -
        path: docker/*
    -
        path: /home/username/git/otherrepo/
        Dockerfile: docker/*/Dockerfile
```

`docker/dev/Dockerfile`
```
FROM prod
ADD  requirements-dev.txt /tmp/requirements-dev.txt
RUN  pip install -r /tmp/requirements-dev.txt
RUN  py.test tests
```
`docker/prod/Dockerfile`
```
FROM base
ADD  requirements.txt /tmp/requirements.txt
RUN  pip install -r /tmp/requirements.txt
ADD  mylib /usr/local/lib/python3.5/site-packages/mylib
```
`/home/username/git/otherrepo/docker/base/Dockerfile`
```
FROM python:3.5-alpine
RUN  apk update && apk add my-company-package
```
Then, `dynker build dev` will :
 1. build the base image from its sources
 2. build the production image from its sources
 3. build the development image
