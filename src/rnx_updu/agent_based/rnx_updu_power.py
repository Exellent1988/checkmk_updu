#!/usr/bin/env python3
# Copyright (C) 2023 Riedo Networks Ltd - License: GNU General Public License v2

from collections.abc import Mapping
from typing import Any, Dict, List

from cmk.agent_based.v2 import (
    CheckResult,
    startswith,
    DiscoveryResult,
    Service,
    SNMPTree,
    State,
    StringTable,
    SNMPSection,
    CheckPlugin
)
from cmk.plugins.lib.elphase import check_elphase

try:
    from cmk.ccc import debug
except ImportError:
    from cmk.utils import debug

#
# SNMP DEFINITIONS - Moved to top so they're available for SimpleSNMPSection
#
pwr_oids = [
    '2',   # upduMib2<ObjectType>SystemName
    '3',   # upduMib2<ObjectType>CustomName
    '4',   # upduMib2<ObjectType>Description
    '50',  # upduMib2<ObjectType>MeterDataQuality
    '51',  # upduMib2<ObjectType>Current
    '52',  # upduMib2<ObjectType>Voltage
    '53',  # upduMib2<ObjectType>ActivePower
    '54',  # upduMib2<ObjectType>ApparentPower
    '56',  # upduMib2<ObjectType>ActiveEnergy
]
# Power monitoring OID bases (indices 0-5)
power_bases = [
    '.1.3.6.1.4.1.55108.2.1.2.1',   # 0: upduMib2PDU
    '.1.3.6.1.4.1.55108.2.2.2.1',   # 1: upduMib2Inlet
    '.1.3.6.1.4.1.55108.2.4.2.1',   # 2: upduMib2Wire
    '.1.3.6.1.4.1.55108.2.5.2.1',   # 3: upduMib2Branch
    '.1.3.6.1.4.1.55108.2.8.2.1',   # 4: upduMib2Module
    '.1.3.6.1.4.1.55108.2.9.2.1',   # 5: upduMib2Outlet
]


# Generate SNMP trees dynamically
snmpe_power_trees = (
    [SNMPTree(base=power_base, oids=pwr_oids) for power_base in power_bases]
)


map_data_quality = {
    '0': (State.OK, 'OK'),
    '1': (State.WARN, 'Expired'),
    '2': (State.UNKNOWN, 'No Data'),
}


def parse_rnx_updu_power(
    string_table: List[StringTable],
) -> Dict:

    def power_data(string_table, objs):
        data = {}
        for index, what in objs:
            # This one must match the SNMPTree sequence in register.snmp_section
            for sysname, custname, desc, qual, i, u, p, ap, e in string_table[index]:
                # If there is any power object with 'No Data' quality, we skip it
                # as it basically means that the channel is no licensed.
                dq = map_data_quality[qual]
                if dq == State.UNKNOWN:
                    if debug.enabled():
                        print(f'WRN: Ignoring {sysname} due to NoData Quality {qual}')
                    continue

                objname = sysname
                if len(custname):
                    objname = f'{custname}'
                if len(desc) > 1:
                    objname += f' [{desc}]'

                val = {
                    'name': objname,

                    'type': what,
                    'title': desc,
                    'power': float(p),
                    'appower': float(ap),
                    'voltage': float(u) / 1000,
                    'current': float(i) / 1000,
                    'energy': float(e),
                    'device_state': map_data_quality[qual],
                }
                data[sysname] = val
        if debug.enabled():
            print(f'DEBUG: data: {data}')
        return data
    parsed_data = {}
    # This one must match the SNMPTree definitions in register.snmp_section
    pwr_in_combined_objs = [
        (0, 'pdu'),
        (1, 'inlets'),
    ]
    pwr_in_objs = [
        (2, 'wires'),
    ]
    parsed_data['power_in_combined'] = power_data(string_table, pwr_in_combined_objs)
    parsed_data['power_in'] = power_data(string_table, pwr_in_objs)
    
    # This one must match the SNMPTree definitions in register.snmp_section
    pwr_out_objs = [
        (3, 'branch'),
        (4, 'module'),
        (5, 'outlet'),
    ]
    parsed_data['power_out'] = power_data(string_table, pwr_out_objs)

    return parsed_data


# SNMP Section Registration
snmp_section_rnx_updu = SNMPSection(
    name='rnx_updu_section_power',
    detect=startswith('.1.3.6.1.2.1.1.1.0', 'RNX UPDU'),
    parse_function=parse_rnx_updu_power,
    fetch=list(snmpe_power_trees),
)


#
# POWER IN
#
def discover_rnx_updu_power_in(section: Dict) -> DiscoveryResult:
    for key in section['power_in']:
        yield Service(item=key)


def discover_rnx_updu_power_in_combined(section: Dict) -> DiscoveryResult:
    for key in section['power_in_combined']:
        yield Service(item=key)


def check_rnx_updu_power_in(
    item: str, params: Mapping[str, Any], section: Dict
) -> CheckResult:
    yield from check_elphase(item, params, section['power_in'])


def check_rnx_updu_power_in_combined(
    item: str, params: Mapping[str, Any], section: Dict
) -> CheckResult:
    yield from check_elphase(item, params, section['power_in_combined'])


check_plugin_rnx_updu_power_in = CheckPlugin(
    name='rnx_updu_power_in',
    sections=['rnx_updu_section_power'],
    service_name='%s',
    discovery_function=discover_rnx_updu_power_in,
    check_function=check_rnx_updu_power_in,
    check_ruleset_name='el_inphase',
    check_default_parameters={'voltage': (200, 195), 'power': (2000, 3000), 'appower': (2200, 3300), 'current': (9, 3)},
)
check_plugin_rnx_updu_power_in_combined = CheckPlugin(
    name='rnx_updu_power_in_combined',
    sections=['rnx_updu_section_power'],
    service_name='%s',
    discovery_function=discover_rnx_updu_power_in_combined,
    check_function=check_rnx_updu_power_in_combined,
    check_ruleset_name='el_inphase',
    check_default_parameters={'voltage': (200, 195), 'power': (6000, 9000), 'appower': (6600, 9900), 'current': (27, 30)},
)


#
# POWER OUT
#
def discover_rnx_updu_power_out(section: Dict) -> DiscoveryResult:
    for key in section['power_out']:
        yield Service(item=key)


def check_rnx_updu_power_out(
    item: str, params: Mapping[str, Any], section: Dict
) -> CheckResult:
    yield from check_elphase(item, params, section['power_out'])


check_plugin__rnx_updu_power_out = CheckPlugin(
    name='rnx_updu_power_out',
    sections=['rnx_updu_section_power'],
    service_name='%s',
    discovery_function=discover_rnx_updu_power_out,
    check_function=check_rnx_updu_power_out,
    check_ruleset_name='ups_outphase',
    check_default_parameters={'voltage': (200, 195), 'power': (2000, 3000), 'appower': (2500, 3300), 'current': (9, 10)},
)
