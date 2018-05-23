from flask import Blueprint, render_template, jsonify, request, flash, send_file, redirect
import subprocess as sb
import apt
import os
import netifaces
from datetime import datetime
from yapsy.IPlugin import IPlugin

from core import DN
from core.utils_flask import logged_in
from core.utils import getPID, termKill
from core.globals import Global

HISTORY_DIR = Global.PLUGINS_DIR + "/Tshark/history"

tshark_b = Blueprint( "tshark_b", __name__, template_folder="templates")

@tshark_b.route("/")
@logged_in
def show_tshark():
    status={}
    # get status of tshark if already running.
    status["pid"] = getPID("tshark")

    status["interfaces"] = netifaces.interfaces()
    if "lo" in status["interfaces"]:
        status["interfaces"].remove("lo")

    # get list of already stored files.
    status["history_list"]=[]
    if os.path.isdir(HISTORY_DIR):
        status["history_list"] = sorted([f for f in os.listdir(HISTORY_DIR) if os.path.isfile(HISTORY_DIR+"/"+f)])[::-1]

    return render_template("tshark_index.html", status=status)

@tshark_b.route("/start_tshark", methods=["GET"])
@logged_in
def start_tshark():

    if "iface" not in request.args:
        return "iface not specified."

    if getPID("tshark") != -1:
        return "tshark already running"

    iface = str(request.args.get("iface"))

    now = datetime.now()
    time_str = "%d-%d-%d" % (now.hour, now.minute, now.second)
    file_name = HISTORY_DIR + "/%s-%s.pcap" % (str(now.date()), time_str)

    sb.Popen(["tshark", "-i", iface, "-w", file_name], stdout=DN, stderr=DN)

    if request.referrer:
        flash("Started Tshark Successfully", "success")
        return redirect(request.referrer)

    return "Started Successfully"


@tshark_b.route("/stop_tshark", methods=["GET"])
@logged_in
def stop_tshark():
    termKill("tshark")
    if request.referrer:
        flash("Stoped tshark", "success")
        return redirect(request.referrer)

    return "Stoped tshark"

@tshark_b.route("/download/<file_name>")
@logged_in
def download_file(file_name):
    download_file = HISTORY_DIR+"/"+file_name

    if not os.path.exists(download_file):
        return "File name : " + file_name + " Doesnt exists."

    return send_file(download_file, attachment_filename=file_name)

@tshark_b.route("/delete/<file_name>")
@logged_in
def delete_file(file_name):
    delete_file = HISTORY_DIR+"/"+file_name

    if not os.path.exists(delete_file):
        return "File name : " + file_name + " Doesnt exists."

    os.remove(delete_file)

    if request.referrer:
        flash("deleted file " + file_name + "Successfully", "success")
        return redirect(request.referrer)

    return  "deleted file " + file_name + "Successfully", "success"


class TsharkPlugin(IPlugin):

    def getBlueprint(self):
        return tshark_b

    def checkDependencies(self):
        cache = apt.Cache()

        if "tshark" in cache:
            return cache["tshark"].is_installed

        return False

    def installDependencies(self):
        sb.call("apt-get install tshark -y", shell=True)


    def activate(self):
        # check if dir exists if not create
        if not os.path.isdir(HISTORY_DIR):
            os.makedirs(HISTORY_DIR)

        print "Tshark Activated : History File Loc : " + HISTORY_DIR
