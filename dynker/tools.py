import os
import git
import logging

class GitHistory(object) :
    def __init__(self) :
        self.repo = git.Repo()
        self.hist = self.repo.iter_commits()
        self.MTimes = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    def isDirty(self, *files) :
        files = set(map(os.path.normpath,files))
        untracked = files - set(map(lambda e:os.path.normpath(e.path), git.Repo().index.entries.itervalues()))
        if  untracked :
            self.logger.debug("%r are untracked ==> dirty state", untracked)
            return True
        for file in files :
            file = os.path.normpath(file)
            for diff in git.Repo().head.commit.diff(None) :
                if diff.b_path == file or diff.a_path == file :
                    logging.debug("%s is dirty",file)
                    return True
        self.logger.debug("%r are clean",files)
        return False

    def getLastCommit(self, *files, **kwds) :
        files = list(files) + kwds.get('files',[])
        strict = kwds.get('strict', True)
        files = set(map(os.path.normpath,files))
        self.logger.debug("Getting latest commit on set of files: %r"%files)
        for commit in self.repo.iter_commits() :
            if strict :
                if files & set(commit.stats.files.keys()) :
                    return commit.hexsha
            else :
                for f in commit.stats.files.keys() :
                    for f2 in files :
                        if f.startswith(f2) :
                            self.logger.debug("commit %s changed file %s, matching our requirement %s", commit.hexsha, f, f2)
                            return commit.hexsha
                        else :
                            self.logger.debug("commit %s changed file %s, but not in our requirement %s", commit.hexsha, f, f2)
        return None

    def getMTime(self, file) :
        file = os.path.normpath(file)
        if file in self.repo.untracked_files or self.isDirty(file) :
            mtime = os.lstat(file).st_mtime
            self.logger.debug("%s is dirty/untracked, returning its system mtime: %f", file, mtime)
            return mtime

        try :
            mtime = self.MTimes[file]
            self.logger.debug("%s has been last modified in git at %d",file, mtime)
            return mtime
        except KeyError :
            pass

        for commit in self.hist :
            for f in commit.stats.files.keys() :
                self.MTimes[f] = commit.committed_date
            try :
                mtime = self.MTimes[file]
                self.logger.debug("%s has been last modified in git at %d",file, mtime)
                return mtime
            except KeyError :
                pass
        mtime = os.lstat(file).st_mtime
        self.logger.debug("%s is not under scm, returning its system mtime: %f", file, mtime)
        return mtime

    @classmethod
    def Get(cls) :
        try :
            cls.Git
        except AttributeError :
            cls.Git = cls()
        return cls.Git

