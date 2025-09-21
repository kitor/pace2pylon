from translator import Translator
from vevor import Vevor, VevorInverter, inverterData
from api.pylon_data import AnalogData as AD, ChargeDischargeData as CDD, PylonChargeFlags
import api.pace as pace_api
from ui import tprint
from coil import CoilData, Coil, CoilState
from config import Thresholds

from pace_master import pace_instances

from dataclasses import dataclass
from time import sleep, time
from datetime import datetime

@dataclass
class SystemProtectionStatus:
    # Params as monitored by Maestro, in range of BMS limits
    bat_oc = False
    cell_ov = False
    cell_uv = False
    cell_ot = False
    bms_ot = False
    mos_ot = False

    cell_balancing = False
    @classmethod
    def as_dict(cls):
        return {k:v for k,v in vars(cls).items() \
            if not k.startswith("_") and not isinstance(v, classmethod)}

@dataclass
class BmsProtectionStatus:
    # Params as monitored by BMSes - if we hit those (except special scenarios)
    # then something is wrong
    bat_ov_prot = True

    # All other protections and faults that has no special conditions
    prot = True
    fault = True

    @classmethod
    def as_dict(cls):
        return {k:v for k,v in vars(cls).items() \
            if not k.startswith("_") and not isinstance(v, classmethod)}

class SystemStatus:
    boot_timestamp = int(time())

    # Comm failed to one or more of cells. Disable battery.
    battery_no_comm = True
    coil_no_comm = True

    disable_charge = True
    disable_discharge = True
    force_disable = False

    rebalance_needed = False
    rebalance_active = False
    rebalance_completed = False
    rebalance_cancel = False
    rebalance_threshold_hit = False

    @classmethod
    def as_dict(cls):
        return {k:v for k,v in vars(cls).items() \
            if not k.startswith("_") and not isinstance(v, classmethod)}

'''
Rebalance step-by-step:

If the one of following conditions occurs:
- Any battery cell depleted to SystemProtectionStatus.cell_uv state
- TODO: More than 1 week passed since last rebalance

Set SystemStatus.rebalance_needed flag.

Rebalance states:

1. Request rebalance:
 - set SystemStatus.rebalance_active
 - switch Inverter to Grid priority (USB)
 - set battery charge voltage (Translator) to Thresholds.pack_rebalance_v
 - set Coil Max voltage and pack capacity to pack_rebalance_v, pack_rebalance_capacity

2. During rebalance:
 - If in night tarriff (13-15, 22-6 local time) switch charging to PV & Grid, else PV only
 - If all conditions are met, set SystemStatus.rebalance_completed
    - Coil voltage read > Thresholds.pack_rebalance_v_threshold
    - Coil current read < Thresholds.pack_rebalance_current_threshold
    - None of batteries report balancing anymore

3. Rebalance completed:
 - Set SystemStatus.rebalance_needed = False
 - Set SystemStatus.rebalance_active = False
 - Set battery charge voltage (Translator) to Thresholds.pack_charge_v
 - Unlock any BMS-locked batteries
 - Reset Coil to fully charged
 - Switch Inverter charging to PV only (if needed)
 - Switch Inverter mode to SBU

4. Reset system state to regular mode:
  - Wait for Coil reported pack capacity to fall under Thresholds.pack_capacity and:
     - Set Coil Max voltage and pack capacity to pack_charge_v, pack_capacity
     - Set SystemStatus.rebalance_completed to False
'''

class Maestro:
    '''
    Task that coordinates entire PV system:
     - Monitors battery / coil comm
     - Monitors some battery limits (stricter than BMS)
     - Enforces software battery disable in case of any problems
     - Orchestrates battery pack rebalancing
    '''
    def __init__(self, thread_id):
        self.thread_id = thread_id
        self.reboot_done = False


    def task(self):
        tprint(self.thread_id, "Maestro: task start")
        while True:
            try:
                sleep(1)
                self.verifyComm()
                self.verifyBmsProtect()
                self.verifyBmsFault()
                self.verifyLimits()
                self.verifyBmsCellBalancing()

                # Allow user to request rebalance cancel
                if SystemStatus.rebalance_cancel \
                        and (SystemStatus.rebalance_active or SystemStatus.rebalance_completed):
                    self.cancelRebalance()

                # Process gathered data
                if SystemStatus.rebalance_active:
                    self.processAlarmsRebalance()
                    self.processRebalance()
                else:
                    self.processAlarmsRegular()

                # Switch between regular and rebalance modes
                if SystemStatus.rebalance_needed and not SystemStatus.rebalance_active:
                    self.requestRebalance()

                if SystemStatus.rebalance_active and SystemStatus.rebalance_completed:
                    self.disableRebalance()

                if SystemStatus.rebalance_completed and not SystemStatus.rebalance_active:
                    self.postRebalance()

            except Exception as e:
                # Never stop the loop!
                tprint(self.thread_id, "Maestro: Task exception: " + str(e))


    def requestRebalance(self):
        '''
        Step 1 of Rebalance procedure
        '''
        # set SystemStatus.rebalance_active
        SystemStatus.rebalance_active = True

        # switch Inverter to Grid priority (USB)
        VevorInverter.instance.setOutputMode(0)

        # set battery charge voltage (Translator) to Thresholds.pack_rebalance_v
        Translator.upper_limit = Thresholds.pack_rebalance_v

        # set Coil Max voltage and pack capacity to pack_rebalance_v, pack_rebalance_capacity
        CoilState.instance.writeFullCapacityAndVoltage(
                capacity = Thresholds.pack_rebalance_capacity,
                voltage = Thresholds.pack_rebalance_v
                )

        tprint(self.thread_id, "Maestro: Rebalance enabled")


    def processRebalance(self):
        '''
        Step 2 of Rebalance procedure
        '''
        # If in night tarriff (13-15, 22-6 local time) swtch charging to PV & Grid, else PV only
        # TODO: Don't change setting if all:
        #    - Coil voltage read > Thresholds.pack_rebalance_v_threshold
        #    - Coil current read < Thresholds.pack_rebalance_current_threshold
        #    - but batteries are still balancing
        # ... as this requires no input power
        hour = datetime.now().hour
        if (0 <= hour < 6) or (13 <= hour < 15) or (22 <= hour < 24):
            VevorInverter.instance.setChargingPriority(2)
        else:
            VevorInverter.instance.setChargingPriority(3)

        # TODO: If any battery hit FULLY, maybe temporary disallow discharge?
        # I think having "in case of power loss during rebalance" procedure that
        # will immediately run cancelRebalance() might be better.

        # Voltage will sag down after batteries are fully charged, so we need to keep this in mind
        if (CoilData.values[Coil.PACK_VOLT.value] * 10) > Thresholds.pack_rebalance_v_threshold:
            SystemStatus.rebalance_threshold_hit = True

        # If all conditions are met, set SystemStatus.rebalance_completed
        #    - Coil voltage read exceeded Thresholds.pack_rebalance_v_threshold
        #    - Coil current read < Thresholds.pack_rebalance_current_threshold
        #    - None of batteries report balancing anymore
        if SystemStatus.rebalance_threshold_hit  \
                 and CoilData.values[Coil.PACK_AMPS.value] < Thresholds.pack_rebalance_current_threshold \
                 and SystemProtectionStatus.cell_balancing == False:
            SystemStatus.rebalance_completed = True
            SystemStatus.rebalance_threshold_hit = False
            tprint(self.thread_id, "Maestro: Rebalance completed")


    def disableRebalance(self):
        '''
        Step 3 of Rebalance procedure
        '''
        # Set SystemStatus.rebalance_needed = False
        # Set SystemStatus.rebalance_active = False
        SystemStatus.rebalance_needed = False
        SystemStatus.rebalance_active = False

        # Set battery charge voltage (Translator) to Thresholds.pack_charge_v
        Translator.upper_limit = Thresholds.pack_charge_v

        # Re-enable charge mosfets on batteries with Protections enabled
        self.unlockPackProtections()

        # Set Coil to full, still at "rebalance" capacity but regular voltage
        CoilState.instance.setFull()

        # Switch Inverter charging back to PV only
        VevorInverter.instance.setChargingPriority(3)

        # Switch Inverter mode to SBU
        VevorInverter.instance.setOutputMode(2)

        tprint(self.thread_id, "Maestro: Rebalance finished")


    def postRebalance(self):
        '''
        Step 4 of Rebalance procedure
        '''
        # Wait for Coil reported pack capacity to fall under Thresholds.pack_capacity
        if CoilData.values[Coil.CAPACITY.value] > Thresholds.pack_capacity:
            return

        # Set Coil Max voltage and pack capacity to pack_charge_v, pack_capacity
        CoilState.instance.writeFullCapacityAndVoltage(
                capacity = Thresholds.pack_capacity,
                voltage = Thresholds.pack_charge_v
                )

        # Set SystemStatus.rebalance_completed to False
        SystemStatus.rebalance_needed = False
        SystemStatus.rebalance_active = False
        SystemStatus.rebalance_completed = False
        tprint(self.thread_id, "Maestro: Post-Rebalance job done")


    def cancelRebalance(self):
        '''
        Allow to cancel rebalance at any moment.
        This will leave SoC uncalibrated!
        '''
        # TODO: This possibly could be merged with disableRebalance() and
        # postRebalance(). It does the same thing minus waiting for thresholds
        # and resetting SoC meter.
        SystemStatus.rebalance_cancel = False
        SystemStatus.rebalance_needed = False
        SystemStatus.rebalance_active = False
        SystemStatus.rebalance_completed = False
        SystemStatus.rebalance_threshold_hit = False

        # Set battery charge voltage (Translator) to Thresholds.pack_charge_v
        Translator.upper_limit = Thresholds.pack_charge_v

        # Re-enable charge mosfets on batteries with Protections enabled
        self.unlockPackProtections()

        # Do not execute Coil "set to full" as we cancelled it mid-balance

        # Switch Inverter charging back to PV only
        VevorInverter.instance.setChargingPriority(3)

        # Set Coil Max voltage and pack capacity to regular mode
        CoilState.instance.writeFullCapacityAndVoltage(
                capacity = Thresholds.pack_capacity,
                voltage = Thresholds.pack_charge_v
                )

        tprint(self.thread_id, "Maestro: Rebalance cancelled")


    def unlockPackProtections(self):
        '''
        Re-enable battery packs that have Overvolt or Fully charged flags set
        '''
        for i in range(len(Translator.batteries)):
            # packs.append(i)
            if any([
                Translator.batteries[i][0x44]["protect_state_1"] & 0x05, # Overvolt
                Translator.batteries[i][0x44]["protect_state_2"] & 0x80  # Fully charged
            ]):
                pace_instances[pack_id].tryPostMsg(
                    pace_api.WriteChargeMosfetSwitchCommand, self.paceRebootCbr)


    def paceRebootCbr(self, battery_id, cid2, data, failed=False):
        '''
        Callback for pack reboot
        '''
        tprint(self.thread_id, f"Maestro: {battery_id}: WriteChargeMosfetSwitchCommand completed")
        pass


    def processAlarmsRegular(self):
        '''
        Alarms processing, regular procedure
        '''
        # Gather data from common processing
        disable_discharge, disable_charge, rebalance_needed = self.processAlarmsCommon()

        # In regular case BMS overvoltage protection should never happen.
        # If it does, BMS locks both charge and discharge (meh...)
        # so we need to protect entire system by disabling the whole pack
        if BmsProtectionStatus.bat_ov_prot:
            disable_charge = True
            disable_discharge = True

        # We also have a defense for BMS ov prot via software Cell OV prot.
        # In case soft cell OV limit is exceeded, just disable the charging.
        if SystemProtectionStatus.cell_ov:
            disable_charge = True

        self.commitAlarms(disable_discharge, disable_charge, rebalance_needed)


    def processAlarmsRebalance(self):
        '''
        Alarms processing, during rebalance procedure
        '''
        # Post-rebalance stage uses "full" (regular) checks
        if SystemStatus.rebalance_completed:
            self.processAlarmsRegular()
            return

        # During rebalance stage we ignore BMS and Maestro OV protection
        # as hitting BMS OT prot activates BMS cell balancing.
        disable_discharge, disable_charge, rebalance_needed = self.processAlarmsCommon()
        self.commitAlarms(disable_discharge, disable_charge, rebalance_needed)


    def commitAlarms(self, disable_discharge, disable_charge, rebalance_needed):
        '''
        Converts gathered alarms into actions
        '''
        Translator.setBatteryChargeDischarge(
            enable_charge = not disable_charge,
            enable_discharge = not disable_discharge
        )
        if SystemStatus.disable_charge != disable_charge:
            tprint(self.thread_id, "Maestro: Battery charge " + ("disabled" if disable_charge else "enabled"))
        if SystemStatus.disable_discharge != disable_discharge:
            tprint(self.thread_id, "Maestro: Battery discharge " + ("disabled" if disable_discharge else "enabled"))

        SystemStatus.disable_charge = disable_charge
        SystemStatus.disable_discharge = disable_discharge

        if rebalance_needed:
            SystemStatus.rebalance_needed = True
            tprint(self.thread_id, "Maestro: Rebalance needed!")


    def processAlarmsCommon(self):
        '''
        Common part of alarms processing, everything except potential
        Cell OV which can be part of Rebalance process
        '''
        disable_discharge = False
        disable_charge = False
        rebalance_needed = False

        # Any failure conditions that should disable battery immediately
        if any([
                SystemStatus.force_disable,
                SystemStatus.battery_no_comm,
                SystemStatus.coil_no_comm,
                BmsProtectionStatus.prot,
                BmsProtectionStatus.fault,
                SystemProtectionStatus.bat_oc,
                SystemProtectionStatus.cell_ot,
                SystemProtectionStatus.bms_ot,
                SystemProtectionStatus.mos_ot
                ]):
            disable_discharge = True
            disable_charge = True

        # In normal conditions we wouldn't hit software undervolt protection.
        # If that happens, Coil redout is out of sync and we let batteries
        # to discharge too much. Thus disable charge and trigger rebalance.
        if SystemProtectionStatus.cell_uv:
            disable_discharge = True
            rebalance_needed = True

        return (disable_discharge, disable_charge, rebalance_needed)


    def verifyComm(self):
        '''
        Check for BMS and Coil communcation failures
        '''
        if all(Translator.stats["battery_comm"]):
            SystemStatus.battery_no_comm = False
        else:
            SystemStatus.battery_no_comm = True

        SystemStatus.coil_no_comm = not CoilData.comm


    def verifyBmsProtect(self):
        '''
        Check for BMS-reported protections
        '''
        ov_reported = False

        for battery in Translator.batteries:
            # No data from battery, assume battery protection
            if not 0x44 in battery.keys() or not "protect_state_1" in battery[0x44].keys():
                BmsProtectionStatus.prot = True
                return

            # Any protection flag enabled except those listed, enable protection
            if any([
                    battery[0x44]["protect_state_1"] & 0x7A, # byte 8 undefined, byte 0 - Cell OV, byte 2 - Pack OV
                    battery[0x44]["protect_state_2"] & 0x7F  # byte 8 is fully charged
                    ]):
                # Report on first failure detected.
                BmsProtectionStatus.prot = True
                return

            # Battery OV protection reported, this is fine in some scenarios (full charge)
            # Report that back but keep looking for other batteries
            if battery[0x44]["protect_state_1"] & 0x5:   # Allow discharge on OV faults
                BmsProtectionStatus.bat_ov_prot = True
                ov_reported = True

        # If we got here, we are good.
        # Clear protection flags
        if not ov_reported:
            BmsProtectionStatus.bat_ov_prot = False
        BmsProtectionStatus.prot = False


    def verifyBmsCellBalancing(self):
        '''
        Check BMSes for active cell balancing
        '''
        for battery in Translator.batteries:
            # No data from battery, assume battery fault
            if not 0x44 in battery.keys() or not "balance_state_1" in battery[0x44].keys():
                SystemProtectionStatus.bat_fault = True
                return

            if battery[0x44]["balance_state_1"] or battery[0x44]["balance_state_2"]:
                # Report on first balancing detected
                SystemProtectionStatus.cell_balancing = True
                return

        SystemProtectionStatus.cell_balancing = False


    def verifyBmsFault(self):
        '''
        Check for BMS-reported faults
        '''
        for battery in Translator.batteries:
            # No data from battery, assume battery fault
            if not 0x44 in battery.keys() or not "protect_state_1" in battery[0x44].keys():
                BmsProtectionStatus.bat_fault = True
                return

            if battery[0x44]["fault_state"] & 0x7F:  # byte 8 undefined
                # Report on first protection detected
                BmsProtectionStatus.fault = True
                return

        # If we got here, we are good.
        # Clear fault flags
        BmsProtectionStatus.fault = False


    def verifyLimits(self):
        # check analog data
        AD.lock()
        CDD.lock()
        try:
            self.__verifyLimits()
        except Exception as e:
            tprint(self.thread_id, f"Maestro: verifyLimits Exception {str(e)}")
            SystemStatus.battery_no_comm = True
        AD.unlock()
        CDD.unlock()


    def __verifyLimits(self):
        if not AD.data_ready or not CDD.data_ready:
            # No data ready, enforce disable
            SystemStatus.battery_no_comm = True
            return

        # Enforce dicharge limits, inverter doesn't seem to care about it.
        # AD is accurancy 3, CCD 1 thus divide.
        # Allows for temporary overshot by 1.2. as we limit BMS values to 0.8
        # This gives our limit 0.96 of BMS
        # TODO: Shall I disable battery instead? I can't think about anything
        # that would allow such a condition to exists. Also, check Vevor
        # badly documented SET_BATTERY_DISCHARGE_PROT_AMPS which is disabled
        # by default... and if working should handle that inverter-side
        if (AD.total_current/100) * 1.2 > min([CDD.max_charge, -CDD.max_discharge]):
            tprint(self.thread_id, "Maestro: Overcurrent detected!")
            SystemProtectionStatus.bat_oc = True
        else:
            SystemProtectionStatus.bat_oc = False

        # Set protection flags when params exceed limits
        if AD.cell_temp_max > Thresholds.cell_ot:
            SystemProtectionStatus.cell_ot = True

        if AD.bms_temp_max > Thresholds.bms_ot:
            SystemProtectionStatus.bms_ot = True

        if AD.mosfet_temp_max > Thresholds.mos_ot:
            SystemProtectionStatus.mos_ot = True

        if AD.cell_v_max > Thresholds.cell_ov:
            SystemProtectionStatus.cell_ov = True

        if AD.cell_v_min < Thresholds.cell_uv:
            SystemProtectionStatus.cell_uv = True

        # Clear protection flags if params returned to safe values
        if SystemProtectionStatus.cell_ot and AD.cell_temp_max < Thresholds.cell_ot_release:
            SystemProtectionStatus.cell_ot = False

        if SystemProtectionStatus.bms_ot and AD.bms_temp_max < Thresholds.bms_ot_release:
            SystemProtectionStatus.bms_ot = False

        if SystemProtectionStatus.mos_ot and AD.mosfet_temp_max < Thresholds.mos_ot_release:
            SystemProtectionStatus.mos_ot = False

        if SystemProtectionStatus.cell_ov and AD.cell_v_max < Thresholds.cell_ov_release:
            SystemProtectionStatus.cell_ov = False

        if SystemProtectionStatus.cell_uv and AD.cell_v_min > Thresholds.cell_uv_release:
            SystemProtectionStatus.cell_uv = False
