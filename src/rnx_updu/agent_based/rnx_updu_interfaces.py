#!/usr/bin/env python3
# Copyright (C) 2023 Riedo Networks Ltd - License: GNU General Public License v2

from typing import List, Dict, Any
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
    TableRow,
    CheckPlugin,
    startswith,
)

try:
    from cmk.ccc import debug
except ImportError:
    from cmk.utils import debug


def parse_rnx_updu_interfaces(string_table: List[StringTable]) -> Dict[str, Any]:
    """Parse network interface data from RNX UPDUs using standard IF-MIB."""
    if debug.enabled():
        print(f"interfaces.parse: received string_table with {len(string_table)} tables")
        for i, table in enumerate(string_table):
            print(f"interfaces.parse: table {i} has {len(table)} rows")
            if len(table) > 0:
                print(f"interfaces.parse: table {i} first row: {table[0]}")

    section = {}

    # Parse interface table (table 0) 
    if len(string_table) > 0 and len(string_table[0]) > 0:
        for row_idx, row in enumerate(string_table[0]):
            if len(row) >= 6:  # Minimum required fields
                if_index = row[0]
                if_descr = row[1] if len(row) > 1 else f"Interface {if_index}"
                if_type = row[2] if len(row) > 2 else "1"
                if_mtu = row[3] if len(row) > 3 else "1500"
                if_speed = row[4] if len(row) > 4 else "0"
                if_admin_status = row[5] if len(row) > 5 else "1"
                if_oper_status = row[6] if len(row) > 6 else "1"

                if debug.enabled():
                    print(f"interfaces.parse: Interface {if_index}: {if_descr} "
                          f"type={if_type} admin={if_admin_status} oper={if_oper_status}")

                # Process all interface types (not just Ethernet)
                # Common types: 1=other, 6=ethernetCsmacd, 24=softwareLoopback, 117=gigabitEthernet
                interface_key = f"if_{if_index}"

                section[interface_key] = {
                    'index': int(if_index) if if_index.isdigit() else 0,
                    'description': if_descr.strip(),
                    'type': int(if_type) if if_type.isdigit() else 1,
                    'mtu': int(if_mtu) if if_mtu.isdigit() else 1500,
                    'speed': int(if_speed) if if_speed.isdigit() else 0,
                    'admin_status': int(if_admin_status) if if_admin_status.isdigit() else 1,
                    'oper_status': int(if_oper_status) if if_oper_status.isdigit() else 1,
                }

                if debug.enabled():
                    print(f"interfaces.parse: added interface {interface_key} with data {section[interface_key]}")
    
    else:
        if debug.enabled():
            print("interfaces.parse: No interface data found in string_table")

    if debug.enabled():
        print(f"interfaces.parse: Found {len(section)} interfaces total")
        
    return section


# Test with simpler detection first
def _detect_if_mib_exists(oid_values):
    """Check if standard IF-MIB exists."""
    return oid_values['.1.3.6.1.2.1.1.1.0'].startswith('RNX UPDU')

# SNMP Section for network interfaces using standard IF-MIB
snmp_section_rnx_updu_interfaces = SNMPSection(
    name='rnx_updu_interfaces_section',
    # More permissive detection - any device that starts with RNX UPDU
    detect=startswith('.1.3.6.1.2.1.1.1.0', 'RNX UPDU'),
    parse_function=parse_rnx_updu_interfaces,
    fetch=[
        # Interface table from IF-MIB - simplified to minimum required
        SNMPTree(
            base='.1.3.6.1.2.1.2.2.1',  # ifTable
            oids=[
                '1',   # ifIndex - absolutely required
                '2',   # ifDescr - required for description
                '3',   # ifType - helps identify interface type
                '4',   # ifMtu - optional but useful
                '5',   # ifSpeed - optional but useful  
                '7',   # ifAdminStatus - required for status
                '8',   # ifOperStatus - required for status
            ],
        ),
    ],
)


def inventory_rnx_updu_interfaces(section: Dict[str, Any]) -> InventoryResult:
    """Generate inventory data for RNX UPDU network interfaces."""
    if debug.enabled():
        print(f"interfaces.inventory: processing section with {len(section)} interfaces")

    for interface_key, interface_data in section.items():
        if debug.enabled():
            print(f"interfaces.inventory: processing interface {interface_key} with data {interface_data}")

        # Interface type mapping (expanded)
        type_mapping = {
            1: 'Other',
            6: 'Ethernet',
            24: 'Software Loopback',
            117: 'Gigabit Ethernet',
            131: '10 Gigabit Ethernet',
            161: '2.5 Gigabit Ethernet',
            162: '5 Gigabit Ethernet',
        }

        interface_type = type_mapping.get(interface_data.get('type', 0), f"Type {interface_data.get('type', 0)}")

        # Admin status mapping
        admin_status_mapping = {
            1: 'up',
            2: 'down',
            3: 'testing',
        }

        # Operational status mapping
        oper_status_mapping = {
            1: 'up',
            2: 'down',
            3: 'testing',
            4: 'unknown',
            5: 'dormant',
            6: 'notPresent',
            7: 'lowerLayerDown',
        }

        admin_status = admin_status_mapping.get(interface_data.get('admin_status', 0), 'unknown')
        oper_status = oper_status_mapping.get(interface_data.get('oper_status', 0), 'unknown')

        # Speed in readable format
        speed = interface_data.get('speed', 0)
        if speed >= 1000000000:
            speed_str = f"{speed // 1000000000} Gbps"
        elif speed >= 1000000:
            speed_str = f"{speed // 1000000} Mbps"
        elif speed > 0:
            speed_str = f"{speed // 1000} Kbps"
        else:
            speed_str = "Unknown"

        # Network interfaces table
        yield TableRow(
            path=['networking', 'interfaces'],
            key_columns={'index': str(interface_data['index'])},
            inventory_columns={
                'description': interface_data.get('description', ''),
                'type': interface_type,
                'speed': speed_str,
                'mtu': str(interface_data.get('mtu', 0)),
                'admin_status': admin_status,
                'oper_status': oper_status,
                'speed_bps': str(interface_data.get('speed', 0)),
                'interface_type_num': str(interface_data.get('type', 0)),
            }
        )

        if debug.enabled():
            print(f"interfaces.inventory: generated inventory data for interface {interface_key}")


inventory_plugin_rnx_updu_interfaces = InventoryPlugin(
    name='rnx_updu_interfaces',
    sections=['rnx_updu_interfaces_section'],
    inventory_function=inventory_rnx_updu_interfaces,
)


# Status mapping for checks
def get_interface_state(admin_status: int, oper_status: int) -> tuple[State, str]:
    """Determine check state based on admin and operational status."""
    if admin_status == 2:  # Admin down
        return State.OK, "administratively down"
    elif oper_status == 1:  # Operationally up
        return State.OK, "up"
    elif oper_status == 2:  # Operationally down
        return State.CRIT, "down"
    elif oper_status == 7:  # Lower layer down
        return State.WARN, "lower layer down"
    else:
        return State.UNKNOWN, f"unknown state (admin: {admin_status}, oper: {oper_status})"


def discover_rnx_updu_interfaces(section: Dict[str, Any]) -> DiscoveryResult:
    """Discover network interfaces for monitoring."""
    for interface_key, interface_data in section.items():
        interface_desc = interface_data.get('description', interface_key)
        yield Service(item=interface_desc)


def check_rnx_updu_interfaces(
    item: str, params: Mapping[str, Any], section: Dict[str, Any]
) -> CheckResult:
    """Check the status of network interfaces."""

    # Find the interface by description
    interface_data = None
    for key, data in section.items():
        if data.get('description', key) == item:
            interface_data = data
            break

    if not interface_data:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Interface {item} not found"
        )
        return

    admin_status = interface_data.get('admin_status', 0)
    oper_status = interface_data.get('oper_status', 0)

    state, status_text = get_interface_state(admin_status, oper_status)

    # Basic interface status
    yield Result(
        state=state,
        summary=f"Status: {status_text}"
    )

    # Speed information
    speed = interface_data.get('speed', 0)
    if speed > 0:
        if speed >= 1000000000:
            speed_str = f"{speed // 1000000000} Gbps"
        elif speed >= 1000000:
            speed_str = f"{speed // 1000000} Mbps"
        else:
            speed_str = f"{speed // 1000} Kbps"

        yield Result(
            state=State.OK,
            summary=f"Speed: {speed_str}"
        )

    # MTU information
    mtu = interface_data.get('mtu', 0)
    if mtu > 0:
        yield Result(
            state=State.OK,
            summary=f"MTU: {mtu}"
        )

    # Error statistics (if available)
    in_errors = interface_data.get('in_errors', 0)
    out_errors = interface_data.get('out_errors', 0)

    if in_errors > 0 or out_errors > 0:
        error_state = State.WARN if (in_errors + out_errors) < params.get('error_threshold', 100) else State.CRIT
        yield Result(
            state=error_state,
            summary=f"Errors: {in_errors} in, {out_errors} out"
        )

    # Discard statistics (if available)
    in_discards = interface_data.get('in_discards', 0)
    out_discards = interface_data.get('out_discards', 0)

    if in_discards > 0 or out_discards > 0:
        discard_state = State.WARN if (in_discards + out_discards) < params.get('discard_threshold', 100) else State.CRIT
        yield Result(
            state=discard_state,
            summary=f"Discards: {in_discards} in, {out_discards} out"
        )


check_plugin_rnx_updu_interfaces = CheckPlugin(
    name='rnx_updu_interfaces',
    sections=['rnx_updu_interfaces_section'],
    service_name='Interface %s',
    discovery_function=discover_rnx_updu_interfaces,
    check_function=check_rnx_updu_interfaces,
    check_default_parameters={
        'error_threshold': 100,
        'discard_threshold': 100,
    },
)
