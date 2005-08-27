
import os
import warnings

def splitall(p):
    car, cdr = os.path.split(p)
    if not cdr:
        return [car]
    else:
        return splitall(car) + [cdr]

def initialize():
    # Am I somewhere I recognize?
    saf = splitall(__file__)
    if not saf[-4:-1] == ['Divmod', 'trunk', 'Combinator']:
        warnings.warn(
            'Combinator sitecustomize located outside of Combinator directory, aborting')
        print saf
        return

    from combinator import branchmgr
    branchmgr.init(os.path.join(*saf[:-4]))

initialize()

