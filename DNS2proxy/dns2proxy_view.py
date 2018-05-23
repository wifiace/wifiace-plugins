from flask import Blueprint, render_template, request, url_for, flash, jsonify, redirect

import netifaces
import subprocess as sb
import apt
import os
from yapsy.IPlugin import IPlugin

from core.globals import Global
from core.utils_flask import logged_in
from core.utils import getPID, termKill
from core import DN

DIR_PATH = Global.PLUGINS_DIR + "/DNS2proxy"
BIN_DNS2PROXY = DIR_PATH + "/dns2proxy/dns2proxy.py"

dns2proxy_b = Blueprint("dns2proxy_b",__name__,template_folder="templates")

@dns2proxy_b.route("/")
@logged_in
def show_dns2proxy():
    status = {}
    status["pid"] = getPID(BIN_DNS2PROXY, script=True)

    status["interfaces"] = netifaces.interfaces()
    if "lo" in status["interfaces"]:
        status["interfaces"].remove("lo")

    return render_template("dns2proxy_index.html", status = status)

@dns2proxy_b.route("/start", methods=["GET"])
@logged_in
def start():
    if "iface" not in request.args:
        flash("iface not specified.", "warning")
        return redirect( url_for("dns2proxy_b.show_dns2proxy") )

    if getPID("dns2proxy.py", script=True) != -1:
        flash("dns2proxy already running", "warning")
        return redirect( url_for("dns2proxy_b.show_dns2proxy") )

    iface = str(request.args.get("iface"))

    if iface not in netifaces.interfaces():
        flash("given iface not available", "danger")
        return redirect( url_for("dns2proxy_b.show_dns2proxy") )


    #sb.Popen(["python", BIN_DNS2PROXY, "-i", iface, "-p", DIR_PATH + "/dns2proxy/"], stdout=f)
    sb.Popen("stdbuf -oL nohup python " + BIN_DNS2PROXY + " -i " + iface + " -p " + DIR_PATH + "/dns2proxy/ > " + DIR_PATH + "/dns2proxy/output.log", shell=True)

    flash("Started Dns2proxy successfully.", "success")

    return redirect( url_for("dns2proxy_b.show_dns2proxy") )

@dns2proxy_b.route("/stop")
@logged_in
def stop():

    if getPID(BIN_DNS2PROXY, script=True) == -1:
        flash("dns2proxy not running", "warning")
        return redirect( url_for("dns2proxy_b.show_dns2proxy") )

    termKill(BIN_DNS2PROXY, script=True)

    flash("dns2proxy stoped successfully", "success")
    return redirect( url_for("dns2proxy_b.show_dns2proxy") )


@dns2proxy_b.route("/fetchfiles/<file_name>")
@logged_in
def fetchfiles(file_name):
    FILE_PATH = DIR_PATH + "/dns2proxy/" + file_name
    if os.path.exists( FILE_PATH ):
        with open(FILE_PATH, "r") as fp:
            file_str = fp.read()
            return jsonify(message=file_str)
    else:
        return jsonify(message="file Not Found")

@dns2proxy_b.route("/writefile", methods=["POST"])
@logged_in
def writefile():
    print request.form
    if "file_name" not in request.form or "file_text" not in request.form:
        return jsonify(message="Invailed request parameters."), 400

    FILE_PATH = DIR_PATH + "/dns2proxy/" + request.form["file_name"]
    if os.path.exists( FILE_PATH ):
        with open(FILE_PATH, "w") as fp:
            fp.write(request.form["file_text"])
            fp.flush()

        return jsonify(message="Saved Changes successfully")
    else:
        return jsonify(message="file Not Found"), 400

class Dns2proxyPlugin(IPlugin):

    def getBlueprint(self):
        return dns2proxy_b

    def checkDependencies(self):
        cache = apt.Cache()
        if os.path.isdir(DIR_PATH + "/dns2proxy/"):
            if ("python-pcapy" in cache) and (cache["python-pcapy"].is_installed):
                return True
        return False

    def installDependencies(self):
        sb.call(["git", "clone", "https://github.com/a5hish/dns2proxy", DIR_PATH + "/dns2proxy"])
        sb.call("apt-get install python-pcapy -y", shell=True)


    def activate(self):
        print "DNS2proxy activated"
