# lk13bd-mqtt
MQTT client for a LK13BD three-phase meter. This is my first release. I'm using a OptoHead (https://shop.weidmann-elektronik.de/index.php?page=product&info=24) from Weidmann Elektronik. Running on my raspberry pi.

The script will read the current total power state and calculate the average consumption between two steps. It will publish the current Watt and the total kWh as a MQTT message for further visualisation and storage.

## configure

Configure the following settings
* mqtt_host
* mqtt_user
* mqtt_password

## use systemd to start your script automatically

* Add mqtt-lk13bd.service to */lib/systemd/system/*
```
sudo vi /lib/systemd/system/mqtt-lk13bd.service
```
Add the following:
```
[Unit]
Description=MQTT LK13BD three-phase meter
After=multi-user.target

[Service]
Type=idle
ExecStart=/<path to your script>/read_lk13bd.py > /<path to your script>/read_lk13bd.log 2>&1
User=<user>
Restart=always
WorkingDirectory=/<path to your script>/

[Install]
WantedBy=multi-user.target
```
Prepare systemd and new service.
```
sudo chmod 644 /lib/systemd/system/mqtt-lk13bd.service
sudo systemctl daemon-reload
sudo systemctl enable mqtt-lk13bd.service
sudo service mqtt-lk13bd start
```

## configure your homeassistant 

Add the following lines to */config/configuration.yaml*
```
mqtt:
  sensor:
    - name: "lk13bd.total_energy"
      state_topic: "lk13bd/energy"
      unit_of_measurement: "kWh"
      value_template: "{{ value_json.Total }}"
      json_attributes_topic: "lk13bd/energy"
      json_attributes_template: "{{ value_json.Total | tojson }}"

    - name: "lk13bd.current_energy"
      state_topic: "lk13bd/energy"
      unit_of_measurement: "W"
      value_template: "{{ value_json.Current }}"
      json_attributes_topic: "lk13bd/energy"
      json_attributes_template: "{{ value_json.Current | tojson }}"
```
That's it. You should now receive your data from LK13BD

## monitor service
```
journalctl -u mqtt-lk13bd.service -f
```

## Todo
- [ ] Cleanup code
