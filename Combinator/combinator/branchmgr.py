
import os
import glob
import site
import warnings
import sys
import re
import shutil

_cmdLineQuoteRe = re.compile(r'(\\*)"')
def _cmdLineQuote(s):
    if ' ' in s or '"' in s:
        return '"' + _cmdLineQuoteRe.sub(r'\1\1\\"', s) + '"'
    return s

def popenl(*x):
    popenstr = ' '.join(map(_cmdLineQuote, x))
    print 'Executing:', popenstr
    return os.popen(popenstr)

from xml.dom.minidom import parse

# Yes, I know I wrote microdom, but this is a stdlib feature and microdom is
# not.  this module really can't use *anything* outside the stdlib, because one
# of its primary purposes is managing the path of your Twisted install!!


class BranchManager:
    def __init__(self, svnProjectsDir, sitePathsPath):
        """
        @param svnProjectsDir: a path to a group of SVN repositories arranged
        in the structure:

            <dir>/ProjectName/trunk/
            <dir>/ProjectName/branches/username/branchname/
            <dir>/ProjectName/branches/username/branch2/
            <dir>/Project2/trunk/
            <dir>/Project2/branches/username/branchname/
            <dir>/Project2/branches/username/branch2/

        Combinator will modify this directory by running SVN commands to check
        out new branches, run merges, and similar stuff.

        @param sitePathsPath: A path to a directory of files with this simple
        structure:

            <dir>/ProjectName.bch
            <dir>/Project2.bch

        .bch files in this context are text files which contain the branch name
        of the most current branch for a particular project.  A branch name, in
        this context, is a relative path from the project's SVN /branches
        directory.  For example, the branch path of
        'svn+ssh://example.com/svn/Foo/branches/quasimodo/your-favorite-branch/'
        is 'quasimodo/your-faorite-branch'.

        'trunk' is a special branch path, which, obviously, points to
        'svn+ssh://example.com/svn/Foo/trunk/'


        The path pointing to each branch thus specified will be added not only
        to sys.path, but also as a site directory, so .pth files in it will be
        respected (so that multi-project repositories such as the Divmod
        repository can be activated).
        """

        self.svnProjectsDir = svnProjectsDir
        self.sitePathsPath = sitePathsPath

    def projectBranchDir(self, projectName, branchPath='trunk'):
        if branchPath == 'trunk':
            return os.path.abspath(
                os.path.join(self.svnProjectsDir, projectName, branchPath))
        return os.path.abspath(
            os.path.join(self.svnProjectsDir, projectName, 'branches', branchPath))

    def addPaths(self):
        """
        Add all .bch-file paths as site paths.
        """
        for yth in glob.glob(os.path.join(self.sitePathsPath, "*.bch")):
            projName = os.path.splitext(os.path.split(yth)[-1])[0]
            branchPath = file(yth).read().strip()
            fsPath = self.projectBranchDir(projName, branchPath)
            noTrunk = False
            if not os.path.exists(fsPath):
                if branchPath != 'trunk':
                    warnings.warn(
                        UserWarning,
                        "branch %s:%s at %r does not exist, trying trunk" % (
                        projName, branchPath, fsPath))
                    trunkFsPath = self.projectBranchDir(projName)
            if os.path.isdir(fsPath):
                if fsPath not in sys.path:
                    sys.path.insert(0, fsPath)
                    site.addsitedir(fsPath)
                else:
                    warnings.warn("Duplicate path entry %r" % (projName,),
                                  UserWarning )
            else:
                warnings.warn('Not even trunk existed for %r' % (projName,),
                              UserWarning )



    def changeProjectBranch(self, projectName, branchRelativePath, branchURI=None):
        """
        Swap which branch of a particular project we are 'working on'.  Adjust
        path files to note this difference.
        """
        branchDirectory = self.projectBranchDir(projectName, branchRelativePath)
        trunkDirectory = self.projectBranchDir(projectName)
        if branchRelativePath == 'trunk' and not os.path.exists(trunkDirectory):
            if branchURI is None:
                raise IOError("You need to specify a URI as a 3rd argument to check out trunk")
            os.chdir(self.svnProjectsDir)
            work(popenl("svn", "co", branchURI, trunkDirectory))
        if not os.path.exists(branchDirectory):
            if branchURI is None:
                branchURI = self.projectBranchURI(projectName, branchRelativePath)
            bchDir = os.path.join(self.svnProjectsDir, projectName, 'branches')

            if not os.path.exists(bchDir):
                os.makedirs(bchDir)
            tempname = branchDirectory+".TRUNK"
            ftd = os.path.dirname(tempname)
            if not os.path.exists(ftd):
                os.makedirs(ftd)
            shutil.copytree(trunkDirectory, tempname)
            os.chdir(tempname)
            work(popenl("svn", "revert", ".", '-R'))
            # no really, revert
            statusf = popenl('svn','status')
            for line in statusf.readlines():
                if line[0] == '?':
                    unknownFile = line[7:-1]
                    print 'removing unknown:', unknownFile
                    if os.path.isdir(unknownFile):
                        shutil.rmtree(unknownFile)
                    else:
                        os.remove(unknownFile)
            work(popenl("svn", "switch", branchURI))
            os.chdir('..')
            os.rename(tempname, branchDirectory)

        if not os.path.exists(self.sitePathsPath):
            os.makedirs(self.sitePathsPath)

        f = file(os.path.join(self.sitePathsPath, projectName)+'.bch', 'w')
        f.write(branchRelativePath)
        f.close()


    def projectBranchURI(self, projectName, branchRelativePath):
        trunkDirectory = self.projectBranchDir(projectName)
        if not os.path.exists(trunkDirectory):
            raise IOError("Trunk not found for project %r" % (projectName,))
        doc = parse(file(os.path.join(trunkDirectory, '.svn', 'entries')))
        for entry in doc.documentElement.childNodes:
            if hasattr(entry, 'hasAttribute'):
                if entry.hasAttribute('url'):
                    uri = '/'.join(entry.getAttribute('url').split('/')[:-1])
                    if branchRelativePath == 'trunk':
                        branchURI = uri + '/trunk'
                    else:
                        branchURI = '/'.join([uri, 'branches', branchRelativePath])
                    return branchURI

def work(f):
    x = 0
    fred = f.readline()
    # print 'S:', fred
    while fred:
        fred = f.readline()
        if fred:
            print 'Output:', fred.strip()
cycle = '-\\|/*'

theBranchManager = None

def init(svnProjectsDir, sitePathsPath=None):
    global theBranchManager
    if sitePathsPath is None:
        sitePathsPath = os.path.join(svnProjectsDir, "combinator_paths")
    theBranchManager = BranchManager(svnProjectsDir, sitePathsPath)
    theBranchManager.addPaths()

