
"""
Try to automate most of the release process for Divmod projects.
"""

import os, sys

from twisted.python.reflect import namedModule
from twisted.python.versions import Version
from twisted.python.filepath import FilePath
from twisted.python.release import (
    sh, inputNewVersion, replaceProjectVersion,
    runChdirSafe, Project)

from combinator.branchmgr import theBranchManager

def release(rootPath, projectNames, prompt=True):
    """
    Prompt for new versions of the indicated projects and re-write their
    version information.

    @type rootPath: L{FilePath}
    @param rootPath: The root of the working copy from which to release.

    @param projectNames: A C{list} of C{str} which name Python modules for
    projects in the Divmod repository.
    """
    if not projectNames:
        raise SystemExit("Specify some package names to release.")


    # Turn names into entities in the filesystem.
    projectObjects = []
    for projName in projectNames:
        for pfx in '', 'x':
            try:
                projPackage = namedModule(pfx + projName)
            except ImportError:
                pass
            else:
                projPackagePath = FilePath(projPackage.__file__)
                break
        else:
            raise SystemExit("Failed to find Python package for %s." % (projName,))

        realName = projPackagePath.parent().parent().basename()
        projectObjects.append(Project(name=realName,
                                      initPath=projPackagePath,
                                      package=projPackage))
        print 'Found', projName, 'as', realName, 'at', projPackagePath.path

    # Gather version information and change _version.py files to contain new
    # version number.
    for proj in projectObjects:
        projVersion = inputNewVersion(proj)
        if projVersion is None:
            projVersion = proj.package.version
            projVersion = projVersion.major, projVersion.minor, projVersion.micro
        projVersionFilePath = proj.initPath.sibling('_version.py')
        replaceProjectVersion(
            projVersionFilePath.path,
            projVersion)
        proj.version = Version(proj.name, *projVersion)
        print 'Updated version in', projVersionFilePath.path

    # Commit
    cmd = 'svn commit %(rootPath)s -m "Version updates for release"'
    sh(cmd % {'rootPath': rootPath.path},
       null=False,
       prompt=prompt)

    # Export
    branchRelativePath = theBranchManager.currentBranchFor('Divmod')
    branchURI = theBranchManager.projectBranchURI(
        'Divmod', branchRelativePath)
    exportPath = FilePath('.release').temporarySibling()
    cmd = 'svn export %(rootPath)s %(exportPath)s'
    sh(cmd % {'rootPath': rootPath.path, 'exportPath': exportPath.path},
       null=False,
       prompt=prompt)

    # sdist
    for proj in projectObjects:
        @runChdirSafe
        def makeSourceRelease():
            os.chdir(exportPath.child(proj.name).path)
            cmd = '%(python)s setup.py sdist'
            sh(cmd % {'python': sys.executable},
               null=False,
               prompt=prompt)

    # unpack sdist
    for proj in projectObjects:
        @runChdirSafe
        def unpackSourceRelease():
            projectExport = exportPath.child(proj.name)
            os.chdir(projectExport.child('dist').path)
            cmd = 'tar xzf %(projectName)s-%(projectVersion)s.tar.gz'
            sh(cmd % {'projectName': proj.name,
                      'projectVersion': proj.version.short()},
               null=False,
               prompt=prompt)

    # install
    installPath = FilePath('.install').temporarySibling()
    for proj in projectObjects:
        @runChdirSafe
        def installSourceRelease():
            projectExport = exportPath.child(proj.name)
            projectDir = '%s-%s' % (proj.name, proj.version.short())
            unpackPath = projectExport.child('dist').child(projectDir)
            os.chdir(unpackPath.path)
            cmd = '%(python)s setup.py install --prefix %(installPath)s'
            sh(cmd % {'python': sys.executable, 'installPath': installPath.path},
               null=False,
               prompt=prompt)

    # test
    siteInstallPath = installPath.child('lib').child('python2.4').child('site-packages')
    for proj in projectObjects:
        @runChdirSafe
        def testSourceInstall():
            cmd = 'PYTHONPATH=%(installPath)s:$PYTHONPATH trial %(projectName)s'
            sh(cmd % {'installPath': siteInstallPath.path,
                      'projectName': proj.initPath.parent().basename()},
               null=False,
               prompt=prompt)

    # tag
    tagRootURI = 'svn+ssh://divmod.org/svn/Divmod/tags/releases'
    for proj in projectObjects:
        @runChdirSafe
        def tagRelease():
            source = '%(branchURI)s/%(projectName)s'
            dest = '%(tagRootURI)s/%(projectName)s-%(projectVersion)s'
            cmd = 'svn cp %s %s -m "Tagging release"' % (source, dest)
            sh(cmd % {'branchURI': branchURI,
                      'projectName': proj.name,
                      'tagRootURI': tagRootURI,
                      'projectVersion': proj.version.short()},
               null=False,
               prompt=prompt)

    # aggregate tgzs
    releasePath = FilePath('releases')
    if not releasePath.isdir():
        releasePath.makedirs()

    for proj in projectObjects:
        @runChdirSafe
        def makeSourceRelease():
            projectExport = exportPath.child(proj.name)
            releaseFile = '%s-%s.tar.gz' % (proj.name,
                                            proj.version.short())
            projectPath = projectExport.child('dist').child(releaseFile)
            projectPath.moveTo(releasePath.child(releaseFile))

if __name__ == '__main__':
    release(FilePath('.'), sys.argv[1:])
