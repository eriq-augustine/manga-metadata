"""
Update the metadata in an existing cbz archive.
"""

import argparse
import os
import re
import sys
import zipfile

import manga.metadata.common
import manga.metadata.fetch

def main(args):
    if (not os.path.isfile(args.path)):
        print("ERROR: No archive to update at '%s'." % (args.path))
        return 1

    match = re.match(r'^(.+)\s+v(\d+)\s+c(\d+[a-z]?)\.cbz$', os.path.basename(args.path).strip())
    if (match is None):
        print("ERROR: Cannot parse name/volume/chapter information from archive path: '%s'." % (args.path))
        return 1

    name = match.group(1).strip()
    volume = str(int(match.group(2).strip()))
    chapter = match.group(3).strip()

    fetch_metadata = manga.metadata.fetch.fetch(name, args.cache_dir, args.use_first)
    if (fetch_metadata is None):
        print("ERROR: Unable to fetch metadata for '%s'." % (name))
        return 1

    old_metadata = manga.metadata.common.Metadata.from_cbz(args.path)
    old_metadata.update(fetch_metadata)

    new_metadata = old_metadata.copy()

    new_metadata['Volume'] = volume
    new_metadata['Number'] = chapter

    # Remove any existing metadata file.
    manga.metadata.common.remove_metadata_from_zipfile(args.path)

    with zipfile.ZipFile(args.path, 'a') as archive:
        with archive.open(manga.metadata.common.METADATA_FILENAME, 'w') as file:
            file.write((new_metadata.to_xml() + "\n").encode(manga.metadata.common.ENCODING))

    return 0

def _load_args():
    parser = argparse.ArgumentParser(description = "Update the metadata in an existing cbz archive.")

    parser.add_argument('path',
        action = 'store', type = str,
        help = 'the path to the archive to update')

    parser.add_argument('--cache', dest = 'cache_dir',
        action = 'store', type = str, default = None,
        help = 'a directory to use for caching (don\'t cache if not specified)')

    parser.add_argument('--first', dest = 'use_first',
        action = 'store_true', default = False,
        help = 'when presented with choices, always choose the first option and do not prompt (default: %(default)s)')

    return parser.parse_args()

if (__name__ == '__main__'):
    sys.exit(main(_load_args()))
