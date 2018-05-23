from flask import Blueprint, render_template, jsonify
import subprocess as sb
import apt

from yapsy.IPlugin import IPlugin
from core.utils_flask import logged_in

def read_datetime():
    banner_str = sb.Popen("date | figlet", shell=True, stdout=sb.PIPE).stdout.read()
    return banner_str

dtbanner = Blueprint( "dtbanner", __name__, template_folder="templates")

@dtbanner.route("/")
@logged_in
def show_banner():
    return render_template("dtbanner_index.html", banner_str=read_datetime())

@dtbanner.route("/get_datetime")
@logged_in
def get_datetime():
    return jsonify(message=read_datetime())


class HelloPlugin(IPlugin):

    def getBlueprint(self):
        return dtbanner

    def checkDependencies(self):
        cache = apt.Cache()

        if "figlet" in cache:
            return cache["figlet"].is_installed

        return False

    def installDependencies(self):
        sb.call("apt-get install figlet -y", shell=True)


    def activate(self):
        print "Datetime Banner activated"
