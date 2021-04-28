#!/usr/bin/python3

import json
import re
import sys
import time
from datetime import datetime

import paho.mqtt.client as mqtt
import serial

SERIALPORT = "/dev/ttyUSB0"
BAUDRATE = 300
BYTESIZE = serial.SEVENBITS
PARITY = serial.PARITY_EVEN
STOPBITS = serial.STOPBITS_ONE
RTSCTS = False
XONXOFF = False
DSRDTR = False
read_timeout = 1
write_timeout = 1

client = None
mqtt_client_name = "LK13BD"
mqtt_host = ""
mqtt_user = ""
mqtt_password = ""
mqtt_client = None
mqtt_topic_state = "lk13bd/state"
mqtt_topic_energy = "lk13bd/energy"
mqtt_sleep = 60

mqtt_last_update = None
mqtt_last_kwh = 0.0

try:
    ser = serial.Serial(SERIALPORT, BAUDRATE, timeout=read_timeout, bytesize=BYTESIZE, parity=PARITY, stopbits=STOPBITS,
                        rtscts=RTSCTS,
                        xonxoff=XONXOFF, dsrdtr=DSRDTR, write_timeout=write_timeout)
    print(ser)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
except Exception as e:
    print(e)
    sys.exit(-1)
    close_tty()


def mqtt_connect():
    global mqtt_client
    try:
        mqtt_client = mqtt.Client(mqtt_client_name, clean_session=True, userdata=None, protocol=mqtt.MQTTv311,
                                  transport="tcp")
        mqtt_client.username_pw_set(mqtt_user, mqtt_password)
        mqtt_client.connect(mqtt_host, port=1883, keepalive=(mqtt_sleep * 2))
        print("# MQTT connected: ", mqtt_client)
    except Exception as e:
        print(e)
        sys.exit(-1)


def read_lines():
    global ser
    lines = []
    while True:
        try:
            time.sleep(0.1)
            line = ser.readline().decode('ascii')
            if len(line) != 0:
                print(">", line)
                lines.append(line)
            else:
                break

        except:
            pass
    # print(lines)
    return lines


def send_line(cmd=""):
    global ser
    # print("send", cmd.encode('ascii'))
    ser.write(str(cmd).encode())
    time.sleep(1)


def close_tty():
    global ser
    print("closed:", ser.closed)
    if not ser.closed:
        ser.close()


def get_kwh(lines):
    m = re.compile("(1.8.0)\(([0-9]{6}.[0-9]{3})\*(.*)")
    kwh = 0.0
    for line in lines:
        g = m.search(line)
        if g:
            kwh = float(g.group(2))
            print("#", kwh, "kwh")
            return kwh
    print("ERROR can't find kwh in", lines)
    return None


def get_average_watt(now, kwh, last_update, last_kwh):
    if last_update is None:
        return 0.0
    d = (kwh - last_kwh) * 1000  # Wh
    td = now - last_update
    ws = (d / td.total_seconds())
    w = ws * 3600
    print("#", kwh, "kwh", w, "W", td.total_seconds(), "s")
    return int(w)


def send_mqtt(kwh, now):
    global mqtt_last_update
    global mqtt_last_kwh

    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
    print("#", timestamp)

    state = {}
    energy = {}
    state['Time'] = timestamp
    state['Sleep'] = mqtt_sleep
    energy['Time'] = timestamp
    energy['Total'] = kwh
    energy['Current'] = get_average_watt(now, kwh, mqtt_last_update, mqtt_last_kwh)
    mqtt_last_update = now
    mqtt_last_kwh = kwh

    mqtt_client.publish(mqtt_topic_state, payload=json.dumps(state))
    mqtt_client.publish(mqtt_topic_state, payload=json.dumps(energy))


if __name__ == "__main__":
    mqtt_connect()

    while True:
        print("# Reading...")
        send_line("\x2F\x3F\x21\x0D\x0A")
        read_lines()
        now = datetime.now()
        send_line("\x06\x30\x30\x30\x0D\x0A")
        payload = read_lines()
        ser.flush()
        if len(payload) < 3:
            print("ERROR reading initial value -> retry")
            continue
        kwh = get_kwh(payload)
        if kwh is not None and kwh > 10000:
            send_mqtt(kwh, now)
        else:
            print("ERROR reading kwh value -> resetting buffer")
            ser.reset_output_buffer()
            ser.reset_input_buffer()
            ser.flushInput()
            ser.flushOutput()
            time.sleep(10)
            continue
        time.sleep(mqtt_sleep)
        print('')

    close_tty()

sys.exit(0)
