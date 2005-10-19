adjacentNs = lambda s, n: (s[i:i+n] for i in xrange(len(s)-1))

def mchain(string, tokenizer=str.split, length=1):
    chains = dict()

    for portion in adjacentNs(tokenizer(string), length+1):
        parent = chains
        for (i, word) in enumerate(portion):
            if i+1 == len(portion):
                parent.setdefault(word, 0)
                parent[word] += 1
            else:
                parent = parent.setdefault(word, dict())

    return chains

if __name__ == '__main__':

    chains = mchain("""we face a lot of issues with gibberish in this world i think it probably has a lot
                       to with the amount of noise words that you would find in a given piece of text
                       lots of and and the and he and she and these are the kinds of problems that we face
                       i cannot really see a likely way for us to over this soup of repetition, perhaps we
                       are indeed doomed to failure""", length=3)

    from pprint import pprint
    pprint(chains)
