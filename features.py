"""Feature extractor for UCCA scene-evoking classifier.

There are two kinds of features: lexical features extracted from the the
classified target word, and context features extracted from its instances
in non-UCCA corpora. In addition, extracting the class for the word from
UCCA passages is also covered.

"""

import argparse
import sys

from itertools import islice


DEFAULT_CHUNK_SIZE = 2 ** 20


def chunks(f, size=DEFAULT_CHUNK_SIZE):
    """Yields chunks of lines from a file until exhausted.

    Args:
        f: file to yield lines from
        size: hint to readlines() of how many bytes each yield should contain.

    Yields:
        list of strings (lines).

    """
    while True:
        x = f.readlines(size)
        if x:
            yield x
        else:
            raise StopIteration


def tokenize(sentences):
    """list of string sentences ==> list of tuples of stripped tokens"""
    return [tuple(x.strip().split()) for x in sentences if x.strip()]


def parse_ngram_line(line):
    """tab-separated ngram line ==> count (int), ngram (tuple)"""
    count, ngram = line.strip().split('\t')
    return int(count), tuple(ngram.split())


def extract_ngrams(size, sentences, counts):
    """Extracts all ngrams of the given size from the sentences.

    Args:
        size: the N parameter of the ngrams to extract
        sentences: sequence (can be generator) of tuples of strings, each
            is a token.
        counts: previous ngram dictionary to start with.
            This dictionary is changed by the method.

    Returns:
        counts dictionary (the same as the argument).

    """
    for s in sentences:
        if len(s) < size:
            continue
        for i in range((len(s) - size + 1)):
            counts[s[i:i + size]] = counts.get(s[i:i + size], 0) + 1
    return counts


def filter_ngrams(lines, *, threshold=1, exclude=frozenset()):
    """Filters the given ngrams according to the keyword parameters.

    Args:
        lines: list of tab-seprated strings of count-ngram pairs,
            will be modified.
        threshold: what is the minimum count to keep the ngram in
        exclude: set of tokens which make the ngram being omitted.
            If one of the tokens appear in any position in the ngram, it
            is being excluded from the results.

    Returns:
        lines argument (after modification)

    """
    def _discard(line):
        count, ngram = parse_ngram_line(line)
        return (count < threshold or exclude & set(ngram))

    indices = [i for i, line in enumerate(lines) if _discard(line)]
    for i in reversed(indices):
        del lines[i]
    return lines


def merge_ngrams(lines):
    """Merge adjacent ngram counts if they are refering to the same ngram.

    Assumes lines are sorted alphabetically by ngram, and removes duplicate
    counts by adding them to one line.

    Args:
        lines: list of tab-separated strings of count-ngram pairs,
            will be modified

    Returns:
        lines argument (after modification)

    """
    total = len(lines)
    i = 0
    while i + 1 < total:
        count1, ngram1 = parse_ngram_line(lines[i])
        count2, ngram2 = parse_ngram_line(lines[i + 1])
        if ngram1 == ngram2:
            lines[i] = '\t'.join(str(count1 + count2), ngram1) + '\n'
            del lines[i + 1]
            total -= 1
        else:
            i += 1
    return lines


def print_progress(current, updated=[0]):
    """Prints progress to stderr by adding current to updated[0] each time."""
    updated[0] = updated[0] + current
    print("Processed: " + str(updated[0]), file=sys.stderr)


def parse_cmd():
    """Parses and validates cmd line arguments, then return them."""
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('ngrams',))
    parser.add_argument('action', choices=('extract', 'filter', 'merge'))
    parser.add_argument('--ngram_size', type=int, default=1)
    parser.add_argument('--sort', action='store_true')
    parser.add_argument('--exclude')
    parser.add_argument('--threshold', type=int, default=1)

    args = parser.parse_args()
    if args.exclude:
        with open(args.exclude) as f:
            tokens = f.readlines()
        args.exclude = {x.strip() for x in tokens}
    else:
        args.exclude = set()

    return args


def main():
    args = parse_cmd()

    if args.command == 'ngrams' and args.action == 'extract':
        counts = {}
        for data in chunks(sys.stdin):
            sentences = tokenize(data)
            counts = extract_ngrams(args.ngram_size, sentences, counts)
            print_progress(len(sentences))
        print("Finished processing", file=sys.stderr)
        if args.sort:
            sorted_counts = sorted(counts.items(), key=lambda x: x[1],
                                   reverse=True)
            print('\n'.join('\t'.join([str(value), ' '.join(ngram)])
                        for ngram, value in sorted_counts))
        else:
            for ngram, value in counts.items():
                print('\t'.join([str(value), ' '.join(ngram)]))

    if args.command == 'ngrams' and args.action == 'filter':
        for data in chunks(sys.stdin):
            print_progress(len(data))
            filtered = filter_ngrams(data, threshold=args.threshold,
                                     exclude=args.exclude)
            print(*filtered, sep='')

    if args.command == 'ngrams' and args.action == 'merge':
        data = sys.stdin.readlines()  # no chunks, separates adjacent lines
        merged = merge_ngrams(data)
        print(*merged, sep='')


if __name__ == '__main__':
    main()
