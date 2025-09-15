from dataclasses import dataclass

@dataclass
class Thresholds:
    # BMS defaults: alarm 3.60v, protect 3.70v, release 3.30V
    cell_ov = 3630
    cell_ov_release = 3300

    # BMS defaults: alarm 2.80v, protect 2.50v, release 3.10V
    cell_uv = 2850
    cell_uv_release = 3100

    #       PROT | FAIL | Release | Our limit
    # CELL: 55C  | 60C  | 50C     | 50.0C -> 323.0K
    # BMS:  65C  | 70C  | 65C     | 55.0C -> 328.0K
    # MOS:  90C  | 110C | 85C     | 60.0C -> 333.0K
    # Release at limit - 5 deg
    cell_ot = 3230
    cell_ot_release = 3180
    bms_ot = 3280
    bms_ot_release = 3230
    mos_ot = 3330
    mos_ot_release = 3280

    # In regular mode charge to roughly 90%
    # For rebalance charge until 27,95V (=BMS Full)
    pack_charge_v = 27200
    pack_rebalance_v = 27950
    pack_rebalance_v_threshold = 27800
    pack_rebalance_current_threshold = 500

    pack_capacity = 205000
    pack_rebalance_capacity = 240000
