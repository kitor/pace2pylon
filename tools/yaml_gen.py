#!/usr/bin/env python3

for i in range(0,12):
    print(
f"""    - name: "Battery {i} volts"
      unique_id: "pv_batteries_{i}_volts"
      state_topic: "pv/batteries/{i}_v"
      state_class: "measurement"
      device_class: "voltage"
      unit_of_measurement: "V"
      suggested_display_precision: 3

    - name: "Battery {i} amps"
      unique_id: "pv_batteries_{i}_amps"
      state_topic: "pv/batteries/{i}_amps"
      state_class: "measurement"
      device_class: "current"
      unit_of_measurement: "A"
      suggested_display_precision: 2

    - name: "Battery {i} soc"
      unique_id: "pv_batteries_{i}_soc"
      state_topic: "pv/batteries/{i}_soc"
      state_class: "measurement"
      device_class: "battery"
      unit_of_measurement: "%"
      suggested_display_precision: 0
"""
)
