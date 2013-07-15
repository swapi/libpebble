#!/usr/bin/env python

from multiprocessing import Lock
from vlcclient import VLCClient
import pebble as libpebble
import sys
import time

if len(sys.argv) < 2:
    print 'Usage: vlcrc <pebble-id>'
    exit(1)

vlc_host = "localhost"
pebble_id = sys.argv[1]
lightblue = True
pair = False

lock = Lock()

try:
    vlc = VLCClient(vlc_host)
    vlc.connect()
except:
    print("Cannot connect to vlc instance, check whether vlc is running or telnet interface is enabled")
    print("Error: " + str(sys.exc_info()))
    exit(1)

try:
    pebble = libpebble.Pebble(pebble_id, using_lightblue=lightblue, pair_first=pair)
except:
    vlc.disconnect();
    print("Cannot connect to pebble, check whether bluetooth is enabled in here and pebble")
    print("Error: " + str(sys.exc_info()))
    exit(1)

state = "stopped"
up_down_button_mode = 'slider'

def update_metadata():
    global state
    with lock:
        status = vlc.status()
        if len(status.split(')')) > 3:
            movie = status.split(')')[0].split(':')[-1].split('/')[-1]
            volume = status.split(')')[1].split(':')[-1]
            #bug in vlc/vlc-client, not correct status is returned, rely manual status 
            #change in control_vlc() function
            #state = vlc.status().split(')')[2].split(':')[-1].split(' ')[-2]
            if up_down_button_mode == 'slider':
                while True:
                    try:
                        t = time.strftime('%H:%M:%S', time.gmtime(int(vlc.get_time())))
                        break
                    except:
                        pass
                pebble.set_nowplaying_metadata(movie, t, 'VLC ' + state)
            else:
                pebble.set_nowplaying_metadata(movie, 'Volume:' + volume, 'VLC ' + state)
        else:
            state = "stopped"
            pebble.set_nowplaying_metadata("No movie is playing", "", "VLC Player")

last_press = 0
unhandled_press = False

def control_vlc(event, backfire=False):
    global state
    global up_down_button_mode
    global last_press
    global unhandled_press
    with lock:
        if event == "playpause":
            current_press = int(time.time()*1000)
            if (current_press - last_press) < 400 and not backfire:
                unhandled_press = False
                if up_down_button_mode == 'slider':
                    up_down_button_mode = 'volume'
                else:
                    up_down_button_mode = 'slider'
                last_press = 0
            elif backfire:
                unhandled_press = False
                if state == "paused":
                    vlc.play()
                    state = "playing"
                elif state == "playing":
                    vlc.pause()
                    state = "paused"
            else:
                last_press = current_press
                unhandled_press = True
                
        if event == "down":
            if up_down_button_mode == 'slider':
                vlc.fastforward()
            else:
                vlc.volup()
        if event == "up":
            if up_down_button_mode == 'slider':
                vlc.rewind()
            else:
                vlc.voldown()

def vlc_control_handler(endpoint, resp):
    events = {
        "PLAYPAUSE": "playpause",
        "PREVIOUS": "up",
        "NEXT": "down"
    }
    control_vlc(events[resp])
    update_metadata()

state = vlc.status().split(')')[2].split(':')[-1].split(' ')[-2]
update_metadata()
pebble.register_endpoint("MUSIC_CONTROL", vlc_control_handler)

print 'waiting for vlc control events'
try:
    while True:
        if unhandled_press:
            control_vlc('playpause', True)
        update_metadata()
        time.sleep(1)
except:
    vlc.disconnect()
    pebble.disconnect()

