#!/bin/bash

TEMP_PATH=/tmp/fix-cbz

mkdir -p "${TEMP_PATH}"

for archive_relpath in **/*.cbz ; do
    archive_path=$(realpath "${archive_relpath}")
    archive_filename=$(basename "${archive_relpath}")

    pushd . > /dev/null
        cd "${TEMP_PATH}"
        rm -Rf *

        cp "${archive_path}" .
        unzip "${archive_filename}"
        rm "${archive_filename}"

        mv **/* .
        find . -type d -empty -delete

        zip "${archive_filename}" *
        mv "${archive_filename}" "${archive_path}"

        rm -Rf *
    popd > /dev/null
done
