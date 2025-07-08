# pace2pylon

Implementation of emulated master BMS for Pylontech protocol and orchestrator for PV system.

This code is for reference only, as-is it applies to my very specific setup, explained below.

## Hardware

What I have is:
 * Vevor EML3500-24L hybrid solar inverter
 * Eco-Worthy battery monitor 200A coulombometer (the old one)
 * A stack of 12 * 520Wh 24V LiFePo4 batteries running on custom Pace BMS

And the main problems are:

This custom Pace BMS lacks ability to daisy-chain communication between batteries.
Just RS232 running Pace v25 protocol, lack of 485/CAN and ability to set battery ID.
Not possible to switch into Pylontech protocol (aka Pace v20), and even if it was
available - still unable to set battery ID / daisy chain them.

Additionally Vevor supports only Pylontech protocol. And there's no communication
dongle available for Vevor anyway, so RS485 Modbus protocol had to be implemented.

To add more fun, Vevor asks for undocumented commands 0x61 and 0x63. Fortunately
I found one of other inverter vendors documented those in their document.

Battery monitor is standalone unit without any comm available. I found that
communication betweeen the "coil" (coulombometer) and display is just Modbus
over RS485 with extra custom command for setting readout to 0/100%.

## The goal

Marry this together by implementing:

 * Console server that exposes:
   * each battery via RS232
   * Vevor BMS port via RS485
   * Vevor comm port via RS232
   * Battery monitor via RS485

 * Python code that handles:
   * Talking with Pace batteries
   * Emulating responses of Pylontech battery stack for inverter
   * Fetching and setting Inveter and battery monitor data
   * Implementing all the safety features (if anything seems wrong, cut battery discharge)
   * Extra: Provide ability to run rebalancing cycle

## Battery monitor, battery readouts, rebalancing:

TL;DR: Each battery BMS monitors its own state, but it is inacurate
(they don't count loads below 0.5A... which with 12 cells is most of the time).

Add this to slightly different currents between each battery (which is normal,
even with busbar topology) and battery reportings fail out of sync quickly,
making them unrealible to get state of charge figures.

The coulombometer is installed on main wire between busbar and inverter.
This provides data accurate also to roughly 0.5A, but measues total of entire
battery system.

Still requires recalibration once upon a time as it measures only
charge/discharge amps, doesn't apply any corrections for the fact amps in > amps
available out. It has provision to set low / high voltage which will auto-reset
readings to 0/100%. But in a real life scenario you don't want to run LiFePo4
in full cycles so extra logic is needed.

Ah, and extra fun with those Pace BMSes. To force their internal cell balacing,
one need to activate cell/pack overvoltage protection (!). Yup. And this shoud
also cut out pack discharge, but for whatever reason those BMSes locks both
charge and discharge.

Thus actual process of rebalance was needed to be implemented - this is
described in comments of maestro.py

## Fail-save

Physical system has a lot of fuses:
 * Each battery pack BMS is rated for 30A
 * BMSes have software protection for 35A
 * Each battery pack has internal 50A fuse (replacable, requires dismounting)
 * Each battery pack has external 30A fuse on busbar connection
 * Busbar has 150A fuse on inverter connection (137A is the theoretical max in this system)

Software enforces battery "software" shutdown in case of any failures and most
protections detected. The only exceptions are:
 * software undervolt protection still allows for charging
 * software overvolt protection still allows for discharging
 * while in "rebalaincing process", BMS overvolt protection triggerred is expected

Software will also disable battery in case communication failed with any battery
pack or coulombometer.

But! in case software fails to respond to inverter BMS comm, there's a catch:
Vevor in lack of comm... switches to no-comm settings :(
Thus inverter for no-comm mode is set as follows:
 * Maximum charge 30A (impossible to set less)
 * Maximum charge voltage: 24.5V (this is below "pack discharged" state)
 * Maximum discharge voltage: 24.4V (step than the above)

This is the best I can do with settings available, but it makes possibility
the pack will be charged in a failure state very low and limits it to a short
amount of time.

This, incl. all physical protection (incl. built-in BMS locks)
shall prevent any problems in worst-case scenario (both comm failed and batteries
report actual problems)

## Project structure
 * `main.py`: Main program entry
 * `debug_run.py`: Alternative entry, with mocking inverter and coil classes
 * `config.py`: Some of the global software configs
 * `coil.py`: Coulombometer communication
 * `vevor.py`: Vevor inverter user-side communcation
 * `pace_master.py`: Communication via message queue with batteries (Pace protocol master)
 * `pylon_slave.py`: Communication with inverter, Pylontech BMS slave emulation
 * `translator.py`: Convertion of gathered data(from coil, pace) to Pylontech-ready format
 * `translator_feeder.py`: Implementation of gathering battery data and populatng Translator inputs
 * `maestro.py`: Implementation of system state monitoring, Fail-save enforcements and pack rebalancing
 * `webui.py`: API server for WebUI and MQTT publishers
 * `publisher.py`: Standalone API to MQTT publisher for HA integration
 * `web/`: WebUI static files
 * `api/`: Classes implementing Pace and Pylontech messages encoding/decoding

Other files: various tests and so on.
