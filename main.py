#!/usr/bin/env -S python3 -u

from pace_master import PaceMaster, pace_instances
from pylon_slave import PylonSlave
from vevor import VevorInverter
from maestro import Maestro, SystemStatus
from coil import CoilState

from translator import Translator
from translator_feeder import TranslatorFeeder

import threading
import ui
from webui import WebUI

import os, time, argparse

# TODO: Move to config.py
IP = '192.168.31.190'

port_base = 4000
port_coil =  port_base + 21
port_slave = port_base + 23
port_vevor = port_base + 25
vevor_slave_id = 1
coil_slave_id = 1

bms_port = [ 2, 4, 6, 8, 10, 12, 38, 40, 42, 44, 46, 48]
bms_count = len(bms_port)

ui.clear_screen()

threads = []

# set timezone to local time
os.environ['TZ'] = "Europe/Warsaw"
time.tzset()

parser = argparse.ArgumentParser()
# Allow to start with a different state than default.
maestro_args = parser.add_argument_group('Maestro')
maestro_args.add_argument("--set_force_disable", action="store_true")
maestro_args.add_argument("--set_force_charging_priority", action="store_true")
maestro_args.add_argument("--set_rebalance_needed", action="store_true")
maestro_args.add_argument("--set_rebalance_active", action="store_true")
maestro_args.add_argument("--set_rebalance_completed", action="store_true")
maestro_args.add_argument("--set_rebalance_threshold_hit", action="store_true")
args = parser.parse_args()

# TODO: maybe move to SytemStatus class as loadCmdlineArgs(args)?
if args.set_force_disable:
    SystemStatus.force_disable = True
if args.set_force_charging_priority:
    SystemStatus.force_charging_priority = True
if args.set_rebalance_needed:
    SystemStatus.rebalance_needed = True
if args.set_rebalance_active:
    SystemStatus.rebalance_active = True
if args.set_rebalance_completed:
    SystemStatus.rebalance_completed = True
if args.set_rebalance_threshold_hit:
    SystemStatus.rebalance_threshold_hit = True

Translator.init(bms_count)

for i in range(0, bms_count):
   master = PaceMaster(i, IP, port_base + bms_port[i])
   pace_instances.append(master)
   t = threading.Thread(target=master.thread)
   threads.append(t)

slave = PylonSlave(len(threads), IP, port_slave)
t = threading.Thread(target=slave.runComm)
threads.append(t)

Translator.thread_id = len(threads)
t = threading.Thread(target=Translator.task)
threads.append(t)

TranslatorFeeder.instance = TranslatorFeeder(len(threads))
t = threading.Thread(target=TranslatorFeeder.instance.task)
threads.append(t)

VevorInverter.instance = VevorInverter(len(threads), IP, port_vevor, vevor_slave_id)
t = threading.Thread(target=VevorInverter.instance.task)
threads.append(t)

maestro = Maestro(len(threads))
t = threading.Thread(target=maestro.task)
threads.append(t)

CoilState.instance = CoilState(len(threads), IP, port_coil, coil_slave_id)
t = threading.Thread(target=CoilState.instance.task)
threads.append(t)

webui = WebUI(len(threads))
t = threading.Thread(target=webui.task)
threads.append(t)

for i in range(0,len(threads)):
    ui.logs.append(["Thread started"])
    threads[i].start()

ui.logs.append(["..."]) # extra for translator logs

# wait for all threads to finish
for t in threads:
    t.join()
