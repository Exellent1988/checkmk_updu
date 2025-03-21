#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")"

BUILD_DIR="$(pwd)/build"

VERSION=$(cat ./VERSION)
mkdir -p "${BUILD_DIR}"

TMP_BUILD_DIR=$(mktemp -d)
function cleanup()
{
  if [ -d "${TMP_BUILD_DIR}" ]; then
    rm -r "${TMP_BUILD_DIR}"
  fi
}

trap cleanup EXIT

for d in src/*/; do
  tar cf "${TMP_BUILD_DIR}/$(basename $d).tar" -C $d $(ls -1 $d | xargs)
done

cp ./src/info "${TMP_BUILD_DIR}"
sed -i "s/<VERSION>/$VERSION/" "${TMP_BUILD_DIR}/info"

cp ./src/info.json "${TMP_BUILD_DIR}"
sed -i "s/<VERSION>/$VERSION/" "${TMP_BUILD_DIR}/info.json"

tar czf "${BUILD_DIR}/rnx_updu-${VERSION}.mkp" -C "${TMP_BUILD_DIR}" $(ls -1 "${TMP_BUILD_DIR}"| xargs)

exit 0