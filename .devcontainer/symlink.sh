#!/bin/bash
PKGNAME=$(python3 -c 'print(eval(open("src/info").read())["name"])')
ln -sv $WORKSPACE $OMD_ROOT/local/lib/python3/cmk_addons/plugins/$PKGNAME

# for DIR in 'agents' 'checkman' 'checks' 'doc' 'inventory' 'notifications' 'pnp-templates' 'web'; do
#     rm -rfv $OMD_ROOT/local/share/check_mk/$DIR
#     ln -sv $WORKSPACE/$DIR $OMD_ROOT/local/share/check_mk/$DIR
# done;

# Apply Nagios container fix for qemu-x86_64 wrapper compatibility
echo ""
echo "=== Applying Nagios Container Fixes ==="
if [ -f "${containerWorkspaceFolder}/.devcontainer/fix-nagios-container.sh" ]; then
    bash "${containerWorkspaceFolder}/.devcontainer/fix-nagios-container.sh"
else
    echo "❌ Nagios fix script not found, skipping..."
fi