#!/bin/bash

# Nagios Container Fix for Check_MK DevContainer
# Fixes the pidof_nagios function to work with qemu-x86_64 wrapper
# This script is automatically executed during container setup

echo "=== Applying Nagios Container Fix ==="

# Backup original nagios init script if not already done
if [ ! -f "$OMD_ROOT/local/lib/nagios.original" ]; then
    echo "Creating backup of original nagios init script..."
    cp "$OMD_ROOT/etc/init.d/nagios" "$OMD_ROOT/local/lib/nagios.original"
fi

# Apply the container fix to pidof_nagios function
echo "Patching nagios init script for container compatibility..."

# Create temp file with the fix
cat > /tmp/nagios_fix.patch << 'EOF'
# Fetches the pid of the currently running nagios process of the given
# user.
#
# --ppid 1 in ps seem not to filter by direct ppid but by the whole
# parent process tree. So filter by hand again.
#
# Removed the filter "-P 1" (filters for ppid=1 processes) as on some
# distros, like Ubuntu 13.10 and newer, the processes will not be childs
# of PID 1, instead the process is child of an "upstart user session",
# which is visible via ps as "init --user". This will be the PPID until
# the user session ends, then the process will be moved to PPID=1.
# Strange one, but we try to simply ignore that...  "-o" should make it.
# 
# It returns 1 when no process can be found and echos the PID while
# returning 0 when a process can be found.
#
# CONTAINER FIX: Modified for qemu-x86_64 wrapper compatibility
pidof_nagios() {
    # Original exact match doesn't work in container with qemu wrapper:
    # pgrep -u $OMD_SITE -o -fx "$BIN $OPTIONS $CFG_FILE" 2>/dev/null
    
    # Container-safe version using flexible pattern matching:
    pgrep -u $OMD_SITE -o -f "bin/nagios.*-ud.*nagios\.cfg" 2>/dev/null
}
EOF

# Apply the patch using sed to replace the pidof_nagios function
sed -i '/^pidof_nagios() {$/,/^}$/c\
# Fetches the pid of the currently running nagios process of the given\
# user.\
#\
# --ppid 1 in ps seem not to filter by direct ppid but by the whole\
# parent process tree. So filter by hand again.\
#\
# Removed the filter "-P 1" (filters for ppid=1 processes) as on some\
# distros, like Ubuntu 13.10 and newer, the processes will not be childs\
# of PID 1, instead the process is child of an "upstart user session",\
# which is visible via ps as "init --user". This will be the PPID until\
# the user session ends, then the process will be moved to PPID=1.\
# Strange one, but we try to simply ignore that...  "-o" should make it.\
# \
# It returns 1 when no process can be found and echos the PID while\
# returning 0 when a process can be found.\
#\
# CONTAINER FIX: Modified for qemu-x86_64 wrapper compatibility\
pidof_nagios() {\
    # Original exact match does not work in container with qemu wrapper:\
    # pgrep -u $OMD_SITE -o -fx "$BIN $OPTIONS $CFG_FILE" 2>/dev/null\
    \
    # Container-safe version using flexible pattern matching:\
    pgrep -u $OMD_SITE -o -f "bin/nagios.*-ud.*nagios\\.cfg" 2>/dev/null\
}' "$OMD_ROOT/etc/init.d/nagios"

# Create cleanup script for manual use
echo "Creating Nagios cleanup script..."
cat > "$OMD_ROOT/local/bin/restart-nagios-clean.sh" << 'EOF'
#!/bin/bash

# Cleanup Script für Nagios-Probleme in Check_MK Dev Container
# Dieses Script behebt das häufige Problem mit hängenden Nagios-Prozessen

echo "=== Nagios Cleanup & Restart ==="

# 1. Alle Nagios-Prozesse finden und killen
echo "Stopping all Nagios processes..."
pkill -f "/omd/sites/cmk/bin/nagios" 2>/dev/null || true
sleep 2

# 2. Lockfile entfernen
echo "Removing lockfile..."
rm -f /omd/sites/cmk/tmp/lock/nagios.lock

# 3. Socket aufräumen (falls vorhanden)
echo "Cleaning up sockets..."
rm -f /omd/sites/cmk/tmp/run/live 2>/dev/null || true

# 4. Nagios neu starten
echo "Starting Nagios..."
omd start nagios

# 5. Status prüfen
echo "Checking status..."
sleep 3
if [ -S "/omd/sites/cmk/tmp/run/live" ]; then
    echo "✅ SUCCESS: Livestatus socket exists"
    echo "✅ Nagios is running properly"
else
    echo "❌ ERROR: Livestatus socket not found"
    echo "Check logs: tail -f /omd/sites/cmk/var/log/nagios.log"
fi

echo "=== Done ==="
EOF

chmod +x "$OMD_ROOT/local/bin/restart-nagios-clean.sh"

# Clean up temp files
rm -f /tmp/nagios_fix.patch

echo "✅ Nagios container fix applied successfully!"
echo "✅ Cleanup script available at: ~/local/bin/restart-nagios-clean.sh"
echo "✅ Original nagios script backed up to: ~/local/lib/nagios.original"

# Test if the fix works
echo "Testing fix..."
if ! pgrep -u "$OMD_SITE" -f "bin/nagios.*-ud.*nagios\.cfg" >/dev/null 2>&1; then
    echo "ℹ️  Note: Nagios is not currently running, but fix is applied"
else
    echo "✅ Fix verified: Nagios process detection working"
fi

echo "=== Nagios Container Fix Complete ===" 