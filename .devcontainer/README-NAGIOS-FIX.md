# Nagios Container Fix für Check_MK DevContainer

## Problem
In Check_MK Development Containern mit qemu-x86_64 Wrapper (typisch bei ARM-Architekturen oder bestimmten Container-Setups) funktioniert der Nagios-Service nicht korrekt. 

### Symptome:
- `Cannot connect to 'unix:/omd/sites/cmk/tmp/run/live': [Errno 2] No such file or directory`
- `omd restart` funktioniert nicht richtig
- Hängende Nagios-Prozesse
- Nagios-Status zeigt "stopped" obwohl Prozesse laufen

### Root Cause:
Die `pidof_nagios()` Funktion im OMD-Init-Script verwendet exact matching (`pgrep -fx`), das mit qemu-Wrappern nicht funktioniert:

**Erwarteter Prozess:**
```
/omd/sites/cmk/bin/nagios -ud /omd/sites/cmk/tmp/nagios/nagios.cfg
```

**Tatsächlicher Prozess:**
```
/usr/bin/qemu-x86_64 /omd/sites/cmk/bin/nagios /omd/sites/cmk/bin/nagios -ud /omd/sites/cmk/tmp/nagios/nagios.cfg
```

## Lösung
Dieser Container enthält einen automatischen Fix, der beim Container-Setup angewendet wird.

### Was wird gepatcht:
1. **`/omd/sites/cmk/etc/init.d/nagios`**: Die `pidof_nagios()` Funktion wird durch eine container-sichere Version ersetzt
2. **Cleanup-Script**: Ein Helper-Script wird erstellt für manuelle Problembehandlung

### Automatische Anwendung:
Der Fix wird automatisch beim Container-Setup über `postCreateCommand` angewendet:
- `.devcontainer/symlink.sh` ruft `.devcontainer/fix-nagios-container.sh` auf
- Das Backup der originalen Datei wird in `/omd/sites/cmk/local/lib/nagios.original` gespeichert

## Verwendung

### Nach Container-Setup:
Alles sollte automatisch funktionieren. Du kannst normal arbeiten:
```bash
omd restart      # Funktioniert jetzt
omd status       # Zeigt korrekten Status
```

### Manuelle Problembehandlung:
Falls trotzdem Probleme auftreten:
```bash
~/local/bin/restart-nagios-clean.sh
```

### Wiederherstellung:
Falls du den originalen Zustand wiederherstellen willst:
```bash
cp ~/local/lib/nagios.original /omd/sites/cmk/etc/init.d/nagios
```

## Dateien
- `.devcontainer/fix-nagios-container.sh` - Haupt-Fix-Script
- `.devcontainer/symlink.sh` - Erweitert um automatische Anwendung
- `/omd/sites/cmk/local/bin/restart-nagios-clean.sh` - Cleanup Helper
- `/omd/sites/cmk/local/lib/nagios.original` - Backup der Original-Datei

## Kompatibilität
- ✅ ARM64 MacBooks mit Docker Desktop
- ✅ x86_64 Container mit qemu-Emulation  
- ✅ Standard Linux Docker-Setups
- ✅ Check_MK 2.3.0 und neuere Versionen

Der Fix ist rückwärtskompatibel und beeinträchtigt normale Container-Setups nicht. 