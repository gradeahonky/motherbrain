from flask import Flask, render_template, request, jsonify, Request
from wifi import Cell, Scheme
from picamera import PiCamera
from time import sleep
from datetime import datetime
#from apscheduler.schedulers.background import BackgroundScheduler
import picamera
import Outlets
import socket
import os
import time


#create some globals for wireless stuff
wiredin = Wireless()
global jinjavar


#find wlan0 output link for wireless access
def wlan():
    if wiredin.current()!=None:
        gw = os.popen("ip -4 route show default").read().split()    
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
        s.connect((gw[2], 0))
        ipaddr = s.getsockname()[0]
        return str("url: " + ipaddr + ":5000")
    else:
        return str("None")

#Find the correct wifi icon
def ifwifi():
    if wiredin.current()!=None:
        return str("wifi")
    else:
        return str("wifi_off")


#All the crazy ways I have to derive the name of the outles from the json
def oselect(num):
    if num == 1: return outlet1
    elif num == 2: return outlet2
    elif num == 3: return outlet3
    elif num == 4: return outlet4
    elif num == 5: return led

led = Outlets.Outlet(29,"secondary",5, "LED", None)
outlet1 = Outlets.Outlet(37, "danger",1, "UVB", None)
outlet2 = Outlets.Outlet(35, "success",2, "PUMP", None)
outlet3 = Outlets.Outlet(33, "info",3, "FAN", None)
outlet4 = Outlets.Outlet(31, "warning",4, "OTHER", None)

global outlet

def thing():
    print ("Still going")

#create dictionary to save from rewriting every variable for jinja
jinjavar = dict(wificon=ifwifi(), webadr=wlan())

#def create_app():
app = Flask(__name__)  

#    return app


@app.route('/wireless')
def wireless():
    name = request.args.get('name', 0, type=str)
    password = request.args.get('password', 0, type=str)
    if wiredin.connect(ssid=name, password=password):wificon="wifi"
    else:wificon="wifi_off"
    return jsonify(result=wificon)

@app.route('/website')
def website():
    global jinjavar
    if wiredin.current():time.sleep(4)
    jinjavar = dict(wificon=ifwifi(), webadr=wlan())
    return jsonify(result=wlan())

@app.route('/_set_template')
def _set_template():
    global outlet
    switch = request.args.get('switch', 0, type=int)
    outlet = oselect(switch)
    return jsonify(result=outlet.phrase())

@app.route('/_switch_board')
def _switch_board():
    global outlet
    switch = request.args.get('switch', 0, type=int)
    outlet = oselect(switch)
    outlet.toggle()
    return jsonify(result=outlet.phrase())

    

@app.route('/')
def index():
    global wificon

    if wiredin.current()!=None:wificon = "wifi"
    else:wificon="wifi_off"
    return render_template('index.html', led = led, outlet1 = outlet1, outlet2 = outlet2, outlet3 = outlet3, outlet4 = outlet4, **jinjavar)

@app.route('/garden')
def garden():
    #camera stuff, we'll fix later!
    '''
    camera=picamera.PiCamera()
    try:
        camera.start_preview()
        time.sleep(2)
        camera.capture('/home/honky/server/static/garden.jpg')
        camera.stop_preview()
    finally:
        camera.close()
    '''
    return render_template('garden.html', **jinjavar)

@app.route('/light')
def light():
    return render_template('outlet.html', outlet = led, **jinjavar)

@app.route('/out1')
def out1():
    return render_template('outlet.html', outlet = outlet1, **jinjavar)

@app.route('/out2')
def out2():
    return render_template('outlet.html', outlet = outlet2, **jinjavar)

@app.route('/out3')
def out3():
    return render_template('outlet.html', outlet = outlet3, **jinjavar)

@app.route('/out4')
def out4():
    return render_template('outlet.html', outlet = outlet4, **jinjavar)

@app.route('/basic')
def basic():
    global outlet
    timeon = request.args.get('timeon', 0, type=str)
    timeoff = request.args.get('timeoff', 0, type=str)
    print(timeon)
    print(timeoff)
    return render_template('basic_light.html', outlet = outlet)
@app.route('/seasonal')
def seasonal():
    global outlet
    return render_template('seasonal_light.html', outlet = outlet)

@app.route('/climate')
def climate():
    global outlet
    return render_template('climate_control.html', outlet = outlet)

@app.route('/feeding')
def feeding():
    global outlet
    return render_template('feeding_schedule.html', outlet = outlet)


    
    
if __name__ == '__main__':
    '''
    scheduler = BackgroundScheduler()
    scheduler.add_job(thing, 'interval', seconds=10)
    scheduler.start()
    '''
    app.run(debug = "True", host='0.0.0.0')


Outlets.cleanup()
