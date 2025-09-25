#!/usr/bin/env python3
# Copyright (C) 2023 Riedo Networks Ltd - License: GNU General Public License v2
# Simple Interface Inventory - Test Implementation

from typing import List, Dict, Any

from cmk.agent_based.v2 import (
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


def parse_rnx_updu_interfaces_simple(string_table: List[StringTable]) -> Dict[str, Any]:
    """Simple parser for RNX UPDU interfaces - just get basic info."""
    
    if debug.enabled():
        print(f"interfaces_simple.parse: received string_table with {len(string_table)} tables")
        for i, table in enumerate(string_table):
            print(f"interfaces_simple.parse: table {i} has {len(table)} rows")
            for j, row in enumerate(table):
                print(f"interfaces_simple.parse: table {i}, row {j}: {row}")

    section = {}

    if len(string_table) > 0:
        table = string_table[0]
        for row_idx, row in enumerate(table):
            if debug.enabled():
                print(f"interfaces_simple.parse: processing row {row_idx}: {row}")
            
            # Try different row lengths to be very permissive
            if len(row) >= 2:
                if_index = row[0] if len(row) > 0 else str(row_idx + 1)
                if_descr = row[1] if len(row) > 1 else f"Interface {if_index}"
                if_type = row[2] if len(row) > 2 else "1"
                
                interface_key = f"interface_{if_index}"
                
                section[interface_key] = {
                    'index': if_index,
                    'description': if_descr,
                    'type': if_type,
                    'raw_data': row,  # Keep raw data for debugging
                }
                
                if debug.enabled():
                    print(f"interfaces_simple.parse: added {interface_key}: {section[interface_key]}")
    
    if debug.enabled():
        print(f"interfaces_simple.parse: final section: {section}")
        
    return section


# SNMP Section - very simple approach
snmp_section_rnx_updu_interfaces_simple = SNMPSection(
    name='rnx_updu_interfaces_simple_section',
    detect=startswith('.1.3.6.1.2.1.1.1.0', 'RNX UPDU'),
    parse_function=parse_rnx_updu_interfaces_simple,
    fetch=[
        # Try just the basic interface info first
        SNMPTree(
            base='.1.3.6.1.2.1.2.2.1',  # ifTable
            oids=[
                '1',   # ifIndex
                '2',   # ifDescr
                '3',   # ifType
            ],
        ),
    ],
)


def inventory_rnx_updu_interfaces_simple(section: Dict[str, Any]) -> InventoryResult:
    """Simple inventory function."""
    
    if debug.enabled():
        print(f"interfaces_simple.inventory: section = {section}")
    
    for interface_key, interface_data in section.items():
        if debug.enabled():
            print(f"interfaces_simple.inventory: processing {interface_key}")
            
        # Very basic inventory entry
        yield TableRow(
            path=['networking', 'interfaces'],
            key_columns={'index': str(interface_data.get('index', ''))},
            inventory_columns={
                'description': interface_data.get('description', ''),
                'type': interface_data.get('type', ''),
                'interface_key': interface_key,
                'raw_data': str(interface_data.get('raw_data', [])),
            }
        )
        
        if debug.enabled():
            print(f"interfaces_simple.inventory: generated inventory for {interface_key}")


inventory_plugin_rnx_updu_interfaces_simple = InventoryPlugin(
    name='rnx_updu_interfaces_simple',
    sections=['rnx_updu_interfaces_simple_section'],
    inventory_function=inventory_rnx_updu_interfaces_simple,
)

