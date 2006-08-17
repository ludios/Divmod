_contentTypes = {"image/jpeg" : ["\xff\xd8"],
                 "image/png"  : ["\x89PNG"],
                 "image/gif"  : ["GIF87a", "GIF89a"],
                 "image/vnd.microsoft.icon" : ["\x00\x00\x01\x00"]}

def getImageType(data, ctypes=_contentTypes):
    for (ctype, magics) in ctypes.iteritems():
        for magic in magics:
            if data.startswith(magic):
                return ctype

if __name__ == "__main__":
    import sys
    print getImageType(file(sys.argv[1]).read())
