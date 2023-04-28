"""
Handle manga metadata.
"""

import abc
import argparse
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree

import Levenshtein
import bs4

import manga.metadata.common
import manga.metadata.sources

DEFAULT_OUTPUT_PATH = 'ComicInfo.xml'

def fetch(config):
    name = config['name']
    if (name is None):
        raise ValueError("No name provided to fetch.")

    source = manga.metadata.sources.MangaUpdates(**config)

    results = source.search(name)
    if (len(results) == 0):
        print("No results found matching name '%s'." % name)
        return 1

    id, title = _pick_result(name, results, use_first = config['use_first'])
    if (id is None):
        print("No matching result selected.")
        return 0

    metadata = source.fetch(id)

    out_path = config.get('output_path')
    if (out_path is not None):
        print("Writing metadata to '%s'." % (out_path))
        metadata.write_xml(out_path)

    if (config['stdout']):
        print("Writing metadata to stdout.")
        print(metadata.to_json())

def _pick_result(name, results, use_first = False):
    if (len(results) == 1):
        return results[0][0], results[0][1]

    sim_results = [(Levenshtein.ratio(name.lower(), result[1].lower()), result) for result in results]
    sim_results.sort(reverse = True)

    print("Found %d possible results." % (len(sim_results)))

    if (use_first):
        print("Automatically choosing first result.")
        return sim_results[0][1][0], sim_results[0][1][1]

    for i in range(len(sim_results)):
        sim_score, (id, title, description) = sim_results[i]
        print("%02d -- %s (Sim: %1.3f) --- %s" % (i, title, sim_score, description))

    index = manga.metadata.common.get_int(0, len(sim_results), "Enter index of desired result.")
    if (index is None):
        return None, None

    return sim_results[index][1][0], sim_results[index][1][1]

def main(args):
    config = vars(args)
    return fetch(config)

def _load_args():
    parser = argparse.ArgumentParser(description = "Manage manga metadata.")

    parser.add_argument('name',
        action = 'store', type = str,
        help = 'The name of the manga to fetch metadata for')

    parser.add_argument('--cache', dest = 'cache_dir',
        action = 'store', type = str, default = None,
        help = 'a directory to use for caching (don\'t cache if not specified)')

    parser.add_argument('--first', dest = 'use_first',
        action = 'store_true', default = False,
        help = 'when presented with choices, always choose the first option and do not prompt (default: %(default)s)')

    parser.add_argument('--stdout', dest = 'stdout',
        action = 'store_true', default = False,
        help = 'output results to stdout')

    parser.add_argument('-o', '--output', dest = 'output_path',
        action = 'store', type = str, default = None,
        help = 'the path to write the output to (as XML))')

    return parser.parse_args()

if (__name__ == '__main__'):
    sys.exit(main(_load_args()))
