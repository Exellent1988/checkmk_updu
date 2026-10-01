#!/bin/bash
set -euo pipefail

cd "${WORKSPACE:?WORKSPACE is not set}"

PKGNAME=$(python3 -c 'print(eval(open("src/info").read())["name"])')
SRC_PKG="${WORKSPACE}/src/${PKGNAME}"
DST_PKG="${OMD_ROOT}/local/lib/python3/cmk_addons/plugins/${PKGNAME}"

# Checkmk 2.5 snapshots ~/local and copies external symlinks with shutil.copy2,
# which only works for files. Symlink individual files, keep real directories.
if [ -e "${DST_PKG}" ] || [ -L "${DST_PKG}" ]; then
    rm -rfv "${DST_PKG}"
fi

if [ ! -d "${SRC_PKG}" ]; then
    echo "❌ Plugin source not found: ${SRC_PKG}"
    exit 1
fi

mkdir -p "${DST_PKG}"

# Mirror package directory tree; symlink only regular files (e.g. *.py)
find "${SRC_PKG}" -type d -print0 | while IFS= read -r -d '' dir; do
    rel="${dir#"${SRC_PKG}/"}"
    if [ "${rel}" = "${dir}" ]; then
        continue  # SRC_PKG itself
    fi
    # Skip bytecode caches
    case "${rel}" in
        *__pycache__*) continue ;;
    esac
    mkdir -p "${DST_PKG}/${rel}"
done

find "${SRC_PKG}" -type f -name '*.py' -print0 | while IFS= read -r -d '' file; do
    rel="${file#"${SRC_PKG}/"}"
    case "${rel}" in
        *__pycache__*) continue ;;
    esac
    ln -sfv "${file}" "${DST_PKG}/${rel}"
done

echo "✓ Linked ${PKGNAME} plugin files into ${DST_PKG}"
ls -laR "${DST_PKG}"

# Apply Nagios container fix for qemu-x86_64 wrapper compatibility
echo ""
echo "=== Applying Nagios Container Fixes ==="
if [ -f "${WORKSPACE}/.devcontainer/fix-nagios-container.sh" ]; then
    bash "${WORKSPACE}/.devcontainer/fix-nagios-container.sh"
else
    echo "❌ Nagios fix script not found, skipping..."
fi
