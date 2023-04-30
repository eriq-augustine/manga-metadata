#!/bin/bash

readonly TEMP_PATH=/tmp/rename-cbz

function fix_names {
    local path="${1}"
    local new_name="${2}"

    local archive_path=$(realpath "${path}")
    local archive_dir=$(dirname "${archive_path}")
    local archive_filename=$(basename "${path}")

    local old_name=$(echo "${archive_filename}" | sed 's/^\(.*\) v0.*$/\1/')

    echo '---'
    echo "${path}"
    echo "${old_name}"
    echo "${new_name}"

    pushd . > /dev/null
        cd "${TEMP_PATH}"
        rm -Rf *

        cp "${archive_path}" .
        unzip "${archive_filename}"
        rm "${archive_filename}"

        rename -- "${old_name}" "${new_name}" *

        zip "${archive_filename}" *
        rename -- "${old_name}" "${new_name}" "${archive_filename}"

        mv *.cbz "${archive_dir}/"

        rm -Rf *
    popd > /dev/null
}

function main() {
    if [[ $# -lt 2 ]]; then
        echo "USAGE: $0 <new name> <cbz> ..."
        exit 1
    fi

    trap exit SIGINT
    set -e

    mkdir -p "${TEMP_PATH}"

    for path in "${@:2}" ; do
        fix_names "${path}" "${1}"
    done
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
