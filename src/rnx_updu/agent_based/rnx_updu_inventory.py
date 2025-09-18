#!/usr/bin/env python3
# Copyright (C) 2023 Riedo Networks Ltd - License: GNU General Public License v2

from typing import List

from cmk.agent_based.v2 import (
    Attributes,
    InventoryPlugin,
    InventoryResult,
    SNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
    startswith,
)

try:
    from cmk.ccc import debug
except ImportError:
    from cmk.utils import debug


def parse_rnx_updu_inventory(string_table: List[StringTable]):
    """Parse device identification data from RNX UPDUs."""
    if debug.enabled():
        print(f"inventory.parse: received string_table with {len(string_table)} tables")
        for i, table in enumerate(string_table):
            print(f"inventory.parse: table {i} has {len(table)} rows")

    section = {}

    # Parse PDU information (table 0)
    if len(string_table) > 0 and len(string_table[0]) > 0:
        for row_idx, row in enumerate(string_table[0]):
            if len(row) >= 6:  # Ensure we have all required PDU fields
                (system_name, custom_name, description, serial_number, part_number, lot_number) = row[:6]

                if debug.enabled():
                    print(f"inventory.parse: PDU row {row_idx}: system={system_name} custom={custom_name} "
                          f"desc={description} serial={serial_number} part={part_number} lot={lot_number}")

                # Use PDU index as device key (PDU table should only have one entry)
                device_key = f"pdu_{row_idx + 1}"

                section[device_key] = {
                    'type': 'PDU',
                    'system_name': system_name.strip(),
                    'custom_name': custom_name.strip(),
                    'description': description.strip(),
                    'serial_number': serial_number.strip(),
                    'part_number': part_number.strip(),
                    'lot_number': lot_number.strip(),
                    'firmware_version': '',  # Will be filled from ICM data
                }

                if debug.enabled():
                    print(f"inventory.parse: added PDU {device_key} with data {section[device_key]}")
    # Parse ICM information (table 1) for firmware data
    if len(string_table) > 1 and len(string_table[1]) > 0:
        for row_idx, row in enumerate(string_table[1]):
            if len(row) >= 5:  # Ensure we have all required ICM fields
                (icm_system_name, icm_serial_number, icm_part_number, icm_lot_number, icm_firmware) = row[:5]

                if debug.enabled():
                    print(f"inventory.parse: ICM row {row_idx}: system={icm_system_name} serial={icm_serial_number} "
                          f"part={icm_part_number} lot={icm_lot_number} firmware={icm_firmware}")

                # Add ICM firmware info to PDU data (assuming one ICM per PDU)
                pdu_key = f"pdu_{row_idx + 1}"
                if pdu_key in section:
                    section[pdu_key]['firmware_version'] = icm_firmware.strip()
                    section[pdu_key]['icm_serial'] = icm_serial_number.strip()
                    section[pdu_key]['icm_part_number'] = icm_part_number.strip()
                    section[pdu_key]['icm_lot_number'] = icm_lot_number.strip()
                    
                    # Extract ICM revision from part number (e.g., "100-0141-3" -> revision 3)
                    icm_revision = 0
                    try:
                        if '-' in icm_part_number:
                            revision_part = icm_part_number.split('-')[-1]  # Last part after dash
                            if revision_part.isdigit():
                                icm_revision = int(revision_part)
                    except (AttributeError, ValueError, IndexError):
                        pass
                    section[pdu_key]['icm_revision'] = icm_revision

                if debug.enabled():
                    print(f"inventory.parse: updated {pdu_key} with ICM firmware data and revision {icm_revision}")
    
    # Parse Module information (table 2) - POM modules
    if len(string_table) > 2 and len(string_table[2]) > 0:
        section['modules'] = {}
        for row_idx, row in enumerate(string_table[2]):
            if len(row) >= 8:  # Ensure we have all required module fields
                (module_system_name, module_serial_number, module_part_number, 
                 module_lot_number, module_rating, module_firmware, 
                 module_composed_name, module_object_path) = row[:8]
                
                if debug.enabled():
                    print(f"inventory.parse: Module row {row_idx}: system={module_system_name} "
                          f"serial={module_serial_number} part={module_part_number} "
                          f"path={module_object_path}")
                
                # Extract phase information from object path
                # ObjectPath format: "PDU/Inlet/WireL1/Module1" -> L1
                phase = "Unknown"
                if "WireL" in module_object_path:
                    try:
                        phase_part = module_object_path.split("/")[2]  # WireL1, WireL2, WireL3
                        if phase_part.startswith("WireL"):
                            phase = phase_part.replace("Wire", "")  # L1, L2, L3
                    except (IndexError, AttributeError):
                        pass
                
                module_key = f"module_{row_idx + 1}"
                
                # Extract POM revision from part number (e.g., "100-0715-2" -> revision 2)
                pom_revision = 0
                try:
                    if '-' in module_part_number:
                        revision_part = module_part_number.split('-')[-1]  # Last part after dash
                        if revision_part.isdigit():
                            pom_revision = int(revision_part)
                except (AttributeError, ValueError, IndexError):
                    pass
                
                section['modules'][module_key] = {
                    'type': 'POM',  # Power Outlet Module
                    'system_name': module_system_name.strip(),
                    'serial_number': module_serial_number.strip(),
                    'part_number': module_part_number.strip(),
                    'lot_number': module_lot_number.strip(),
                    'rating': int(module_rating) if module_rating.isdigit() else 0,
                    'firmware': module_firmware.strip(),
                    'composed_name': module_composed_name.strip(),
                    'object_path': module_object_path.strip(),
                    'phase': phase,
                    'outlets': 8,  # RNX POM modules typically have 8 outlets
                    'revision': pom_revision,
                }
                
                if debug.enabled():
                    print(f"inventory.parse: added module {module_key} on phase {phase}")
    
    # Note: Revisions are now extracted from part numbers directly
    # No need for separate revision parsing from table 3
    if debug.enabled():
        print(f"inventory.parse: built section with {len(section)} devices: {list(section.keys())}")
        if 'modules' in section:
            print(f"inventory.parse: found {len(section['modules'])} modules")
    
    return section


snmp_section_rnx_updu_inventory = SNMPSection(
    name='rnx_updu_inventory_section',
    detect=startswith('.1.3.6.1.2.1.1.1.0', 'RNX UPDU'),
    parse_function=parse_rnx_updu_inventory,
    fetch=[
        # PDU information
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.1.2.1',
            oids=[
                "2",   # upduMib2PDUSystemName
                "3",   # upduMib2PDUCustomName
                "4",   # upduMib2PDUDescription
                "5",   # upduMib2PDUSerialNumber
                "6",   # upduMib2PDUPartNumber
                "7",   # upduMib2PDULotNumber
            ],
        ),
        # ICM information for firmware
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.6.2.1',
            oids=[
                "2",   # upduMib2ICMSystemName
                "5",   # upduMib2ICMSerialNumber
                "6",   # upduMib2ICMPartNumber
                "7",   # upduMib2ICMLotNumber
                "9",   # upduMib2ICMFirmware
            ],
        ),
        # Module information (POM - Power Outlet Modules)
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.8.2.1',
            oids=[
                "2",   # upduMib2ModuleSystemName
                "5",   # upduMib2ModuleSerialNumber
                "6",   # upduMib2ModulePartNumber
                "7",   # upduMib2ModuleLotNumber
                "8",   # upduMib2ModuleRating
                "9",   # upduMib2ModuleFirmware
                "10",  # upduMib2ModuleComposedName
                "11",  # upduMib2ModuleObjectPath (contains phase info)
            ],
        ),
    ],
)


def inventory_rnx_updu(section) -> InventoryResult:
    """Generate inventory data for RNX UPDU devices."""
    if debug.enabled():
        print(f"inventory.inventory: processing section with {len(section)} devices")

    for device_id, device_data in section.items():
        if debug.enabled():
            print(f"inventory.inventory: processing device {device_id} with data {device_data}")

        # Determine device name and model
        device_name = device_data.get('custom_name') or device_data.get('system_name') or 'RNX UPDU'
        if device_data.get('custom_name') and device_data.get('system_name'):
            device_name = f"{device_data['system_name']} ({device_data['custom_name']})"

        model = device_data.get('part_number') or 'RNX UPDU'

        # Hardware information in the hardware tree
        yield Attributes(
            path=['hardware', 'system'],
            inventory_attributes={
                'manufacturer': 'Riedo Networks',
                'product': model,
                'serial': device_data.get('serial_number') or device_data.get('icm_serial') or '',
                'model': model,
                'name': device_name,
                'description': device_data.get('description') or 'RNX UPDU',
                'part_number': device_data.get('part_number') or device_data.get('icm_part_number') or '',
                
            }
        )

        # Separate ICM table entry if ICM data is available
        if device_data.get('icm_serial') or device_data.get('icm_part_number'):
            yield TableRow(
                path=['hardware', 'modules'],
                key_columns={'type': 'ICM'},
                inventory_columns={
                    'name': 'Interface Controller Module',
                    'device': device_data.get('system_name') or device_id,
                    'serial_number': device_data.get('icm_serial') or '',
                    'part_number': device_data.get('icm_part_number') or '',
                    'lot_number': device_data.get('icm_lot_number') or '',
                    'firmware': device_data.get('firmware_version') or '',
                    'revision': str(device_data.get('icm_revision', 0)),
                    'composed_name': device_data.get('icm_composed_name') or '',
                    'module_id': device_id,
                    'object_path': device_data.get('object_path', ''),
                    'description': device_data.get('description', 'Network Interface and Control Module'),
                }
            )

        if debug.enabled():
            print(f"inventory.inventory: generated inventory data for icm module {device_id}")
    
    # Add detailed module information if available
    if 'modules' in section:
        for module_key, module_data in section['modules'].items():
            if debug.enabled():
                print(f"inventory.inventory: processing module {module_key} with data {module_data}")
            
            # Hardware modules table
            yield TableRow(
                path=['hardware', 'modules'],
                key_columns={'module_id': module_key},
                inventory_columns={
                    'name': f"{module_data.get('type', 'Module')} {module_data.get('system_name', '')}",
                    'type': module_data.get('type', 'POM'),
                    'phase': module_data.get('phase', 'Unknown'),
                    'outlets': str(module_data.get('outlets', 8)),
                    'serial_number': module_data.get('serial_number', ''),
                    'part_number': module_data.get('part_number', ''),
                    'lot_number': module_data.get('lot_number', ''),
                    'Rating': f"{str(module_data.get('rating', 0)/1000)} A",
                    'firmware': module_data.get('firmware', ''),
                    'revision': str(module_data.get('revision', 0)),
                    'object_path': module_data.get('object_path', ''),
                    'composed_name': module_data.get('composed_name', ''),
                    'description': module_data.get('description', 'Power Outlet Module'),
                }
            )
            
            # Software/firmware information for each module
            if module_data.get('firmware'):
                yield TableRow(
                    path=['software', 'firmware'],
                    key_columns={'name': f"{module_data.get('type', 'Module')} {module_data.get('system_name', '')} Firmware"},
                    inventory_columns={
                        # 'name': f"{module_data.get('type', 'Module')} {module_data.get('system_name', '')} Firmware",
                        'version': module_data.get('firmware', ''),
                        'vendor': 'Riedo Networks',
                        'package_type': 'Firmware',
                        'install_date': '',
                        'size': '',
                        'path': module_data.get('object_path', ''),
                        'summary': f"Firmware for {module_data.get('type', 'Module')} on phase {module_data.get('phase', 'Unknown')}",
                    }
                )
            
            if debug.enabled():
                print(f"inventory.inventory: generated module inventory for {module_key}")


inventory_plugin_rnx_updu = InventoryPlugin(
    name='rnx_updu_inventory',
    sections=['rnx_updu_inventory_section'],
    inventory_function=inventory_rnx_updu,
)
