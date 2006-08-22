import textwrap

from nevow import loaders, tags
from nevow.livetrial import testcase

from xmantissa import liveform

class TextInput(testcase.TestCase):
    jsClass = u'Mantissa.Test.Forms'

    def getWidgetDocument(self):
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument',
                                liveform.TEXT_INPUT,
                                unicode,
                                'A text input field: ',
                                default=u'hello world')])
        f.setFragmentParent(self)
        return f


    def submit(self, argument):
        self.assertEquals(argument, u'hello world')



class MultiTextInput(testcase.TestCase):
    jsClass = u'Mantissa.Test.Forms'

    def submit(self, sequence):
        self.assertEquals(sequence, [1, 2, 3, 4])


    def getWidgetDocument(self):
        f = liveform.LiveForm(
                self.submit,
                (liveform.ListParameter('sequence',
                                        int,
                                        4,
                                        'A bunch of text inputs: ',
                                        defaults=(1, 2, 3, 4)),))
        f.setFragmentParent(self)
        return f



class TextArea(testcase.TestCase):
    jsClass = u'Mantissa.Test.TextArea'

    defaultText = textwrap.dedent(u"""
    Come hither, sir.
    Though it be honest, it is never good
    To bring bad news. Give to a gracious message
    An host of tongues; but let ill tidings tell
    Themselves when they be felt.
    """).strip()

    def submit(self, argument):
        self.assertEquals(
            argument.replace('\r\n', '\n'),
            self.defaultText.replace('\r\n', '\n'))


    def getWidgetDocument(self):
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument',
                                liveform.TEXTAREA_INPUT,
                                unicode,
                                'A text area: ',
                                default=self.defaultText)])
        f.setFragmentParent(self)
        return f



class Select(testcase.TestCase):
    jsClass = u'Mantissa.Test.Select'

    def submit(self, argument):
        self.assertEquals(argument, u"apples")


    def getWidgetDocument(self):
        # XXX No support for rendering these yet!
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument', None, unicode)])
        f.docFactory = loaders.stan(tags.form(render=tags.directive('liveElement'))[
            tags.select(name="argument")[
                tags.option(value="apples")["apples"],
                tags.option(value="oranges")["oranges"]],
            tags.input(type='submit', render=tags.directive('submitbutton'))])
        f.setFragmentParent(self)
        return f



class Choice(testcase.TestCase):
    jsClass = u'Mantissa.Test.Choice'

    def submit(self, argument):
        self.assertEquals(argument, 2)


    def getWidgetDocument(self):
        f = liveform.LiveForm(
            self.submit,
            [liveform.ChoiceParameter('argument',
                [('One', 1, False),
                 ('Two', 2, True),
                 ('Three', 3, False)])])
        f.setFragmentParent(self)
        return f



class ChoiceMultiple(testcase.TestCase):
    jsClass = u'Mantissa.Test.ChoiceMultiple'

    def submit(self, argument):
        self.assertIn(1, argument)
        self.assertIn(3, argument)


    def getWidgetDocument(self):
        f = liveform.LiveForm(
            self.submit,
            [liveform.ChoiceParameter('argument',
                [('One', 1, True),
                 ('Two', 2, False),
                 ('Three', 3, True)],
                "Choosing mulitples from a list.",
                multiple=True)])
        f.setFragmentParent(self)
        return f



SPECIAL = object() # guaranteed to fuck up JSON if it ever gets there by
                   # accident.

class Traverse(testcase.TestCase):
    jsClass = u'Mantissa.Test.Traverse'

    def submit(self, argument, group):
        self.assertEquals(argument, u'hello world')
        self.assertEquals(group, SPECIAL)


    def paramfilter(self, param1):
        self.assertEquals(param1, u'goodbye world')
        return SPECIAL


    def getWidgetDocument(self):
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument',
                                liveform.TEXT_INPUT,
                                unicode,
                                'A text input field: ',
                                default=u'hello world'),
             liveform.Parameter('group',
                                liveform.FORM_INPUT,
                                liveform.LiveForm(self.paramfilter,
                                                  [liveform.Parameter
                                                   ('param1',
                                                    liveform.TEXT_INPUT,
                                                    unicode,
                                                    'Another input field: ',
                                                    default=u'goodbye world')]),
                                'A form input group: ',
                                )])
        f.setFragmentParent(self)
        return f
