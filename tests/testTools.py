import os
import subprocess
import tempfile
import unittest
import shutil
import atexit

from dynker.tools import GitHistory



class TestGitHistory(unittest.TestCase) :
    @classmethod
    def setUpClass(cls) :
        cls.origWD = os.getcwd()
        # this is where we will have the reposiroty
        cls.testWD = tempfile.mkdtemp()
        if not os.path.exists(cls.testWD) :
            os.makedirs(cls.testWD)
        # we have created a temporary directory, we are responsible for cleaning it up
        def delete() :
            shutil.rmtree(cls.testWD)
        atexit.register(delete)
        os.chdir(cls.testWD)
        cls.commits = {}
        cls.mtimes = {}
        cls.gitCmd('init', '.')
        cls.addFileAndCommit('README.md','test repository')
        cls.addFile("Some/untracked/file", "with a content")
        cls.addFile("Some/tracked/file/modified/once", ["will be modified once","init commit"])
        cls.addFile("Some/tracked/file/dirty/once", ["will be dirty once","init commit"])
        cls.addFile("Some/tracked/file/modified/twice", ["will be modified twice","init commit"])
        cls.addFile("Some/tracked/file/modified/3-times", ["will be modified 3 times","init commit"])
        cls.addFilesToGit("Some/tracked/file/modified/once", "Some/tracked/file/dirty/once", "Some/tracked/file/modified/twice", "Some/tracked/file/modified/3-times")

        cls.addFile("Some/tracked/file/modified/twice", ["will be modified twice","second commit"])
        cls.addFile("Some/tracked/file/modified/3-times", ["will be modified 3 times","second commit"])
        cls.addFilesToGit("Some/tracked/file/modified/twice", "Some/tracked/file/modified/3-times")

        cls.addFile("Some/tracked/file/modified/once-at-last", ["will be modified once","init commit"])
        cls.addFile("Some/tracked/file/modified/3-times", ["will be modified 3 times","third commit"])
        cls.addFilesToGit("Some/tracked/file/modified/once-at-last", "Some/tracked/file/modified/3-times")
        
        cls.addFile("Some/tracked/file/dirty/once", ["will be dirty once","update not commited"])
        cls.addFile(".gitignore", ["Some/ignored/file"])
        cls.addFile("Some/ignored/file", ["this file is in the ignore list"])

    @classmethod
    def addFile(cls, name, content) :
        dirname = os.path.dirname(name)
        if dirname and not os.path.exists(dirname) :
            os.makedirs(dirname)
        if isinstance(content, (list, tuple)) :
            content = '\n'.join(content)
        file(name, "w").write(content)
        cls.mtimes[name] = [os.lstat(name).st_mtime] + cls.mtimes.get(name, [])

    @classmethod
    def addFileAndCommit(cls, name, *args, **kwds) :
        cls.addFile(name, *args, **kwds)
        cls.addFilesToGit(name)

    @classmethod
    def addFilesToGit(cls, *files, **kwds) :
        message = kwds.get('message', 'commit message')
        out, err = cls.gitCmd('add',*files)
        out, err = cls.gitCmd('commit', '-m', message)
        sha, err = cls.gitCmd('log', '-n', '1', '--pretty=format:%H')
        mtime, err = cls.gitCmd('log', '-n', '1', '--pretty=format:%ct')
        mtime = float(mtime)
        for f in files :
            cls.commits[f] = [sha]+cls.commits.get(f, [])
            cls.mtimes[f] = [mtime]+cls.mtimes[f][:-1]

    @classmethod
    def gitCmd(cls, *args) :
        return subprocess.Popen(['git']+list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    @classmethod
    def tearDownClass(cls) :
        os.chdir(cls.origWD)

    def testGetter(self) :
        git = GitHistory.Get()
        if git is not GitHistory.Get() :
            self.fail("GitHistory.Get should return the exact same object any time")

    def testLastCommitNotunderGit(self) :
        self.assertEquals(GitHistory.Get().getLastCommit("Some/untracked/file"), None)
        self.assertEquals(GitHistory.Get().getLastCommit("Some/ignored/file"), None)

    def testLastCommitedFile(self) :
        # providing the exact name tracked by git
        self.assertEquals(GitHistory.Get().getLastCommit("Some/tracked/file/modified/once-at-last"),self.commits["Some/tracked/file/modified/once-at-last"][0])
        # providing some manually generated path, not mormalized
        self.assertEquals(GitHistory.Get().getLastCommit("./Some/tracked//file////modified/once-at-last"),self.commits["Some/tracked/file/modified/once-at-last"][0])

        self.assertEquals(GitHistory.Get().getLastCommit("Some/tracked/", strict=False), self.commits["Some/tracked/file/modified/once-at-last"][0], "With strict matching of the filename, it should not be possible to retrieve last commit on a directory")
        self.assertEquals(GitHistory.Get().getLastCommit("Some/tracked/"), None, "With strict matching of the filename, it should not be possible to retrieve last commit on a directory")

        self.assertEquals(GitHistory.Get().getLastCommit("Some/untracked/", srict=False), None)

    def testDirtyState(self) :
        self.assertTrue(GitHistory.Get().isDirty("Some/tracked/file/dirty/once"))
        self.assertTrue(GitHistory.Get().isDirty("Some/untracked/file"))
        self.assertTrue(GitHistory.Get().isDirty("Some/dirty/file"))
        self.assertFalse(GitHistory.Get().isDirty("Some/tracked/file/modified/once"))

    def testDirtyStateGetMTime(self) :
        for f in self.mtimes.keys() :
            self.assertEquals(GitHistory.Get().getMTime(f), self.mtimes[f][0])


