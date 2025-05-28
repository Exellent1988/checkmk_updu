#!/bin/bash

# Build the package first
# $(pwd)/build.sh

# Extract name and version from info file
NAME=$(python3 -c 'print(eval(open("src/info").read())["name"])')
VERSION=$(cat VERSION)
# Replace <VERSION> in src/info.json
sed -i "s/<VERSION>/$VERSION/g" src/info

#Infos
echo "Package name: $NAME"
echo "Version: $VERSION"
echo "WORKSPACE: $WORKSPACE"


#Clean up aktive package
#mkp disable $NAME ||:
#mkp remove $NAME ||:
# Clean up old packages
rm -f /omd/sites/cmk/var/check_mk/packages/${NAME} \
      /omd/sites/cmk/var/check_mk/packages_local/${NAME}-*.mkp 2>/dev/null ||:

# Install the package
echo "Packing MKP package..."
mkp -v package $(pwd)/src/info ||:

# Copy the built package
if [ -f "/omd/sites/cmk/var/check_mk/packages_local/$NAME-$VERSION.mkp" ]; then
    cp /omd/sites/cmk/var/check_mk/packages_local/$NAME-$VERSION.mkp $WORKSPACE/build/$NAME-$VERSION.mkp && echo "Package copied to $WORKSPACE/build/$NAME-$VERSION.mkp" || echo "Package not found"
fi

# Inspect the package
if [ -f "$WORKSPACE/build/$NAME-$VERSION.mkp" ]; then
    echo "Inspecting package:"
    mkp inspect $WORKSPACE/build/$NAME-$VERSION.mkp
    sed -i "s/$VERSION/<VERSION>/g" src/info
else
    echo "Package file not found: $WORKSPACE/build/$NAME-$VERSION.mkp"
    echo "Available files in build directory:"
    ls -la $WORKSPACE/build/
fi
