from axiom.test.historic import stubloader
from xmantissa.signup import PasswordReset

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        self.store.findUnique(PasswordReset)
