"""
Common code for manga metadata.
"""

import json
import re
import xml.etree.ElementTree

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
