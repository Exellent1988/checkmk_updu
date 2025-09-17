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
                
                if debug.enabled():
                    print(f"inventory.parse: updated {pdu_key} with ICM firmware data")
    
    if debug.enabled():
        print(f"inventory.parse: built section with {len(section)} devices: {list(section.keys())}")
    
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
                'serial': device_data.get('serial_number') or 'Unknown',
                'model': model,
                'name': device_name,
                'description': device_data.get('description') or '',
                'part_number': device_data.get('part_number') or '',
                'lot_number': device_data.get('lot_number') or '',
            }
        )
        
        # Software information in the software tree (firmware from ICM)
        if device_data.get('firmware_version'):
            yield Attributes(
                path=['software', 'firmware'],
                inventory_attributes={
                    'name': 'RNX UPDU ICM Firmware',
                    'version': device_data['firmware_version'],
                    'package_type': 'Firmware',
                    'summary': f"RNX UPDU {model} ICM Firmware",
                    'vendor': 'Riedo Networks',
                    'package_version': device_data['firmware_version'],
                }
            )
        
        # Device-specific table for detailed UPDU information
        yield TableRow(
            path=['hardware', 'components'],
            key_columns={'index': device_id},
            inventory_columns={
                'type': device_data.get('type','UPDU'),
                'system_name': device_data.get('system_name') or '',
                'custom_name': device_data.get('custom_name') or '',
                'description': device_data.get('description') or '',
                'serial_number': device_data.get('serial_number') or '',
                'part_number': device_data.get('part_number') or '',
                'lot_number': device_data.get('lot_number') or '',
                'firmware_version': device_data.get('firmware_version') or '',
                'icm_serial': device_data.get('icm_serial') or '',
                'icm_part_number': device_data.get('icm_part_number') or '',
                'icm_lot_number': device_data.get('icm_lot_number') or '',
            }
        )
        
        if debug.enabled():
            print(f"inventory.inventory: generated inventory data for device {device_id}")


inventory_plugin_rnx_updu = InventoryPlugin(
    name='rnx_updu_inventory',
    sections=['rnx_updu_inventory_section'],
    inventory_function=inventory_rnx_updu,
)
