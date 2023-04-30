"""
Sources to fetch manga metadata from.
"""

import abc
import os
import re
import urllib.request

import bs4

import manga.metadata.common

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
            data = response.read()
            html = data.decode(manga.metadata.common.ENCODING, errors = 'replace')

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
        metadata = manga.metadata.common.Metadata()

        url = MangaUpdates.BASE_FETCH_URL % (id)
        html = self._fetch_url(url)
        document = bs4.BeautifulSoup(html, 'html.parser')

        metadata['Title'] = document.select_one('span.releasestitle').get_text()
        metadata['Series'] = metadata['Title']

        if (document.select_one('div#div_desc_more') is not None):
            metadata['Summary'] = document.select_one('div#div_desc_more').contents[0].strip()
        else:
            metadata['Summary'] = self._parse_single_section('Description', document)

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

        remove_values = [
            'Log in to vote!',
            'Show all (some hidden)',
        ]

        for value in remove_values:
            if (value in values):
                values.remove(value)

        metadata['Tags'] = ','.join(values)
