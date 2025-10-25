var boot_timestamp = 0;
var battery_count = 0;
var Vevor = {}
var VevorValues = {
    OutputPriority: [
        "Grid First", "Solar First", "SBU"
    ],
    ChargePriority: [
        "Grid > PV", "PV > Grid", "PV & Grid", "PV Only"
    ],
    WorkingMode: [
        "Power ON", "Standby", "Grid", "Off-Grid", "Bypass", "Charging", "Fault"
    ]
}

var Coil = {}
var CoilValues = ["Idle", "Discharging", 'Charging']

var analogData = {}
var inverter = []
var cdd = {}
var batteries = {}
var systemStatus = {}
var systemProtectionStatus = {}
var bmsProtectionStatus = {}
var batteryPack = {}

function $(arg){
    return document.querySelector(arg)
}

//wrapper for XHMHttpRequest
function getJson(item, callback){
    var request = new XMLHttpRequest();
    request.timeout = 2000; //wait 2 seconds
    request.open('GET', item, true);
    request.onreadystatechange = function(){
        if (request.readyState === 4){
            if(request.status === 200){
                callback(JSON.parse(request.response), item);
            }
        }
    };
    request.send();
}

function drawBool(val){
    if(val){
      return '<span style="color: #0F0">&#x2713;</span>'
    }
    return '<span style="color: #F00">&#x2717;</span>'
}

function drawProt(val){
    if(val){
      return '<span style="font-weight: bold; color: #F00">!</span>'
    }
    return '<span style="color: #0F0">&#x2713;</span>'
}

var maestroUI = {
    monitor: false,
    init: function(){
        console.log("Maestro UI init")
        this.monitor = $("#maestro .data")
    },
    update: function(){
      this.updateMonitor()
    },
    setError: function(){
        this.monitor.innerHTML = "Maestro data error"
    },
    updateMonitor: function(){
        buf = `Allow charge ${ drawBool(!systemStatus.disable_charge) }, discharge ${ drawBool(!systemStatus.disable_discharge) }, 
               Force disable: <a href="/toggle/BatteryDisable">${ systemStatus.force_disable }</a><br />
               Comm: battery ${ drawBool(!systemStatus.battery_no_comm) }, coil ${ drawBool(!systemStatus.coil_no_comm) } <br />
               BMS protect ${ drawProt(bmsProtectionStatus.prot) }, fault ${ drawProt(bmsProtectionStatus.fault) },
               cell OV ${ drawProt(bmsProtectionStatus.bat_ov_prot) }, cell balancing active: ${systemProtectionStatus.cell_balancing }<br />
               Maestro protect: Cell OV ${ drawProt(systemProtectionStatus.cell_ov) },  UV: ${ drawProt(systemProtectionStatus.cell_uv) },
               OC: ${ drawProt(systemProtectionStatus.bat_oc) }, &#127777; BMS: ${ drawProt(systemProtectionStatus.bms_ot) },
               &#127777; MOS: ${ drawProt(systemProtectionStatus.mos_ot) }, &#127777; CELL: ${ drawProt(systemProtectionStatus.cell_ot) }. <br />
               Rebalance needed: <a href="/toggle/RebalanceNeeded">${ systemStatus.rebalance_needed }</a>,
               active: ${ systemStatus.rebalance_active }, threshold:  <a href="/toggle/RebalanceThreshold">${ systemStatus.rebalance_threshold_hit }</a>,
               completed: ${ systemStatus.rebalance_completed };
               <a href="/toggle/CancelRebalance">Cancel rebalance</a>`
        this.monitor.innerHTML = buf
    }
}

var batteryDetailsUI = {
    container: false,
    batteries: [],
    headers: [],
    volts: [],
    cells: [],
    stats: [],
    init: function(){
        console.log("Battery details UI init")
        this.container = $("#batteries")
        this.container.innerHTML = "" // reset container
        for( i = 0; i < battery_count; i++){
            battery = document.createElement("span")
            battery.classList.add("battery-container")

            header = document.createElement("h3")
            battery.appendChild(header)

            volts = document.createElement("span")
            battery.appendChild(volts)

            cells = document.createElement("div")
            cells.classList.add("battery")
            battery.appendChild(cells)

            stats = document.createElement("span")
            battery.appendChild(stats)

            this.headers.push(header)
            this.volts.push(volts)
            this.cells.push(cells)
            this.stats.push(stats)
            this.batteries.push(battery)

            this.container.appendChild(battery)
        }
    },
    update: function(){
        for( i = 0; i < battery_count; i++){
             try {
                 this.updateEntry(i)
             } catch (error) {
                 this.setError(i)
             }
         }
    },
    setError: function(i){
        this.headers[i].innerHTML = "Error"
    },
    updateEntry: function(i){
        analogInfo = batteries[i][0x42]
        flags = batteries[i][0x44]

        buf = `Battery ${i}: ${ analogInfo.soc }%`
        this.headers[i].innerHTML = buf

        amps = (analogInfo["current"] / 100).toFixed(2)
        volts = (analogInfo["volts"] / 1000).toFixed(3)
        buf = `${amps}A @ ${volts}V<br />`
        this.volts[i].innerHTML = buf

        balance_data = ("00000000" + flags["balance_state_1"].toString(2)).slice(-8).split('').reverse().join('')
        cells_buf = ""
        for (cell in analogInfo.cells){
            is_balancing = balance_data[cell]
            cell = analogInfo.cells[cell]
            cls = ""
            volts = (cell/1000).toFixed(3)
            if (cell == analogInfo["cell_v_min"]){
                cls = "cell-min"
            }
            else if (cell == analogInfo["cell_v_max"]){
                cls = "cell-max"
            }
            if(is_balancing == "1"){
                cls += " cell-balancing"
            }
            cells_buf += `<div class="cell ${cls}">${volts}</div>`
        }
        this.cells[i].innerHTML = cells_buf

        cell_temp_min = ((analogInfo["cell_temp_min"] - 2731) / 10).toFixed(1)
        cell_temp_max =  ((analogInfo["cell_temp_max"] - 2731) / 10).toFixed(1)
        mos_temp =  ((analogInfo["mosfet_temp"] - 2731) / 10).toFixed(1)
        bms_temp = ((analogInfo["bms_temp"] - 2731) / 10).toFixed(1)
        flags_fault = flags["fault_state"]
        flags_prot1 = ("00000000" + flags["protect_state_1"].toString(2)).slice(-8)
        flags_prot2 = ("00000000" + flags["protect_state_2"].toString(2)).slice(-8)
        buf = `<b>Temperatures (C)</b><br />
               Cells: ${cell_temp_min}, <span class="temp">${cell_temp_max}</span><br />
               MOS: ${mos_temp}<br />
               BMS: ${bms_temp}<br />
               <b>Flags</b><br />
               Faults: ${flags_fault}<br />
               Protect1: ${flags_prot1}<br />
               Protect2: ${flags_prot2}<br />
               Balance: ${balance_data}<br />`
        this.stats[i].innerHTML = buf
    }
}

var batteryStatsUI = {
    header: false,
    general: false,
    temps: false,
    charge: false,
    init: function(){
        console.log("Battery stats UI init")
        this.header = $("#battery-stats-header")
        this.general = $("#battery-stats-general .data")
        this.temps = $("#battery-stats-temperatures .data")
        this.charge = $("#battery-stats-charge .data")
    },
    update: function(){
        this.updateHeader()
        this.updateGeneral()
        this.updateTemps()
        this.updateCharge()
    },
    updateHeader: function(){
        volts = analogData.average_voltage / 1000
        amps = analogData.total_current / 100
        pow = (volts * amps).toFixed(0)
        soc = analogData.soc
        buf = `Battery: ${ pow }W: ${ amps.toFixed(1) }A @ ${ volts.toFixed(3) }V, ${ soc }%`
        this.header.innerHTML = buf
    },
    updateGeneral: function(){
        cell_v_min = (analogData.cell_v_min / 1000).toFixed(3)
        cell_v_min_id = analogData.cell_v_min_id
        cell_v_max = (analogData.cell_v_max / 1000).toFixed(3)
        cell_v_max_id = analogData.cell_v_max_id
        total_current = (analogData.total_current / 100).toFixed(1)
        average_voltage = (analogData.average_voltage / 1000).toFixed(3)
        buf = `Cells: &uarr;${cell_v_max}@${cell_v_max_id}, &darr;${cell_v_min}@${cell_v_min_id}<br />
               Total current: ${total_current}A<br />
               Average voltage: ${average_voltage}V<br />`
        this.general.innerHTML = buf
    },
    updateTemps: function(){
        cell_avg = ((analogData.cell_temp_avg - 2731) / 10).toFixed(1)
        cell_min = ((analogData.cell_temp_min - 2731) / 10).toFixed(1)
        cell_max = ((analogData.cell_temp_max - 2731) / 10).toFixed(1)
        cell_min_id = analogData.cell_temp_min_id
        cell_max_id = analogData.cell_temp_max_id
        mos_avg = ((analogData.mosfet_temp_avg - 2731) / 10).toFixed(1)
        mos_min = ((analogData.mosfet_temp_min - 2731) / 10).toFixed(1)
        mos_max = ((analogData.mosfet_temp_max - 2731) / 10).toFixed(1)
        mos_min_id = analogData.mosfet_temp_min_id
        mos_max_id = analogData.mosfet_temp_max_id
        bms_avg = ((analogData.bms_temp_avg - 2731) / 10).toFixed(1)
        bms_min = ((analogData.bms_temp_min - 2731) / 10).toFixed(1)
        bms_max = ((analogData.bms_temp_max - 2731) / 10).toFixed(1)
        bms_min_id = analogData.bms_temp_min_id
        bms_max_id = analogData.bms_temp_max_id
        buf = `Cells: ~${cell_avg}: &uarr;${cell_max}@${cell_max_id}, &darr;${cell_min}@${cell_min_id}<br />
               MOS: ~${mos_avg}: &uarr;${mos_max}@${mos_max_id}, &darr;${mos_min}@${mos_min_id}<br />
               BMS: ~${bms_avg}: &uarr;${bms_max}@${bms_max_id}, &darr;${bms_min}@${bms_min_id}<br />`
        this.temps.innerHTML = buf
    },
    updateCharge: function(){
        charge_volts = (cdd.upper_limit / 1000).toFixed(3)
        charge_amps =  (cdd.max_charge / 10).toFixed(1)
        discharge_volts = (cdd.lower_limit / 1000).toFixed(3)
        discharge_amps = (cdd.max_discharge / 10).toFixed(1)
        flags = ("00000000" + cdd.state_flags.toString(2)).slice(-8)
        buf = `Volts: Charge ${charge_volts}V, Discharge ${discharge_volts}V<br />
               Amps: Charge ${charge_amps}A, Discharge ${discharge_amps}A<br />
               Flags: ${flags} <a href="/toggle/FullCharge">Toggle full charge</a><br /><br />`
        this.charge.innerHTML = buf
    }
}

var batteryPackUI = {
    general: false,
    init: function(){
        console.log("Battery pack UI init")
        this.general = $("#battery-pack-general .data")
    },
    update: function(){
        this.updateGeneral()
    },
    updateGeneral: function(){
        pack_percent = batteryPack[Coil.PERCENT]
        pack_volt = (batteryPack[Coil.PACK_VOLT] / 100).toFixed(2)
        pack_amps = (batteryPack[Coil.PACK_AMPS] / 100).toFixed(2)
        pack_power = (batteryPack[Coil.PACK_POWER] / 10).toFixed(1)  // Just skip HI, it will never exceed it
        pack_energy = (batteryPack[Coil.PACK_ENERGY] / 100).toFixed(2)
        pack_capacity = (batteryPack[Coil.CAPACITY] / 1000).toFixed(3)
        pack_state = CoilValues[batteryPack[Coil.STATE]]
        buf = `<b>${pack_percent}%</b> ${pack_state}<br />
               ${pack_volt}V ${pack_amps}A ${pack_power}W<br />
               ${pack_energy} Wh / ${pack_capacity}Ah<br />`
        this.general.innerHTML = buf
    }
}

var inverterUI = {
    header: false,
    summary: false,
    output: false,
    grid: false,
    battery_header: false,
    battery: false,
    solar: false,
    charging: false,
    charging_header: false,
    init: function(){
        this.header = $("#inverter-header")
        this.summary = $("#inverter-summary")
        this.output = $("#inverter-output .data")
        this.grid = $("#inverter-grid .data")
        this.battery = $("#inverter-battery .data")
        this.battery_header = $("#inverter-battery-header")
        this.solar = $("#inverter-solar .data")
        this.charging = $("#inverter-charging .data")
        this.charging_header = $("#inverter-charging-header")
        console.log("Inverter UI init")
    },
    update: function(){
        try {
            this.updateSummary()
            this.updateOutput()
            this.updateGrid()
            this.updateBattery()
            this.updateSolar()
            this.updateCharging()
        } catch (error) {
            this.setError()
        }
    },
    setError: function(){
        this.header.innerHTML = "Inverter data fetch failed"
    },
    updateSummary: function(){
        mode = VevorValues.WorkingMode[inverter[Vevor.WORKING_MODE]]
        this.header.innerHTML = `Inverter: ${mode}`

        temp_dcdc = inverter[Vevor.DCDC_TEMP]
        temp_inverter = inverter[Vevor.INVERTER_TEMP]
        temp_mppt = inverter[Vevor.INVERTER_TEMP]
        fault1 = ("0000" + inverter[Vevor.FAULT_CODE_1].toString(2)).slice(-4)
        fault2 = ("0000" + inverter[Vevor.FAULT_CODE_2].toString(2)).slice(-4)
        warn1 = ("0000" + inverter[Vevor.WARN_CODE_1].toString(2)).slice(-4)
        warn2 = ("0000" + inverter[Vevor.WARN_CODE_2].toString(2)).slice(-4)

        buf = `DCDC ${temp_dcdc}C, Inverter ${temp_inverter}C, MPPT ${temp_mppt}C<br />
               FaultFlags: ${fault1}${fault2} WarnFlags: ${warn1}${warn2}<br />`
        this.summary.innerHTML = buf
    },
    updateOutput: function(){
        mode = VevorValues.OutputPriority[inverter[Vevor.SET_OUTPUT_PRIO]]
        volts = inverter[Vevor.OUTPUT_VOLTS] / 10
        pow = inverter[Vevor.OUTPUT_ACTIVE_POW]
        buf = `Mode: <span id="inverter-mode"> ${mode}</span><br />
               <span id="inverter-voltage"> ${volts.toFixed(1)}V
               <span id="inverter-power"> ${pow}W</span><br />`
        this.output.innerHTML = buf
    },
    updateGrid: function(){
        volts = inverter[Vevor.GRID_VOLTS] / 10
        pow = inverter[Vevor.GRID_POWER]
        buf = `${volts.toFixed(1)}V ${pow}W`
        this.grid.innerHTML = buf
    },
    updateBattery: function(){
        soc = inverter[Vevor.BATTERY_SOC]
        this.battery_header.innerHTML = `Battery: ${soc}%`

        watts = inverter[Vevor.BATTERY_POWER]
        amps = inverter[Vevor.BATTERY_AMPS] / 10
        volts = inverter[Vevor.BATTERY_VOLTS] / 10
        charge_li = inverter[Vevor.LI_MAX_CHARGE_AMPS] / 10
        charge_nocomm = inverter[Vevor.SET_BATTERY_CHARGE_AMPS] / 10
        buf = `${ watts }W: ${ amps.toFixed(1) }A @ ${ volts }V<br />
               &#x1F50B;:  Li: ${charge_li.toFixed(1) }A, NC: ${charge_nocomm.toFixed(1) }A`
        this.battery.innerHTML = buf
    },
    updateSolar: function(){
        pow = inverter[Vevor.PV_POWER]
        amps =  inverter[Vevor.PV_AMPS] / 10
        volts =  inverter[Vevor.PV_VOLTS] / 10
        buf = `${ pow }W: ${ amps.toFixed(1) }A @ ${ volts.toFixed(1) }V<br />`
        this.solar.innerHTML = buf
    },
    updateCharging: function(){
        mode = VevorValues.ChargePriority[inverter[Vevor.SET_BATTERY_CHARGE_PRIO]]
        soc_low = inverter[Vevor.SET_BATTERY_SOC_LOW]
        soc_high = inverter[Vevor.SET_BATTERY_SOC_HIGH]
        soc_cutoff = inverter[Vevor.SET_BATTERY_SOC_CUTOFF]
        charge_pow = inverter[Vevor.INV_CHARGING_POWER]
        charge_amps = inverter[Vevor.INV_CHARGING_AMPS] / 10
        pv_amps = inverter[Vevor.PV_CHARGING_AMPS]/10
        is_auto = systemStatus.force_charging_priority ? "Forced" : "Auto"

        this.charging_header.innerHTML = `Charging: ${mode} (${is_auto})`
        buf = `Set <a href="/toggle/ForceChargingPriority/2">PV + Grid</a> | <a href="/toggle/ForceChargingPriority/3">PV only</a> | <a href="/toggle/ResetChargingPriority/">Auto</a><br />
               Limits: &darr;${ soc_low }% &uarr;${ soc_high }% &cross;${ soc_cutoff }%<br />
               &#128268; ${ charge_pow }W; &#x2600; ${ pv_amps.toFixed(1) }A; ~ ${ charge_amps.toFixed(1) }A<br />`
        this.charging.innerHTML = buf
    }
}

var titleUI = {
    init: function(){
        console.log("Title UI init")
    },
    update: function(){
        out_pow = inverter[Vevor.OUTPUT_ACTIVE_POW]
        bat_soc = inverter[Vevor.BATTERY_SOC]
        solar_pow = inverter[Vevor.PV_POWER]
        document.title = `PV ${solar_pow}W / ${bat_soc}% / Out ${out_pow}W`
    }
}

var ui = {
  init: function(){
    inverterUI.init()
    batteryStatsUI.init()
    maestroUI.init()
    batteryDetailsUI.init()
    titleUI.init()
    batteryPackUI.init()
  },
  update: function(){
    inverterUI.update()
    batteryStatsUI.update()
    maestroUI.update()
    batteryDetailsUI.update()
    titleUI.update()
    batteryPackUI.update()
  }
}

var pollData = {
  start: function(){
      console.log("Hello");
      pollData.getStaticData()
  },
  getStaticData: function(){
      getJson("/api/static/", pollData.callbacks.setStaticData)
  },
  pollDynamicData: function(){
      getJson("/api/", pollData.callbacks.setDynamicData)
  },
  callbacks: {
    setDynamicData: function(data){

      if(data.boot_timestamp == boot_timestamp) {
          inverter = data.inverter
          analogData = data.analogData
          cdd = data.cdd
          batteries = data.batteries
          systemStatus = data.systemStatus
          systemProtectionStatus = data.systemProtectionStatus
          bmsProtectionStatus = data.bmsProtectionStatus
          batteryPack = data.batteryPack
          ui.update()
          setTimeout(pollData.pollDynamicData, 1000)
      }
      else {
          console.log("Timestamp changed, poll static data")
          pollData.getStaticData()
      }

    },
    setStaticData: function(data){
      boot_timestamp = data.boot_timestamp
      battery_count = data.battery_count
      Vevor = data.Vevor
      Coil = data.Coil

      // start dynamic data polling
      ui.init()
      pollData.pollDynamicData()
    }
  }
}

pollData.start()
