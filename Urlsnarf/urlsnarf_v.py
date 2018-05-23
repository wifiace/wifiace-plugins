from flask import Blueprint, render_template, jsonify, request, flash, send_file, redirect
import apt
from yapsy.IPlugin import IPlugin
from os.path import isdir,isfile
from os import makedirs,listdir,remove
import netifaces
import subprocess as sb
from datetime import datetime


from core.utils_flask import logged_in
from core.utils import getPID, termKill
from core.globals import Global

urlsnarf_b = Blueprint("urlsnarf_b",__name__,template_folder="templates")

LOGDIR = Global.PLUGINS_DIR + "/Urlsnarf/logs"

@urlsnarf_b.route("/")
@logged_in
def show_snarf():
    status = {}
    status["pid"] = getPID("urlsnarf")
    status["interfaces"] = netifaces.interfaces()
    if "lo" in status["interfaces"]:
        status["interfaces"].remove("lo")

    status["logs"]=[]
    if isdir(LOGDIR):
        status["logs"]= sorted([file_ for file_ in listdir(LOGDIR) if file_.endswith(".log")])[::-1]

	return render_template("urlsnarf.html",status=status)

@urlsnarf_b.route("/stop_urlsnarf",methods=["GET"])
@logged_in
def stop_snarf():
    termKill("urlsnarf")
    if request.referrer:
        flash("Stoped urlsnarf", "success")
        return redirect(request.referrer)

    return "Stoped urlsnarf"

@urlsnarf_b.route("/start_urlsnarf",methods=["GET"])
@logged_in
def start_snarf():
    if getPID("urlsnarf")!=-1:
        return "URLsnarf is already running"

    if "iface" not in request.args:
        return "Interface not specified"

    iface = str(request.args.get("iface"))

    if iface not in netifaces.interfaces():
        flash("Invalid interface", "warning")
        return redirect(request.referrer)
    now = datetime.now()
    time_str = "%d:%d:%d@%d-%s-%d.log" % (now.hour, now.minute, now.second,now.day,now.strftime("%B"),now.year)

    sb.Popen("stdbuf -oL nohup urlsnarf -i"+iface+" > "+LOGDIR+"/"+time_str,shell=True)

    return redirect(request.referrer)

@urlsnarf_b.route("/download/<file_name>")
@logged_in
def download_file(file_name):
    download_file = LOGDIR+"/"+file_name

    if not isfile(download_file):
        return "File name : " + file_name + " Doesnt exists."

    return send_file(download_file, attachment_filename=file_name)

@urlsnarf_b.route("/delete/<file_name>")
@logged_in
def delete_file(file_name):
    delete_file = LOGDIR+"/"+file_name

    if not isfile(delete_file):
        return "File name : " + file_name + " Doesnt exists."

    remove(delete_file)

    if request.referrer:
        flash("deleted file " + file_name + "Successfully", "success")
        return redirect(request.referrer)

    return  "deleted file " + file_name + "Successfully", "success"

class UrlsnarfPlugin(IPlugin):

    def getBlueprint(self):
        return urlsnarf_b

    def checkDependencies(self):
        cache = apt.Cache()

        if "dsniff" in cache:
            return cache["dsniff"].is_installed

        return False

    def installDependencies(self):
        sb.call("apt-get install dsniff -y", shell=True)


    def activate(self):
        # check if dir exists if not create
        if not isdir(LOGDIR):
            makedirs(LOGDIR)

        print "Urlsnarf activated logs stored at  : " + LOGDIR
