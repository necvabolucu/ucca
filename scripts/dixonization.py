"""Identifies and categorizes words according to Dixon's verb list."""

import argparse
import xml.etree.ElementTree as ETree

from ucca import lex, convert, scenes


class Stats:
    def __init__(self):
        self.heads = []
        self.lemmas = []
        self.no_cats = []
        self.fulls = []


def main():
    """Runs DixonIdentifier and gathers statistics."""
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='*',
                        help="Site XML files to operate on")
    parser.add_argument('-v', '--verbs',
                        default='/home/beka/thesis/resources/dixon-verbs.xml',
                        help="Dixon's verb categories in XML file")
    parser.add_argument('-c', '--collins',
                default='/home/beka/thesis/resources/collins/collins.pickle',
                help="Collins parsed dictionary in pickle file")
    parser.add_argument('-w', '--wiktionary',
            default='/home/beka/thesis/resources/enwikt-defs-latest-en.tsv',
            help="Wiktionary definitions only in tab-separated format")

    args = parser.parse_args()
    eng = lex.DixonIdentifier(args.verbs, args.collins, args.wiktionary)
    stats = Stats()
    for path in args.filename:
        run_file(path, eng, stats)
    stats.heads.sort(key=str)  # by scene
    stats.lemmas.sort(key=lambda x: str(x[1]))  # by head
    stats.no_cats.sort(key=lambda x: str(x[1]))  # by head
    stats.fulls.sort(key=lambda x: str(x[-1]))  # by category
    print('=== NO HEADS ({}) ==='.format(len(stats.heads)))
    for s in stats.heads:
        print(str(s))
    print('=== LEMMAS ({}) ==='.format(len(stats.lemmas)))
    for s, h in stats.lemmas:
        print("{}\t{}".format(str(h), str(s)))
    print('=== NO CATEGORIES ({}) ==='.format(len(stats.no_cats)))
    for out in stats.no_cats:
        print('\t'.join([str(x) for x in out]))
    print('=== FULLS ({}) ==='.format(len(stats.fulls)))
    for out in stats.fulls:
        print('\t'.join([str(x) for x in out]))


def run_file(path, eng, stats):
    """Site XML file ==> prints list of sceneness results"""
    with open(path) as f:
        root = ETree.ElementTree().parse(f)
    passage = convert.from_site(root)

    sc = scenes.extract_possible_scenes(passage)
    heads = [scenes.extract_head(x) for x in sc]

    for s, h in zip(sc, heads):
        if h is None:
            stats.heads.append(s)
            continue
        out = eng.get_categories(s, h)
        if out == 'implicit':
            stats.heads.append(s)
        elif out == 'no base form':
            stats.lemmas.append((s, h))
        elif out[2]:
            stats.fulls.append((s, h) + out)
        else:
            stats.no_cats.append((s, h) + out)


if __name__ == '__main__':
    main()