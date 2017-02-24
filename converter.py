#!/usr/bin/env python
from gcoder import *
import sys
import uuid
import os
import json
import shutil
from subprocess import call

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

def gen_json_cmd(func, parameter, metadata=dict(), tags=[]):
    return {
        "command": {
            "function": func,
            "parameters": parameter,
            "metadata": metadata,
            "tags": tags
        }
    }


def gen_set_temp(temp):
    return gen_json_cmd("set_toolhead_temperature", {
        "temperature": temp
    })


def gen_fan_duty(value):
    return gen_json_cmd("fan_duty", {"value": value})


def gen_toggle_fan(val):
    return gen_json_cmd("toggle_fan", {"value": val})


def gen_move(x, y, z, a, f):
    return gen_json_cmd("move", {
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "a": float(a),
        "feedrate": f,
    },
                        {"relative": {"x": False, "y": False, "z": False, "a": False}
                         })


class Dotmakerbot:
    def __init__(self, data):
        print "Init Dotmakerbot"
        self.cmd_count = 0
        self.gcode = GCode(data)
        self.meta = dict()
        self.jsontoolpath = []
        self.fan = 0.5

        self.temp = 230
        self.preprocesser()
        self.init_meta()

    def init_meta(self):
        meta = self.meta
        meta["uuid"] = uuid.uuid1().__str__()
        # TODO:Parse Time
        meta["toolhead_0_temperature"] = self.temp
        meta["toolhead_1_temperature"] = self.temp
        meta["total_commands"] = self.jsontoolpath.__len__()
        printer_settings = {
            "default_raft_extruder": 0,
            "slicer": "CURA",
            "platform_temperature": 0,
            "shells": 1,
            "default_support_extruder": 0,
            "support": False,
            "layer_height": 0.3,
            "travel_speed": 150,
            "extruder_temperatures": [
                230,
                230
            ],
            "materials": [
                "PLA",
                "PLA"
            ],
            "infill": 0.03,
            "heat_platform": False,
            "raft": True,
            "do_auto_support": False,
            "path": None,
            "print_speed": 90,
            "do_auto_raft": False,
            "extruder": "0"
        }
        meta["printer_settings"] = printer_settings
        meta["extrusion_mass_a_grams"] = int(self.gcode.filament_length* 2.4e-9 * 1250000)
        meta["extrusion_mass_b_grams"] =  0.0
        meta["extrusion_distance_a_mm"] = int(self.gcode.filament_length)
        meta["extrusion_distance_b_mm"] = 0.0
        meta["duration_s"] = self.gcode.duration.total_seconds()
        print "Model Mass {0} grams time {1}".format(
            meta["extrusion_mass_a_grams"],
            meta["duration_s"]

        )
        return

    def preprocesser(self):
        cmds = self.jsontoolpath
        cmds.append(gen_set_temp(self.temp))
        cmds.append(gen_fan_duty(self.fan))
        cmds.append(gen_toggle_fan(True))
        feedspeed = 0
        x = 0
        y = 0
        z = 0
        e = 0
        f = 0
        for line in self.gcode.lines:
            if line.command:
                if line.is_move:
                    if line.x != None:
                        x = line.x
                    if line.y != None:
                        y = line.y
                    if line.z != None:
                        z = line.z
                    if line.e != None:
                        e = line.e
                    if line.f != None:
                        f = line.f
                    cmds.append(gen_move(x, y, z, e, f/60))
                else:
                    #print line.command
                    pass
        cmds.append(gen_toggle_fan(False))
        # print self.cmds
        return


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: %s filename.gcode" % sys.argv[0])
        exit(0)
    source_path = sys.argv[1]
    dotmatkerbot = Dotmakerbot(open(sys.argv[1], "rU"))
    base = os.path.basename(sys.argv[1])
    name = os.path.splitext(base)[0]
    root_path = "tmp/" \
                "{0}_gcode".format(name)
    try:
        os.mkdir(root_path)
    except:
        print 'Dir exist, overwriting'

    #try:
    #    shutil.copy2("./templates/imgs/thumbnail_55x40.png", root_path+"/")
    #    shutil.copy2("./templates/imgs/thumbnail_110x80.png", root_path + "/")
    #    shutil.copy2("./templates/imgs/thumbnail_320x200.png", root_path+"/")
    #except:
    #    print "Copy Failed"

    f_meta = open(root_path+"/meta.json","w")
    f_meta.write(json.dumps(dotmatkerbot.meta,indent=4))
    f_meta.close()
    f_jsontoolpath = open(root_path+"/print.jsontoolpath","w")
    f_jsontoolpath.write(json.dumps(dotmatkerbot.jsontoolpath,indent=4))
    f_jsontoolpath.close()
    #shutil.make_archive("dst/{0}_gcode".format(name),'zip',root_path)
    #shutil.copyfile("dst/{0}_gcode.zip".format(name),"dst/{0}_gcode.makerbot".format(name))
    call(["/Library/MakerBot/dot_makerbot_writer",
          "dst/{0}_gcode.makerbot".format(name),
          root_path + "/print.jsontoolpath",
          root_path + "/meta.json",
         "./templates/imgs/"
          ])