
pdo_type = {
    0b00: 'Fixed Supply',
    0b01: 'Battery',
    0b10: 'Variable Supply',
    0b11: 'Augmented Power Data Object'
}
augmented_pdo_type = {
    0b00: 'Programmable Power Supply',
    0b01: 'Reserved',
    0b10: 'Reserved',
    0b11: 'Reserved'
}

fixed_supply_sink_fast_role_swap_required_current = {
    0b00: 'Fast Swap not supported',
    0b01: 'Default USB Power',
    0b10: '1.5A @ 5V',
    0b11: '3.0A @ 5V'
}

# Source_capabilities,
def decode_source_power_data_object( word):
    data = {
        'data_object_type': 'Power Data Object'
    }
    frame_type = 'object'
    _pdo_type = (word >> 30) & 0x3
    pdo_type_str = pdo_type[_pdo_type]
    if _pdo_type == 0b11:
        _augmented_pdo_type = (word >> 28) & 0x3
        pdo_type_str = augmented_pdo_type[_augmented_pdo_type]
        if _augmented_pdo_type == 0b00:
            # Programmable Power Supply Augmented Power Data Object
            pps_power_limited = (word >> 27) & 0x1
            maximum_voltage_100mv_units = (word >> 17) & 0xFF
            minimum_voltage_100mv_units = (word >> 8) & 0xFF
            maximum_current_50ma_units = word & 0x7F
            data['maximum_voltage_100mv_units'] = maximum_voltage_100mv_units
            data['minimum_voltage_100mv_units'] = minimum_voltage_100mv_units
            data['maximum_current_50ma_units'] = maximum_current_50ma_units
            frame_type = 'source_programmable_supply_pdo'
    else:
        if _pdo_type == 0b00:
            # Fixed Supply Power Data Object
            dual_role_power = (word >> 29) & 0x1
            usb_suspend_supported  = (word >> 28) & 0x1
            unconstrained_power = (word >> 27) & 0x1
            usb_communications_capable = (word >> 26) & 0x1
            dual_role_data = (word >> 25) & 0x1
            unchecked_extended_messages_supported  = (word >> 24) & 0x1
            peak_current = (word >> 20) & 0x3 #
            voltage_50mv_units = (word >> 10) & 0x3FF
            maximum_current_10ma_units = word & 0x3FF
            data['dual_role_power'] = dual_role_power
            data['usb_suspend_supported'] = usb_suspend_supported
            data['unconstrained_power'] = unconstrained_power
            data['usb_communications_capable'] = usb_communications_capable
            data['dual_role_data'] = dual_role_data
            data['unchecked_extended_messages_supported'] = unchecked_extended_messages_supported
            data['peak_current'] = peak_current
            data['voltage_50mv_units'] = voltage_50mv_units
            data['maximum_current_10ma_units'] = maximum_current_10ma_units
            frame_type = 'source_fixed_supply_pdo'

        elif _pdo_type == 0b10:
            # variable supply (non-battery) Power Data Object - source
            maximum_voltage_50mv_units = (word >> 20) & 0x3FF
            minimum_voltage_50mv_units = (word >> 10) & 0x3FF
            maximum_current_10ma_units = word & 0x3FF
            data['maximum_voltage_50mv_units'] = maximum_voltage_50mv_units
            data['minimum_voltage_50mv_units'] = minimum_voltage_50mv_units
            data['maximum_current_10ma_units'] = maximum_current_10ma_units
            frame_type = 'source_variable_supply_pdo'
        elif _pdo_type == 0b01:
            # Battery Supply Power Data Object
            maximum_voltage_50mv_units = (word >> 20) & 0x3FF
            minimum_voltage_50mv_units = (word >> 10) & 0x3FF
            maximum_allowable_power_250mw_units = word & 0x3FF
            data['maximum_voltage_50mv_units'] = maximum_voltage_50mv_units
            data['minimum_voltage_50mv_units'] = minimum_voltage_50mv_units
            data['maximum_allowable_power_250mw_units'] = maximum_allowable_power_250mw_units
            frame_type = 'source_battery_supply_pdo'

    data['pdo_type'] = pdo_type_str

    return frame_type, data

# sink_capabilities,
def decode_sink_power_data_object( word):
    data = {
        'data_object_type': 'Power Data Object'
    }
    frame_type = 'object'

    _pdo_type = (word >> 30) & 0x3
    pdo_type_str = pdo_type[_pdo_type]
    if _pdo_type == 0b11:
        _augmented_pdo_type = (word >> 28) & 0x3
        pdo_type_str = augmented_pdo_type[_augmented_pdo_type]
        if _augmented_pdo_type == 0b00:
            # Programmable Power Supply Augmented Power Data Object
            pps_power_limited = (word >> 27) & 0x1
            maximum_voltage_100mv_units = (word >> 17) & 0xFF
            minimum_voltage_100mv_units = (word >> 8) & 0xFF
            maximum_current_50ma_units = word & 0x7F
            data['maximum_voltage_100mv_units'] = maximum_voltage_100mv_units
            data['minimum_voltage_100mv_units'] = minimum_voltage_100mv_units
            data['maximum_current_50ma_units'] = maximum_current_50ma_units
            frame_type = 'sink_programmable_supply_pdo'
    else:
        if _pdo_type == 0b00:
            # Fixed Supply Power Data Object
            dual_role_power = (word >> 29) & 0x1
            usb_suspend_supported  = (word >> 28) & 0x1
            unconstrained_power = (word >> 27) & 0x1
            usb_communications_capable = (word >> 26) & 0x1
            dual_role_data = (word >> 25) & 0x1
            fast_role_swap_required_current = (word >> 23) & 0x3
            voltage_50mv_units = (word >> 10) & 0x3FF
            operational_current_10ma_units = word & 0x3FF
            data['dual_role_power'] = dual_role_power
            data['usb_suspend_supported'] = usb_suspend_supported
            data['unconstrained_power'] = unconstrained_power
            data['usb_communications_capable'] = usb_communications_capable
            data['dual_role_data'] = dual_role_data
            data['fast_role_swap_required_current'] = fixed_supply_sink_fast_role_swap_required_current[fast_role_swap_required_current]
            data['voltage_50mv_units'] = voltage_50mv_units
            data['operational_current_10ma_units'] = operational_current_10ma_units
            frame_type = 'sink_fixed_supply_pdo'

        elif _pdo_type == 0b10:
            # variable supply (non-battery) Power Data Object - source
            maximum_voltage_50mv_units = (word >> 20) & 0x3FF
            minimum_voltage_50mv_units = (word >> 10) & 0x3FF
            maximum_current_10ma_units = word & 0x3FF
            data['maximum_voltage_50mv_units'] = maximum_voltage_50mv_units
            data['minimum_voltage_50mv_units'] = minimum_voltage_50mv_units
            data['maximum_current_10ma_units'] = maximum_current_10ma_units
            frame_type = 'sink_variable_supply_pdo'
        elif _pdo_type == 0b01:
            # Battery Supply Power Data Object
            maximum_voltage_50mv_units = (word >> 20) & 0x3FF
            minimum_voltage_50mv_units = (word >> 10) & 0x3FF
            maximum_allowable_power_250mw_units = word & 0x3FF
            data['maximum_voltage_50mv_units'] = maximum_voltage_50mv_units
            data['minimum_voltage_50mv_units'] = minimum_voltage_50mv_units
            data['maximum_allowable_power_250mw_units'] = maximum_allowable_power_250mw_units
            frame_type = 'sink_battery_supply_pdo'

    data['pdo_type'] = pdo_type_str

    return frame_type, data

def decode_bist_data_object(word):
    pass

def decode_request_data_object(word):
    pass

def decode_vendor_data_object(word):
    pass

