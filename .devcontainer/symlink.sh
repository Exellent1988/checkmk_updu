#!/bin/bash
PKGNAME=$(python3 -c 'print(eval(open("src/info").read())["name"])')

if [ -d ~/local/lib/python3/cmk_addons/plugins/$PKGNAME ]; then
    rm -rfv ~/local/lib/python3/cmk_addons/plugins/$PKGNAME
fi
ln -sv $WORKSPACE/src/$PKGNAME $OMD_ROOT/local/lib/python3/cmk_addons/plugins/$PKGNAME

# ERROR='false'
# for DIR in "agent_based" "rulesets" "graphing"; do
#     # rm -rfv $OMD_ROOT/local/share/check_mk/$DIR
#     if [ -d $WORKSPACE/src/$PKGNAME/$DIR ]; then
#         if [ -d ~/local/lib/python3/cmk_addons/plugins/$PKGNAME ]; then
#             rm -rfv ~/local/lib/python3/cmk_addons/plugins/$PKGNAME
#         else
#             mkdir -p ~/local/lib/python3/cmk_addons/plugins/$PKGNAME
#         fi
#         ln -sv $WORKSPACE/src/$PKGNAME/$DIR ~/local/lib/python3/cmk_addons/plugins/$PKGNAME
#     else
#         # echo "❌ $DIR not found in $WORKSPACE/src/"
#         ERROR='true'
#     fi
# done;
# if [ "$ERROR" = 'true' ]; then
#     echo "❌ Error: Some directories were not found in $WORKSPACE/src/$PKGNAME/"
#     ls -la $WORKSPACE/src/$PKGNAME/
    
# fi

# Apply Nagios container fix for qemu-x86_64 wrapper compatibility
echo ""
echo "=== Applying Nagios Container Fixes ==="
if [ -f "${WORKSPACE}/.devcontainer/fix-nagios-container.sh" ]; then
    bash "${WORKSPACE}/.devcontainer/fix-nagios-container.sh"
else
    echo "❌ Nagios fix script not found, skipping..."
fi