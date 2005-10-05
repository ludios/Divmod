# could very easily be changed to return the actual mime-type, 
# but we dont really need that at the moment

_prefixes = ["\xff\xd8", "\x89PNG", "GIF87a", "GIF89a", "\x00\x00\x01\x00"]

def isImage(FLO, spellbook=_prefixes):
    FLO.seek(0)
    fprefix = ""
    found = False

    for spell in sorted(spellbook, key=len):
        fprefix += FLO.read(len(spell) - len(fprefix))
        if fprefix == spell:
            found = True
            break

    FLO.seek(0)
    return found
