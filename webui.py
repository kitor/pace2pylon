from translator import Translator
from vevor import *
from coil import *
from maestro import SystemStatus, BmsProtectionStatus, SystemProtectionStatus
from api.pylon_data import *
from ui import tprint

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from time import sleep
import json

def do_redirect(url):
    return f'<html><head><meta http-equiv="refresh" content="0; url={url}"></head></html>'

def do_api(path):
    if path.endswith("/static/"):
        # Dump static data, required only once per reload.
        # No need to serialize static stuff on every call.
        obj = {
            "boot_timestamp": SystemStatus.boot_timestamp,
            "battery_count": len(Translator.batteries),
            "Vevor": Vevor.as_dict(),
            "Coil" : Coil.as_dict()
        }
        return json.dumps(obj)
    else:
        obj = {
            "boot_timestamp": SystemStatus.boot_timestamp,
            "batteries": Translator.batteries,
            "comm_avail": Translator.stats["battery_comm"],
            "analogData": AnalogData.as_dict(),
            "systemStatus": SystemStatus.as_dict(),
            "bmsProtectionStatus": BmsProtectionStatus.as_dict(),
            "systemProtectionStatus": SystemProtectionStatus.as_dict(),
            "cdd": ChargeDischargeData.as_dict(),
            "inverter": inverterData,
            "batteryPack": CoilData.values,
            "stats": Translator.stats
        }
        return json.dumps(obj)

def do_static(path):
    if path == "/":
        path = "/index.html"

    try:
        with open(os.path.join("web", path[1:]), "r") as f:
            return "".join(f.readlines())
    except:
        return False

def do_toggle(path):
    args = path.split("/")
    arg = args[2]
    if arg == "RebalanceNeeded":
        SystemStatus.rebalance_needed = not SystemStatus.rebalance_needed
        tprint(WebUI.thread_id, 'toggleRebalanceNeeded')
    elif arg == "CancelRebalance":
        SystemStatus.rebalance_cancel = True
        tprint(WebUI.thread_id, 'toggleCancelRebalance')
    elif arg == "FullCharge":
        Translator.toggleBatteryFullCharge()
        tprint(WebUI.thread_id, 'toggleFullCharge')
    elif arg == "BatteryDisable":
        SystemStatus.force_disable = not SystemStatus.force_disable
        tprint(WebUI.thread_id, 'toggleBatteryDisable')
    elif arg == "SetUpperLimit":
        try:
            Translator.setBatteryUpperLimit(int(args[3]))
        except:
            pass
    elif arg == "SetChargingPriority":
        VevorInverter.instance.setChargingPriority(int(args[3]))
    return do_redirect("/")

class Server(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            api = False
            if self.path.startswith("/toggle/"):
                out = do_toggle(self.path)
            elif self.path.startswith("/api/"):
                api = True
                out = do_api(self.path)
            else:
                out = do_static(self.path)

            if out:
                self.send_response(200)
                if api:
                    self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(out.encode())
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            tprint(WebUI.thread_id, str(e))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, format, *args):
        tprint(WebUI.thread_id, "%s - - [%s] %s\n" % (self.address_string(),self.log_date_time_string(),format%args))


class WebUI():
    thread_id = 0

    def __init__(self, thread_id):
        WebUI.thread_id = thread_id

    def task(self):
        sleep(3) # allow systems to start up

        server = ThreadingHTTPServer(("0.0.0.0", 8080), Server)
        tprint(WebUI.thread_id, 'Starting status server')
        server.serve_forever()
