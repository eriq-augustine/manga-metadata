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

class Metadata(object):
    COMIC_INFO_KEY_ORDER = [
        'Title', 'Series', 'Number', 'Count', 'Volume',
        'AlternateSeries', 'AlternateNumber', 'AlternateCount',
        'Summary', 'Notes', 'Year', 'Month', 'Day',
        'Writer', 'Penciller', 'Inker', 'Colorist', 'Letterer', 'CoverArtist', 'Editor', 'Publisher',
        'Imprint', 'Genre', 'Web', 'PageCount', 'LanguageISO', 'Format', 'BlackAndWhite', 'Manga',
        'Characters', 'Teams', 'Locations', 'ScanInformation', 'StoryArc', 'SeriesGroup', 'AgeRating',
        'Pages', 'CommunityRating', 'MainCharacterOrTeam', 'Review'
    ]

    def __init__(self):
        self._data = {
            'Manga': 'Yes',
            'Notes': '{}',
        }

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def put_note(self, key, value):
        notes = json.loads(self._data['Notes'])
        notes[key] = value
        self._data['Notes'] = json.dumps(notes)

    def __repr__(self):
        return json.dumps(self._data, indent = 4)

    def to_xml(self):
        root = xml.etree.ElementTree.Element('ComicInfo')

        for key in Metadata.COMIC_INFO_KEY_ORDER:
            if (key not in self._data):
                continue

            node = xml.etree.ElementTree.SubElement(root, key)
            node.text = self._data[key]

        xml.etree.ElementTree.indent(root, space = '    ')
        return xml.etree.ElementTree.tostring(root, encoding = 'unicode')

    def write_xml(self, path):
        with open(path, 'w') as file:
            file.write(self.to_xml() + "\n")

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
        metadata = Metadata()

        url = MangaUpdates.BASE_FETCH_URL % (id)
        html = self._fetch_url(url)
        document = bs4.BeautifulSoup(html, 'html.parser')

        metadata['Title'] = document.select_one('span.releasestitle').get_text()
        metadata['Series'] = metadata['Title']
        metadata['Summary'] = document.select_one('div#div_desc_more').contents[0].strip()

        metadata['Year'] = self._parse_single_section('Year', document)
        metadata['Writer'] = ','.join(self._parse_multi_section('Author(s)', document))
        metadata['Penciller'] = ','.join(self._parse_multi_section('Artist(s)', document))
        metadata['Publisher'] = ','.join(self._parse_multi_section('Original Publisher', document))
        metadata['Web'] = url

        self._parse_associated_name(document, metadata)
        self._parse_genres(document, metadata)
        self._parse_tags(document, metadata)

        return metadata

    def _parse_single_section(self, label, document):
        values = self._parse_multi_section(label, document)
        if ((values is None) or (len(values) == 0)):
            return None

        return values[0]

    def _parse_multi_section(self, label, document):
        header = document.find('div', 'sCat', string = label)
        if (header is None):
            return None

        node = header.find_next_sibling('div')
        if (node is None):
            return None

        text = node.get_text("\n").strip()

        values = [re.sub(r'\s+', ' ', name).strip() for name in text.split("\n")]
        values = [value for value in values if value != '']
        values.sort()

        return values

    def _parse_associated_name(self, document, metadata):
        values = self._parse_multi_section('Associated Names', document)
        if (values is None):
            return

        metadata.put_note('associated_names', values)

    def _parse_genres(self, document, metadata):
        values = self._parse_multi_section('Genre', document)
        if (values is None):
            return

        values.remove('Search for series of same genre(s)')

        metadata['Genre'] = ','.join(values)

    def _parse_tags(self, document, metadata):
        values = self._parse_multi_section('Categories', document)
        if (values is None):
            return

        values.remove('Log in to vote!')
        values.remove('Show all (some hidden)')

        metadata['Tags'] = ','.join(values)

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

    out_path = config.get('output_path')
    if (out_path is None):
        out_path = DEFAULT_OUTPUT_PATH

    print("Writing output to '%s'." % (out_path))
    metadata.write_xml(out_path)

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
