
import sys
from combinator.branchmgr import theBranchManager

theBranchManager.changeProjectBranch(*sys.argv[1:])

