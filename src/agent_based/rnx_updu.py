#!/usr/bin/env python3
# Copyright (C) 2023 Riedo Networks Ltd - License: GNU General Public License v2

from collections.abc import Mapping
from typing import Any, Dict, List

from .agent_based_api.v1 import startswith, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from cmk.plugins.lib.elphase import check_elphase
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def parse_rnx_updu_power(
    string_table: List[StringTable],
) -> Dict:
    # Source: cmk/base/api/agent_based/checking_classes.py
    # Don't use IntEnum to prevent 'state.CRIT < state.UNKNOWN" from evaluating to True.
    # OK = 0
    # WARN = 1
    # CRIT = 2
    # UNKNOWN = 3
    map_data_quality = {
        '0': (State.OK, 'OK'),
        '1': (State.WARN, 'Expired'),
        '2': (State.UNKNOWN, 'No Data')
    }

    def power_data(string_table, objs):
        data = {}
        for index, what in objs:
            # This one must match the SNMPTree sequence in register.snmp_section
            for sysname, custname, qual, i , u, p, ap, e in string_table[index]:
                # If there is any power object with 'No Data' quality, we skip it
                # as it basically means that the channel is no licensed.
                dq, _hrdq = map_data_quality[qual]
                if dq == State.UNKNOWN:
                    print(f'WRN: Ignoring {sysname} due to NoData Quality')
                    continue

                objname = sysname
                if len(custname):
                    objname = f'{sysname} ({custname})'

                val = {
                    'name': objname ,
                    'type': what,
                    'power': float(p),
                    'appower': float(ap),
                    'voltage': float(u)/1000,
                    'current': float(i)/1000,
                    'energy': float(e),
                    'device_state': map_data_quality[qual]
                    }            
                data[sysname] = val
        return data
    
    def sensor_temp(string_table, objs):
        data = {}
        for index, what in objs:
            # This one must match the SNMPTree sequence in register.snmp_section
            for sysname, custname, port, t , qual_t, rh, qual_rh in string_table[index]:
                # If there is any power object with 'No Data' quality, we skip it
                # as it basically means that the channel is no licensed.
                dq, dq_hr = map_data_quality[qual_t]
                if dq == State.UNKNOWN:
                    print(f'WRN: Ignoring {sysname} due to NoData Quality')
                    continue
                objname = f'{sysname} Temperature on {port}'
                if len(custname):
                    objname += f' ({custname})'
                val = {
                    'name': objname,
                    'type': what,
                    'reading': float(t) / 10,
                    'unit': 'c',
                    'status': dq,
                    'status_name': dq_hr,
                    }            
                data[sysname] = val
        return data
    
    def sensor_rh(string_table, objs):
        data = {}
        for index, what in objs:
            # This one must match the SNMPTree sequence in register.snmp_section
            for sysname, custname, port, t , qual_t, rh, qual_rh in string_table[index]:
                # If there is any power object with 'No Data' quality, we skip it
                # as it basically means that the channel is no licensed.
                dq, dq_hr = map_data_quality[qual_rh]
                if dq == State.UNKNOWN:
                    print(f'WRN: Ignoring {sysname} due to NoData Quality')
                    continue
                objname = f'{sysname} Humidity on {port}'
                if len(custname):
                    objname += f' ({custname})'
                val = {
                    'name': objname,
                    'type': what,
                    'reading': float(rh) / 10,
                    'status': dq,
                    'status_name': dq_hr,
                    }            
                data[sysname] = val
        return data

    parse_data = {}

    # This one must match the SNMPTree definitions in register.snmp_section
    pwr_in_objs = [
        (0, 'pdu'), 
        (1, 'inlets'), 
        (2, 'wires'), 
    ]
    parse_data['power_in'] = power_data(string_table, pwr_in_objs)

    # This one must match the SNMPTree definitions in register.snmp_section
    pwr_out_objs = [
        (3, 'branch'), 
        (4, 'module'), 
        (5, 'outlet'), 
    ]
    parse_data['power_out'] = power_data(string_table, pwr_out_objs)

    # This one must match the SNMPTree definitions in register.snmp_section
    aux_sens_objs = [
        (6, 'external-sensor'), 
    ]
    parse_data['temperature'] = sensor_temp(string_table, aux_sens_objs)
    parse_data['humidity'] = sensor_rh(string_table, aux_sens_objs)

    return parse_data
    
#
# SNMP DEFINITIONS
#
pwr_oids = [
    '2',  # upduMib2<ObjectType>SystemName
    '3',  # upduMib2<ObjectType>CustomName
    '50', # upduMib2<ObjectType>MeterDataQuality
    '51', # upduMib2<ObjectType>Current
    '52', # upduMib2<ObjectType>Voltage
    '53', # upduMib2<ObjectType>ActivePower
    '54', # upduMib2<ObjectType>ApparentPower
    '56', # upduMib2<ObjectType>ActiveEnergy
]

sensor_oids = [
    '2',  # upduMib2SensorSystemName
    '3',  # upduMib2SensorCustomName
    '79', # upduMib2SensorPort
    '70', # upduMib2SensorTempDegC
    '71', # upduMib2SensorTempQuality
    '72', # upduMib2SensorRH
    '73', # upduMib2SensorRHQuality
]

register.snmp_section(
    name='rnx_updu_section',    
    detect=startswith('.1.3.6.1.2.1.1.1.0', 'RNX UPDU'),
    parse_function=parse_rnx_updu_power,

    fetch=[
        # 0: upduMib2PDU
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.1.2.1',
            oids=pwr_oids,
        ),

        # 1: upduMib2Inlet
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.2.2.1',
            oids=pwr_oids,
        ),

        # 2: upduMib2Wire
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.4.2.1',
            oids=pwr_oids,
        ),

        # 3: upduMib2Branch
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.5.2.1',
            oids=pwr_oids,
        ),

        # 4: upduMib2Module
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.8.2.1',
            oids=pwr_oids,
        ),

        # 5: upduMib2Outlet
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.9.2.1',
            oids=pwr_oids,
        ),

        # 6: upduMib2Sensor
        SNMPTree(
            base='.1.3.6.1.4.1.55108.2.23.2.1',
            oids=sensor_oids,
        ),  
    ],
)

#
# POWER IN
#
def discover_rnx_updu_power_in(section: Dict) -> DiscoveryResult:
    for key in section['power_in']:
        yield Service(item=key)

def check_rnx_updu_power_in(
    item: str, params: Mapping[str, Any], section: Dict
) -> CheckResult:
    yield from check_elphase(item, params, section['power_in'])

register.check_plugin(
    name='rnx_updu_power_in',
    sections=['rnx_updu_section'],
    service_name='%s',
    discovery_function=discover_rnx_updu_power_in,
    check_function=check_rnx_updu_power_in,
    check_ruleset_name='el_inphase',
    check_default_parameters={},
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

register.check_plugin(
    name='rnx_updu_power_out',
    sections=['rnx_updu_section'],
    service_name='%s',
    discovery_function=discover_rnx_updu_power_out,
    check_function=check_rnx_updu_power_out,
    check_ruleset_name='el_outphase',
    check_default_parameters={},
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

register.check_plugin(
    name="rnx_updu_temperature",
    sections=["rnx_updu_section"],
    service_name="%s Temperature",
    discovery_function=discover_rnx_updu_temp,
    check_function=check_rnx_updu_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
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

register.check_plugin(
    name="rnx_updu_humidity",
    sections=["rnx_updu_section"],
    service_name="%s Humidity",
    discovery_function=discover_rnx_updu_rh,
    check_function=check_rnx_updu_rh,
    check_ruleset_name="humidity",
    check_default_parameters={},
)