import unittest
import docker
import dynker.cmd

docker_error = None
no_docker = False
try:
    docker.Client.from_env().version()
except Exception as e:
    docker_error = e
    no_docker = True

@unittest.skipIf(no_docker, "Failed to connect to docker host, error: %s" % docker_error)
class TestDynker(unittest.TestCase):
    def test_build_dynker(self):
        dynker.cmd.main(['dynker', 'build', 'dynker'])
