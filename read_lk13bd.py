#!/usr/bin/python3

import serial
import logging
import time
import sys
import paho.mqtt.client as mqtt
import re
from datetime import datetime
import json

EXIT = False
SERIALPORT = ""
BAUDRATE = 300
BYTESIZE = serial.SEVENBITS
PARITY = serial.PARITY_EVEN
STOPBITS = serial.STOPBITS_ONE
RTSCTS = False
XONXOFF = False
DSRDTR = False
LOG_FILE = ""
read_timeout = 1
write_timeout = 1

mqtt_client_name = ""
mqtt_host = ""
mqtt_port = 1883
mqtt_user = ""
mqtt_password = ""
mqtt_topic_state = ""
mqtt_topic_energy = ""
mqtt_sleep = 60

mqtt_last_update = None
mqtt_last_kwh = 0.0

logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s %(message)s')

try:
    with open('read_lk13bd.json', 'r') as f:
        cf = json.load(f)
        SERIALPORT = cf['SERIALPORT']
        LOG_FILE = cf['LOG_FILE']
        mqtt_client_name = cf['mqtt_client_name']
        mqtt_host = cf['mqtt_host']
        mqtt_port = cf['mqtt_port']
        mqtt_user = cf['mqtt_user']
        mqtt_password = cf['mqtt_password']
        mqtt_topic_state = cf['mqtt_topic_state']
        mqtt_topic_energy = cf['mqtt_topic_energy']
        mqtt_sleep = cf['mqtt_sleep']
        logging.debug(str(cf))
except Exception as e:
    logging.error(str(e))
    sys.exit(-1)


try:
    ser = serial.Serial(SERIALPORT, BAUDRATE, timeout=read_timeout, bytesize=BYTESIZE, parity=PARITY, stopbits=STOPBITS,
                        rtscts=RTSCTS,
                        xonxoff=XONXOFF, dsrdtr=DSRDTR, write_timeout=write_timeout)
    logging.debug("serial: " + str(ser))
    ser.reset_input_buffer()
    ser.reset_output_buffer()
except Exception as e:
    logging.error("%s", e)
    sys.exit(-1)


def signal_handler(sig, frame):
    logging.info('You pressed Ctrl+C!')
    global EXIT
    EXIT = True

def mqtt_connect():
    global mqtt_client
    try:
        mqtt_client = mqtt.Client(mqtt_client_name, clean_session=True, userdata=None, protocol=mqtt.MQTTv311,
                                  transport="tcp")
        mqtt_client.username_pw_set(mqtt_user, mqtt_password)
        mqtt_client.connect(mqtt_host, port=mqtt_port, keepalive=(mqtt_sleep * 2))
        logging.info("# MQTT connected: %s", mqtt_host)
    except Exception as e:
        logging.error("%s", e)
        sys.exit(-1)

def mqtt_reconnect():
    global mqtt_client
    try:
        mqtt_client.reconnect()
    except Exception as e:
        logging.error("%s", e)
        sys.exit(-1)


def read_lines():
    global ser
    lines = []
    while True:
        try:
            time.sleep(0.1)
            line = ser.readline().decode('ascii')
            if len(line) != 0:
                logging.debug(">%s",line)
                lines.append(line)
            else:
                break

        except:
            pass    
    return lines


def send_line(cmd=""):
    global ser
    logging.debug("send %s", cmd.encode('ascii') )
    ser.write(str(cmd).encode())
    time.sleep(1)


def close_tty():
    global ser
    logging.info("closed: %s", ser.closed)
    if not ser.closed:
        ser.close()


def get_kwh(lines):
    m = re.compile("(1.8.0)\(([0-9]{6}.[0-9]{3})\*(.*)")
    kwh = 0.0
    for line in lines:
        g = m.search(line)
        if g:
            kwh = float(g.group(2))
            logging.info("# %f kWh", kwh)
            return kwh
    logging.error("cant find kwh in %s", line)
    return None


def get_average_watt(now, kwh, last_update, last_kwh):
    if last_update is None:
        return 0.0
    d = (kwh - last_kwh) * 1000  # Wh
    td = now - last_update
    ws = (d / td.total_seconds())
    w = ws * 3600
    logging.info("# %f kWh %i W %d s",kwh,int(w),td.total_seconds())
    return int(w)


def send_mqtt(kwh, now, payload=None):
    global mqtt_last_update
    global mqtt_last_kwh

    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
    logging.info("# %s", timestamp)

    state = {}
    energy = {}
    state['Time'] = timestamp
    state['Sleep'] = mqtt_sleep
    state['payload'] = str(payload)
    energy['Time'] = timestamp
    energy['Total'] = kwh
    energy['Current'] = get_average_watt(now, kwh, mqtt_last_update, mqtt_last_kwh)
    mqtt_last_update = now
    mqtt_last_kwh = kwh

    mqtt_client.publish(mqtt_topic_state, payload=json.dumps(state))
    mqtt_client.publish(mqtt_topic_energy, payload=json.dumps(energy))


if __name__ == "__main__":
    mqtt_connect()

    while EXIT == False:
        logging.info("# Reading...")
        send_line("\x2F\x3F\x21\x0D\x0A")
        read_lines()
        now = datetime.now()
        send_line("\x06\x30\x30\x30\x0D\x0A")
        payload = read_lines()
        ser.flush()
        if len(payload) < 3:
            logging.warning("reading initial value -> retry")
            continue
        kwh = get_kwh(payload)
        if kwh is not None and kwh > 10000:
            mqtt_reconnect()            
            send_mqtt(kwh, now, payload=payload)
        else:
            logging.warning("reading kwh value -> resetting buffer")
            ser.reset_output_buffer()
            ser.reset_input_buffer()
            ser.flushInput()
            ser.flushOutput()
            time.sleep(10)
            continue
        logging.debug("Sleeping %d", mqtt_sleep)
        time.sleep(mqtt_sleep)

    close_tty()

logging.info("Exit")
sys.exit(0)
