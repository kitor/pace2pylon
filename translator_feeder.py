from ui import tprint
from pace_master import pace_instances
import api.pace as pace_api

from time import sleep

from translator import Translator


class TranslatorFeeder:
    instance = None
    def __init__(self, thread_id):
        self.thread_id = thread_id
        self.count = len(pace_instances)

        self.regular_waiting = []
        self.extra_waiting = []

        for i in range(self.count):
            self.regular_waiting.append(0)
            self.extra_waiting.append(0)

        self.regular_commands = [
                pace_api.ReadAnalogData,
                pace_api.ReadPackStatus
            ]

        self.extra_commands = [
                pace_api.ReadPackOverVoltageConfiguration,
                pace_api.ReadPackUnderVoltageConfiguration,
                pace_api.ReadChargeOverCurrentConfiguration,
                pace_api.ReadDischargeSlowOverCurrentConfiguration
            ]

    def run(self):
        sleep(5)
        while True:
            for tick in range(10):
                for battery_id in range(self.count):
                    # In case of read failures this will execute only once per full loop
                    if tick == 0 and self.extra_waiting[battery_id] < 1:
                        for cmd in self.extra_commands:
                            if pace_instances[battery_id].tryPostMsg(cmd, self.dataReadyExtraCbr):
                                self.extra_waiting[battery_id] += 1

                    if self.regular_waiting[battery_id] < 1:
                        for cmd in self.regular_commands:
                            if pace_instances[battery_id].tryPostMsg(cmd, self.dataReadyRegularCbr):
                                self.regular_waiting[battery_id] += 1
                sleep(1)

    def dataReadyExtraCbr(self, battery_id, cid2, data, failed=False):
        self.extra_waiting[battery_id] -= 1
        if not failed:
            Translator.setBatteryData(battery_id, cid2, data)

        tprint(self.thread_id, f"dataReadyExtraCbr: {battery_id}, {failed}")

    def dataReadyRegularCbr(self, battery_id, cid2, data, failed=False):
        self.regular_waiting[battery_id] -= 1
        if not failed:
            Translator.setBatteryData(battery_id, cid2, data)

        tprint(self.thread_id, f"dataReadyRegularCbr: {battery_id}, {failed}")
