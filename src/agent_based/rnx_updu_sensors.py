#!/usr/bin/env python3
# Copyright (C) 2023 Riedo Networks Ltd - License: GNU General Public License v2

from typing import Dict, List

from cmk.agent_based.v2 import (
    CheckResult,
    startswith,
    DiscoveryResult,
    Result,
    Service,
    SNMPTree,
    State,
    StringTable,
    SNMPSection,
    CheckPlugin
)

from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

try:
    from cmk.ccc import debug
except ImportError:
    from cmk.utils import debug

#
# SNMP DEFINITIONS - Moved to top so they're available for SimpleSNMPSection
#


sensor_oids = [
    '2',   # upduMib2SensorSystemName
    '3',   # upduMib2SensorCustomName
    '4',   # upduMib2SensorDescription
    '79',  # upduMib2SensorPort
    '70',  # upduMib2SensorTempDegC
    '71',  # upduMib2SensorTempQuality
    '72',  # upduMib2SensorRH
    '73',  # upduMib2SensorRHQuality
]
# Power monitoring OID bases (indices 0-5)


# Sensor OID bases (index 6)
sensor_bases = [
    '.1.3.6.1.4.1.55108.2.23.2.1',  # 6: upduMib2Sensor
]


snmp_sensor_trees = (
    [SNMPTree(base=sensor_base, oids=sensor_oids) for sensor_base in sensor_bases]
)


map_data_quality = {
    '0': (State.OK, 'OK'),
    '1': (State.WARN, 'Expired'),
    '2': (State.UNKNOWN, 'No Data'),
}


def parse_rnx_updu_sensor(
    string_table: List[StringTable],
) -> Dict:

    if debug.enabled():
        print(f'DEBUG: string_table: {string_table}')

    #
    # TEMPERATURE
    #
    def sensor_temp(string_table, objs):
        data = {}
        for index, what in objs:
            # This one must match the SNMPTree sequence in register.snmp_section
            for sysname, custname, desc, port, t, qual_t, rh, qual_rh in string_table[index]:
                # If there is any power object with 'No Data' quality, we skip it
                # as it basically means that the channel is no licensed.
                if debug.enabled():
                    print(f'DEBUG: string_table[index]: {string_table[index]}')

                dq, dq_t = map_data_quality[qual_t]
                if debug.enabled():
                    print(f'DEBUG: dq: {dq}, dq_t: {dq_t}')
                objname = f"{sysname} Temperature on {port}"
                if len(custname) > 1:
                    objname += f' ({custname})'
                if len(desc) > 1:
                    objname += f' [{desc}]'
                if dq == State.UNKNOWN:
                    print(f'WRN: Ignoring {objname} due to NoData Quality {qual_t}: {string_table[index]}')
                    continue

                val = {
                    'name': objname,
                    'type': what,
                    'description': desc,
                    'reading': float(t) / 10,
                    'unit': 'c',
                    'status': dq,
                    'status_name': dq_t,
                }
                data[sysname] = val
        return data

    #
    # HUMIDITY
    #
    def sensor_rh(string_table, objs):
        data = {}
        for index, what in objs:
            # This one must match the SNMPTree sequence in register.snmp_section
            for sysname, custname, desc, port, t, qual_t, rh, qual_rh in string_table[index]:
                # If there is any power object with 'No Data' quality, we skip it
                # as it basically means that the channel is no licensed.
                dq, dq_rh = map_data_quality[qual_rh]
                objname = f'{sysname} Humidity on {port}'
                if len(custname) > 1:
                    objname += f' ({custname})'
                if len(desc) > 1:
                    objname += f' [{desc}]'
                if dq == State.UNKNOWN:
                    if debug.enabled():
                        print(f'WRN: Ignoring {objname} due to NoData Quality {qual_rh}')
                    continue

                val = {
                    'label': objname,
                    'type': what,
                    'description': desc,
                    'reading': float(rh) / 10,
                    'status': dq,
                    'status_name': dq_rh,
                }
                data[sysname] = val
        return data
    parsed_data = {}

    # This one must match the SNMPTree definitions in register.snmp_section
    aux_sens_objs = [
        (0, 'external-sensor'),
    ]
    parsed_data['temperature'] = sensor_temp(string_table, aux_sens_objs)
    parsed_data['humidity'] = sensor_rh(string_table, aux_sens_objs)

    return parsed_data


# SNMP Section Registration
snmp_section_rnx_updu = SNMPSection(
    name='rnx_updu_section_sensor',
    detect=startswith('.1.3.6.1.2.1.1.1.0', 'RNX UPDU'),
    parse_function=parse_rnx_updu_sensor,
    fetch=list(snmp_sensor_trees),
)


#
# TEMPERATURE
#
def discover_rnx_updu_temp(section: Dict) -> DiscoveryResult:
    for key in section["temperature"]:
        yield Service(item=key)


def check_rnx_updu_temp(item: str, params: TempParamType, section: Dict) -> CheckResult:
    reading = section["temperature"][item]['reading']
    status = section["temperature"][item]['status']
    status_name = section["temperature"][item]['status_name']
    unit = section["temperature"][item]['unit']
    yield from check_temperature(
        reading,
        params,
        dev_unit=unit,
        dev_status=status,
        dev_status_name=status_name,
    )


check_plugin__rnx_updu_temp = CheckPlugin(
    name="rnx_updu_temperature",
    sections=["rnx_updu_section_sensor"],
    service_name="%s Temperature",
    discovery_function=discover_rnx_updu_temp,
    check_function=check_rnx_updu_temp,
    check_ruleset_name="temperature",
    check_default_parameters={'levels': (42.0, 50.0), 'levels_lower': (15.0, 5.0)},
)


#
# HUMIDITY
#
def discover_rnx_updu_rh(section: Dict) -> DiscoveryResult:
    for key in section["humidity"]:
        yield Service(item=key)


def check_rnx_updu_rh(item: str, params: TempParamType, section: Dict) -> CheckResult:
    reading = section["humidity"][item]['reading']
    status = section["humidity"][item]['status']
    status_name = section["humidity"][item]['status_name']
    yield from check_humidity(
        reading,
        params,
    )
    yield Result(
        state=State(status),
        summary=status_name,
    )


check_plugin__rnx_updu_rh = CheckPlugin(
    name="rnx_updu_humidity",
    sections=["rnx_updu_section_sensor"],
    service_name="%s Humidity",
    discovery_function=discover_rnx_updu_rh,
    check_function=check_rnx_updu_rh,
    check_ruleset_name="humidity",
    check_default_parameters={'levels': (75.0, 80.0), 'levels_lower': (7.0, 5.0)},
)
