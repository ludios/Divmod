from twisted.trial.unittest import TestCase
from clickchronicle.searchparser import parseSearchString
from operator import eq as op_eq

class SearchParserTestCase(TestCase):
    def assertUniform(self, *sequences):
        msg = 'not uniform: %s' % ','.join(repr(i) for i in sequences)
        self.failUnless(reduce(op_eq, (sorted(s) for s in sequences)), msg)

    def testPlainStrings(self):
        positive = ['hello', 'hello world', 'goodbye cruel world']
        for s in positive:
            self.assertUniform(s.split(), parseSearchString(s))
                                              
    def testQuoting(self):
        positive = {'hello "cruel world"'  : ['hello', '"cruel world"'],
                    'squeamish "ossifrage"' : ['squeamish', '"ossifrage"'],
                    '"a" "b" "c "de""' : ['"a"', '"b"', '"c "', 'de""']}
        for (source, expected) in positive.iteritems():
            self.assertUniform(expected, parseSearchString(source))

    def testNegation(self):
        positive = {'hello -world' : ['hello', 'NOT world'],
                    'hello -"computer programs"' : ['hello', 'NOT "computer programs"'],
                    'hello -world -"a b c"' : ['hello', 'NOT world', 'NOT "a b c"'],
                    'hello -"a" -"b" -c "d"' : ['hello', 'NOT "a"', 'NOT "b"', 'NOT c', '"d"'],
                    'gcc x.c -03 -v' : ['gcc', 'x.c', 'NOT 03', 'NOT v']}

        for (source, expected) in positive.iteritems():
            self.assertUniform(expected, parseSearchString(source))
        
        
