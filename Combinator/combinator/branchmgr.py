
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

def prompt(s):
    p = os.getcwd().replace(os.path.expanduser('~'), '~')
    return p + '$ ' + s

def runcmd(*x):
    popenstr = ' '.join(map(_cmdLineQuote, x))
    print prompt(popenstr)

    pipe = os.popen(popenstr)
    output = pipe.read()
    code = pipe.close() or 0

    print 'C: ' + '\nC: '.join(output.splitlines())
    if os.name == 'nt':
        # There is nothing we can possibly do with this error code.
        return output
    if os.WIFSIGNALED(code):
        raise ValueError("Command: %r exited with signal: %d" % (
            popenstr, os.WTERMSIG(code)))
    elif os.WIFEXITED(code):
        status = os.WEXITSTATUS(code)
        if status:
            raise ValueError("Command: %r exited with status: %d" % (
                popenstr, status))
        else:
            return output
    else:
        raise ValueError("Command: %r exited with unexpected code: %d" % (
            popenstr, code))

from xml.dom.minidom import parse

# Yes, I know I wrote microdom, but this is a stdlib feature and microdom is
# not.  this module really can't use *anything* outside the stdlib, because one
# of its primary purposes is managing the path of your Twisted install!!

def addSiteDir(fsPath):
    if fsPath not in sys.path:
        sys.path.insert(0, fsPath)
        site.addsitedir(fsPath)
    elif 0:                     # We SHOULD emit a warning here, but all kinds
                                # of tests set PYTHONPATH invalidly and cause
                                # havoc.
        warnings.warn("Duplicate path entry %r" % (fsPath,),
                      UserWarning )



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
        self.binCachePath = os.path.join(sitePathsPath, 'bincache')

    def projectBranchDir(self, projectName, branchPath='trunk'):
        if branchPath == 'trunk':
            return os.path.abspath(
                os.path.join(self.svnProjectsDir, projectName, branchPath))
        return os.path.abspath(
            os.path.join(self.svnProjectsDir, projectName, 'branches', branchPath))


    def addPaths(self):
        for fsp in self.getPaths():
            addSiteDir(fsp)

    def getCurrentBranches(self):
        for yth in glob.glob(os.path.join(self.sitePathsPath, "*.bch")):
            projName = os.path.splitext(os.path.split(yth)[-1])[0]
            branchPath = file(yth).read().strip()
            yield projName, branchPath

    def getPaths(self):
        """ Yield all .bch-file paths as well as a locally-installed directory.
        """
        for projName, branchPath in self.getCurrentBranches():
            fsPath = self.projectBranchDir(projName, branchPath)
            noTrunk = False
            if not os.path.exists(fsPath):
                if branchPath != 'trunk':
                    m = "branch %s:%s at %r does not exist, trying trunk" % (
                        projName, branchPath, fsPath)
                    warnings.warn(m, UserWarning)
                    trunkFsPath = self.projectBranchDir(projName)
            if os.path.isdir(fsPath):
                yield fsPath
            else:
                warnings.warn('Not even trunk existed for %r' % (projName,),
                              UserWarning )

        # platform-specific entry

        majorMinor = sys.version[0:3]
        if sys.platform.startswith('win'):
            yield (os.path.abspath(
                    os.path.expanduser("~/Python/Lib/site-packages")))
        elif sys.platform != 'darwin':
            # Darwin already has appropriate user-installation directories set up.
            yield (os.path.abspath(
                    os.path.expanduser("~/.local/lib/python%s/site-packages" % (majorMinor,))))

    def currentBranchFor(self, projectName):
        return file(os.path.join(self.sitePathsPath, projectName)+'.bch').read().strip()

    def newProjectBranch(self, projectName, branchName):
        trunkURI = self.projectBranchURI(projectName, 'trunk')
        branchURI = self.projectBranchURI(projectName, branchName)
        runcmd('svn', 'cp', trunkURI, branchURI, '-m',
               'Branching to %r' % (branchName,))
        self.changeProjectBranch(projectName, branchName, revert=False)

    def mergeProjectBranch(self, projectName):
        currentBranch = self.currentBranchFor(projectName)
        if currentBranch == "trunk":
            raise ValueError("Cannot merge trunk")
        branchDir = self.projectBranchDir(projectName, currentBranch)
        os.chdir(branchDir)
        rev = None
        for node in parse(os.popen("svn log --stop-on-copy --xml")
                          ).documentElement.childNodes:
            if hasattr(node, 'getAttribute'):
                rev = node.getAttribute("revision")
        if rev is None:
            raise IOError("No revision found")
        trunkDir = self.projectBranchDir(projectName)
        print 'Swapping to', trunkDir
        os.chdir(trunkDir)
        runcmd('svn', 'up')
        runcmd('svn', 'merge',
               branchDir + "/@" + rev,
               branchDir + "/@HEAD")
        self.changeProjectBranch(projectName, 'trunk')

    def changeProjectBranch(self, projectName, branchRelativePath,
                            branchURI=None, revert=True):
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
            runcmd("svn", "co", branchURI, trunkDirectory)
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
            try:
                shutil.copytree(trunkDirectory, tempname)
            except KeyboardInterrupt:
                shutil.rmtree(tempname)
                raise
            os.chdir(tempname)
            if revert:
                runcmd("svn", "revert", ".", '-R')
                # no really, revert
                statusf = runcmd('svn','status','--no-ignore')
                for line in statusf.splitlines():
                    if line[0] == '?' or line[0] == 'I':
                        unknownFile = line[7:].strip()
                        print 'removing unknown:', unknownFile
                        if os.path.isdir(unknownFile):
                            shutil.rmtree(unknownFile)
                        else:
                            os.remove(unknownFile)
            runcmd("svn", "switch", branchURI)
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

theBranchManager = None

def splitall(p):
    car, cdr = os.path.split(p)
    if not cdr:
        return [car]
    else:
        return splitall(car) + [cdr]

def getDefaultPath():
    # Am I somewhere I recognize?
    saf = splitall(__file__)
    if not saf[-5:-2] == ['Divmod', 'trunk', 'Combinator']:
        warnings.warn(
            'Combinator sitecustomize located outside of Combinator directory, aborting')
        return

    return os.path.join(*saf[:-5])

def init(svnProjectsDir=None, sitePathsPath=None):
    global theBranchManager
    if theBranchManager is not None:
        return theBranchManager
    if svnProjectsDir is None:
        svnProjectsDir = getDefaultPath()
    if sitePathsPath is None:
        sitePathsPath = os.path.join(svnProjectsDir, "combinator_paths")
    theBranchManager = BranchManager(svnProjectsDir, sitePathsPath)
    theBranchManager.addPaths()
    return theBranchManager

