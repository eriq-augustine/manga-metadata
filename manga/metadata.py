"""
Handle manga metadata.
"""

import abc
import argparse
import os
import re
import sys
import urllib.request

import Levenshtein
import bs4

TASK_FETCH = 'fetch'
TASK_READ = 'read'
TASK_SET = 'set'
TASK_UPDATE = 'update'

TASKS = [
    TASK_FETCH,
    TASK_READ,
    TASK_SET,
    TASK_UPDATE,
]

DEFAULT_OUTPUT_PATH = 'ComicInfo.xml'

class Source(abc.ABC):
    def __init__(self, cache_dir = None, **kwargs):
        self._cache_dir = cache_dir

    @abc.abstractmethod
    def search(self, name):
        """
        Returns: [
            (id, name, description),
            ...
        ]
        """

        pass

    @abc.abstractmethod
    def fetch(self, id):
        """
        Returns: {
            ...
        }
        """

        pass

    def _fetch_url(self, url):
        cache_path = None
        if (self._cache_dir is not None):
            cache_path = os.path.join(self._cache_dir, url)
            if (os.path.isfile(cache_path)):
                with open(cache_path, 'r') as file:
                    return file.read()

        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')

        if (cache_path is not None):
            os.makedirs(os.path.dirname(cache_path), exist_ok = True)
            with open(cache_path, 'w') as file:
                file.write(html)

        return html

class MangaUpdates(Source):
    BASE_SEARCH_URL = 'https://www.mangaupdates.com/series.html?search=%s'
    BASE_FETCH_URL = 'https://www.mangaupdates.com/series/%s'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def search(self, name):
        name = re.sub(r'\s+', ' ', name).strip().replace(' ', '+')
        url = MangaUpdates.BASE_SEARCH_URL % (name)

        html = self._fetch_url(url)
        document = bs4.BeautifulSoup(html, 'html.parser')

        results = []
        for node in document.select('div.col-12.col-lg-6.p-3.text'):
            title_link = node.select('div.flex-column > div.text > a[alt="Series Info"]')

            if (len(title_link) != 1):
                continue
            title_link = title_link[0]

            match = re.match(r'^.*www\.mangaupdates\.com/series/([^/]+)/.*$', title_link.get('href'))
            if (match is None):
                continue

            id = match.group(1)
            title = title_link.get_text()

            year_node = node.select('div.d-flex.flex-column.h-100 div.text:last-child')
            if (len(year_node) != 1):
                continue
            year_node = year_node[0]

            match = re.match(r'^(\d{4}).*$', year_node.get_text())
            if (match is None):
                year = '???'
            else:
                year = match.group(1)

            genres_node = node.select('div.textsmall a')
            if (len(genres_node) != 1):
                continue
            genres_node = genres_node[0]

            genres = genres_node.get('title')

            results.append((id, title, "%s (%s) - %s" % (title, year, genres)))

        return results

    def fetch(self, id):
        metadata = {}

        url = MangaUpdates.BASE_FETCH_URL % (id)
        html = self._fetch_url(url)
        document = bs4.BeautifulSoup(html, 'html.parser')

        # TEST
        print(document)

        return metadata

def _get_int(lower, upper, prompt):
    prompt += ' (Enter "q" or "quit" to exit.): '

    while (True):
        try:
            text = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

        if (text == ''):
            continue
        
        if (text.lower() in ['q', 'quit']):
            return None

        if (re.match(r'^\s*-?\d+\s*$', text) is None):
            continue

        value = int(text)

        if ((value < lower) or (value > upper)):
            print("Int is out of bounds, must be in [%d, %d]." % (lower, upper))
            continue

        return value

def fetch(config):
    name = config.get('input_value')
    if (name is None):
        raise ValueError("No name provided to fetch.")

    source = MangaUpdates(**config)

    results = source.search(name)
    if (len(results) == 0):
        print("No results found matching name '%s'." % name)
        return 1

    id, title = _pick_result(name, results, **config)
    if (id is None):
        print("No matching result selected.")
        return 0

    metadata = source.fetch(id)

    # TEST
    print(metadata)

def _pick_result(name, results, use_first = False, **kwargs):
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

    index = _get_int(0, len(sim_results), "Enter index of desired result.")
    if (index is None):
        return None, None

    return sim_results[index][1][0], sim_results[index][1][1]

def main(args):
    config = vars(args)

    if (args.task == TASK_FETCH):
        return fetch(config)
    elif (args.task == TASK_READ):
        # TODO
        pass
    elif (args.task == TASK_SET):
        # TODO
        pass
    elif (args.task == TASK_UPDATE):
        # TODO
        pass
    else:
        raise ValueError("Unknown task '%s'." % (task))

    return 0

def _load_args():
    parser = argparse.ArgumentParser(description = "Manage manga metadata.")

    parser.add_argument('task',
        action = 'store', type = str, choices = TASKS,
        help = 'The task to run.')

    parser.add_argument('--cache', dest = 'cache_dir',
        action = 'store', type = str, default = None,
        help = 'a directory to use for caching (don\'t cache if not specified)')

    parser.add_argument('--first', dest = 'use_first',
        action = 'store_true', default = False,
        help = 'when presented with choices, always choose the first option and do not prompt (default: %(default)s)')

    parser.add_argument('-i', '--input', dest = 'input_value',
        action = 'store', type = str, default = None,
        help = 'the input for the task')

    parser.add_argument('-o', '--output', dest = 'output_path',
        action = 'store', type = str, default = None,
        help = 'the path to write the output of the task')

    return parser.parse_args()

if (__name__ == '__main__'):
    sys.exit(main(_load_args()))
