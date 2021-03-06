import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, jsonify, Request
from flask_socketio import SocketIO, emit, send
from wireless import Wireless
from picamera import PiCamera
from time import sleep
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import BaseJobStore
from apscheduler.triggers.interval import IntervalTrigger
import picamera
import Outlets
import usbtemper
import socket
import os
import time
import datetime

#def create_app():
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app)
#    return app

#create some globals for wireless stuff and outlet to pass outletname
wiredin = Wireless()
global jinjavar
global outlet
global temp
global hum

temp = usbtemper.findtemp()
hum = usbtemper.findhum()

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

def do_nothing():
    return null

#All the crazy ways I have to derive the name of the outles from the json
def oselect(num):
    if num == 1: return outlet1
    elif num == 2: return outlet2
    elif num == 3: return outlet3
    elif num == 4: return outlet4
    elif num == 5: return led


#The spiffies make sure each completed job is replaced with the next
def spiffyon(outy):
    outy.on()
    socketio.emit(str(outy.num) + 'switch', outy.phrase())
    if outy.url == "/feeding":
        if led.name == "NONE":
            outy.feeding()
            jobomatic(outy)
        else:
            outy.feeding(led.t_on, led.t_off)
            jobomatic(outy)            
    print ("spiffy on activated! " + str(outy.num) + 'switch')
    print (outy.num)
    print (datetime.datetime.now())
    print (outy.check)

def spiffyoff(outy):
    outy.off()
    socketio.emit(str(outy.num) + 'switch', outy.phrase())
    if outy.url == "/feeding":
        if led.name == "NONE":
            outy.feeding()
            jobomatic(outy)
        else:
            outy.feeding(led.t_on, led.t_off)
            jobomatic(outy)
    print ("spiffy off activated! " + str(outy.num) + 'switch')
    print (outy.num)
    print (datetime.datetime.now())
    print (outy.check)

#Check humidity and temperature and update necessary outlets
def checker():
    global temp
    global hum
    temp = usbtemper.findtemp()
    hum = usbtemper.findhum()
    socketio.emit('temp', str(temp))
    socketio.emit('hum', str(hum))
    for x in range(1,6):
        mustard = oselect(x)
        mustard.update(temp,hum,led.check())
        socketio.emit(str(mustard.num)+'switch', mustard.phrase())

#Use the camera!
def camerago():
    timenow = datetime.datetime.now()
    camera=PiCamera()
    camera.start_preview()
    time.sleep(3)
    camera.capture('/home/honky/server/static/pics/garden' + str(timenow.minute) + '.jpg')
    camera.stop_preview()
    camera.close()

#Set up outlet objects
led = Outlets.Outlet(29,"secondary",5)
outlet1 = Outlets.Outlet(37, "danger",1)
outlet2 = Outlets.Outlet(35, "success",2)
outlet3 = Outlets.Outlet(33, "info",3)
outlet4 = Outlets.Outlet(31, "warning",4)

#create dictionary to save from rewriting every variable for jinja
jinjavar = dict(wificon=ifwifi(), webadr=wlan())


@app.route('/wireless') #Log on to Wireless!
def wireless():
    name = request.args.get('name', 0, type=str)
    password = request.args.get('password', 0, type=str)
    if wiredin.connect(ssid=name, password=password):wificon="wifi"
    else:wificon="wifi_off"
    return jsonify(result=wificon)

@app.route('/website') #Pause to return wifi web address
def website():
    global jinjavar
    if wiredin.current():time.sleep(6)
    jinjavar = dict(wificon=ifwifi(), webadr=wlan())
    return jsonify(result=wlan())

@app.route('/')
def index():
    global wificon
    if wiredin.current()!=None:wificon = "wifi"
    else:wificon="wifi_off"
    temp = usbtemper.findtemp()
    hum = usbtemper.findhum()
    return render_template('index.html', led = led, outlet1 = outlet1, outlet2 = outlet2, outlet3 = outlet3, outlet4 = outlet4, temp = temp, hum = hum, **jinjavar)

@app.route('/garden')
def garden():
    #camera stuff, we'll fix later!
    temp = usbtemper.findtemp()
    hum = usbtemper.findhum()
    return render_template('garden.html', temp = temp, hum = hum, **jinjavar) 

#---------Routes for the specific outlets-----------------------------------
@app.route('/sun')
def sun():
    global outlet
    outlet = led
    return render_template('sun.html', outlet = led, **jinjavar)

@app.route('/plug1')
def plug1():
    global outlet
    outlet = outlet1
    return render_template('outlet.html', outlet = outlet1, **jinjavar)

@app.route('/plug2')
def plug2():
    global outlet
    outlet = outlet2
    return render_template('outlet.html', outlet = outlet2, **jinjavar)

@app.route('/plug3')
def plug3():
    global outlet
    outlet = outlet3
    return render_template('outlet.html', outlet = outlet3, **jinjavar)

@app.route('/plug4')
def plug4():
    global outlet
    outlet = outlet4
    return render_template('outlet.html', outlet = outlet4, **jinjavar)


#-----------------All the template routes------------------------------
@app.route('/daynight')
def daynight():
    global outlet
    return render_template('day_night.html', outlet = outlet, **jinjavar)

@app.route('/basic')
def basic():
    return render_template('basic_light.html', outlet=outlet)

#Seasonal and updates.
@app.route('/seasonal')
def seasonal():
    return render_template('seasonal_light.html', outlet = outlet)

#Climate and updates and various templates
@app.route('/climate')
def climate():
    global outlet
    return render_template('climate_control.html', outlet = outlet)

@app.route('/climateupdate')
def climateupdate():
    global outlet
    # specific outlet variables
    if request.args.get('day_t', 0, type=str):
        outlet.day_t = request.args.get('day_t', 0, type=str)
    if request.args.get('night_t', 0, type=str):
        outlet.night_t = request.args.get('night_t', 0, type=str)
    if request.args.get('c_style', 0, type=str):
        outlet.c_style = request.args.get('c_style', 0, type=str)
    # universal outlet variables
    if request.args.get('d_t_high', 0, type=str):
        Outlets.Outlet.d_t_high = request.args.get('d_t_high', 0, type=int)
    if request.args.get('d_t_low', 0, type=str):
        Outlets.Outlet.d_t_low = request.args.get('d_t_low', 0, type=int)
    if request.args.get('n_t_high', 0, type=str):
        Outlets.Outlet.n_t_high = request.args.get('n_t_high', 0, type=int)
    if request.args.get('n_t_low', 0, type=str):
        Outlets.Outlet.n_t_low = request.args.get('n_t_low', 0, type=int)
    if request.args.get('h_high', 0, type=str):
        Outlets.Outlet.h_high = request.args.get('h_high', 0, type=int)
    if request.args.get('h_low', 0, type=str):
        Outlets.Outlet.h_low = request.args.get('h_low', 0, type=int)
    return ('',204)

@app.route('/ac')
def ac():
    global outlet
    return render_template('ac.html', outlet = outlet)

@app.route('/heater')
def heater():
    global outlet
    return render_template('heater.html', outlet = outlet)

@app.route('/humidifier')
def humidifier():
    global outlet
    return render_template('humidifier.html', outlet = outlet)

@app.route('/deHumidifier')
def deHumidifier():
    global outlet
    return render_template('deHumidifier.html', outlet = outlet)

#Feeding and updates
@app.route('/feeding')
def feeding():
    return render_template('feeding_schedule.html',led = led, outlet = outlet)

#Return empty template and erase jobs
@app.route('/none')
def none():
    return ('',204)

#-------------Here's all the socket.io stuff -------------------------

@socketio.on('connected')
def handleMessage(msg):
    print ("connected to " + msg)

@socketio.on('toggle')
def handle_toggle(num):
    bozo = oselect(num)
    bozo.toggle()
    emit(str(num) + 'switch', bozo.phrase(), broadcast=True)

@socketio.on('outlet_template')
def handle_outlet_template(msg,num):
    global outlet
    outlet = oselect(num)
    bozo = outlet
    if msg == "/none":
        bozo.none()
        jobkiller(bozo)
    else:
        if msg == "/daynight":bozo.daynight()
        if msg == "/basic":bozo.basic()
        if msg == "/seasonal":bozo.seasonal()
        if msg == "/climate":bozo.climate()
        if msg == "/feeding":bozo.feeding()
        jobomatic(bozo)
    emit(str(num) + 'outlet_template', msg, broadcast=True)
    emit(str(num) + 'outlet_name', bozo.name, broadcast=True)
    emit(str(num) + 'outlet_button', bozo.type, broadcast=True)

@socketio.on('climate_u')
def handle_climate_u(msg,style,num):
    bozo = oselect(num)
    if style == "aday":bozo.aday = int(msg)
    if style == "aday2":bozo.aday2 = int(msg)
    if style == "day_t":bozo.day_t = msg
    if led.name!="NONE" and bozo.day_t=="checked":
        outlet.feeding(led.t_on, led.t_off)
    else:
        outlet.feeding()
    feedon = bozo.feed_on_str
    jobomatic(bozo)
    if style!="None":emit(str(outlet.num) + style, msg, broadcast=True)
    emit(str(outlet.num) + 'feedon', feedon, broadcast=True)
    print (str(bozo.num) + str(bozo.day_t))

@socketio.on('t_on')
def handle_t_on(msg,num):
    bozo = oselect(num)
    bozo.t_on = Outlets.formater(msg)
    bozo.timeon = msg
    jobomatic(bozo)
    emit(str(outlet.num) + 't_on', msg, broadcast=True)

@socketio.on('t_off')
def handle_t_off(msg,num):
    bozo = oselect(num)
    bozo.t_off = Outlets.formater(msg)
    bozo.timeoff = msg
    jobomatic(bozo)
    emit(str(outlet.num) + 't_off', msg, broadcast=True)

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.start()


    #Set up methods to start jobs, kill them, and create dummy jobs
    def jobkiller(buggo):
        scheduler.remove_job(str(buggo.num)+'on')
        scheduler.remove_job(str(buggo.num)+'off')
        scheduler.add_job(do_nothing, 'cron',hour=20,id=str(buggo.num)+'off')
        scheduler.add_job(do_nothing, 'cron',hour=20,id=str(buggo.num)+'on')

    def jobomatic(buggo):
        #Use buggo to pass outlet instance instead of the ever changing global outlet
        scheduler.remove_job(str(outlet.num)+'on')
        scheduler.remove_job(str(outlet.num)+'off')
        scheduler.add_job(lambda: spiffyon(buggo), 'cron'
                          ,hour=outlet.t_on.hour
                          ,minute=outlet.t_on.minute
                          ,id=str(outlet.num)+'on')
        scheduler.add_job(lambda: spiffyoff(buggo), 'cron'
                          ,hour=outlet.t_off.hour
                          ,minute=outlet.t_off.minute
                          ,id=str(outlet.num)+'off')
    def jobdummystart():
        for x in range(1,6):
            scheduler.add_job(do_nothing, 'cron'
                          ,hour=20
                          ,id=str(x)+'off')
            scheduler.add_job(do_nothing, 'cron'
                          ,hour=8
                          ,id=str(x)+'on')
    #Set up dummy jobs so it doesn't complain
    #Set up interval based jobs
    jobdummystart()
    scheduler.add_job(checker,'interval', minutes=1)
    scheduler.add_job(camerago, 'cron',hour=12)
    socketio.run(app, debug="False", host='0.0.0.0')


Outlets.cleanup()
