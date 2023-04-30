"""
Common code for manga metadata.
"""

import json
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree
import zipfile

ENCODING = 'utf-8'
METADATA_FILENAME = 'ComicInfo.xml'
METADATA_FILENAME_REGEX = r'ComicInfo\.xml'
TEMP_ZIP_FILENAME = 'temp.zip'

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

    def __init__(self, data = {}):
        self._data = {
            'Manga': 'Yes',
            'Notes': '{}',
        }

        self._data.update(data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def put_note(self, key, value):
        notes = json.loads(self._data['Notes'])
        notes[key] = value
        self._data['Notes'] = json.dumps(notes)

    def __repr__(self):
        return self.to_json()

    def copy(self):
        return Metadata(data = dict(self._data))

    @staticmethod
    def from_cbz(path):
        with zipfile.ZipFile(path, 'r') as archive:
            try:
                archive.getinfo(METADATA_FILENAME)
            except KeyError:
                # This archive contains no metadata.
                return Metadata(), False

            xml = archive.read(METADATA_FILENAME).decode(ENCODING)
            return Metadata.from_xml(xml), True

    @staticmethod
    def from_xml(text):
        document = xml.etree.ElementTree.fromstring(text)

        data = {}
        for child in document:
            data[child.tag] = child.text

        return Metadata(data)

    def update(self, other):
        self._data.update(other._data)

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

    def to_json(self):
        output = dict(self._data)
        output['Notes'] = json.loads(output['Notes'])
        return json.dumps(output, indent = 4, sort_keys = True)

def get_int(lower, upper, prompt):
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

def remove_metadata_from_zipfile(zip_path):
    return remove_from_zipfile(zip_path, METADATA_FILENAME_REGEX)

def remove_from_zipfile(zip_path, filename_regex):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, TEMP_ZIP_FILENAME)

        with zipfile.ZipFile(zip_path, 'r') as old_archive:
            with zipfile.ZipFile(temp_path, 'w') as new_archive:
                for item in old_archive.infolist():
                    if (re.search(filename_regex, item.filename) is None):
                        data = old_archive.read(item.filename)
                        new_archive.writestr(item, data)

        shutil.move(temp_path, zip_path)
