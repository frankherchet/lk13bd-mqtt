# lk13bd-mqtt
MQTT client for a LK13BD three-phase meter

## configure

Configure the following settings
* mqtt_host
* mqtt_user
* mqtt_password

## use systemd to start your script automatically

* Add and modify mqtt-lk13bd.service to */lib/systemd/system/*
```
sudo chmod 644 /lib/systemd/system/mqtt-lk13bd.service
sudo systemctl daemon-reload
sudo systemctl enable mqtt-lk13bd.service
sudo service mqtt-lk13bd start
```

## configure your homeassistant 

Add the following lines to */config/configuration.yaml*
```
sensor:
  - platform: mqtt
    state_topic: "lk13bd/energy"
    name: "Total"
    unit_of_measurement: "kWh"
    value_template: "{{ value_json.Total }}"
    json_attributes_topic: "lk13bd/energy"
    json_attributes_template: "{{ value_json.Total | tojson }}"
  - platform: mqtt
    state_topic: "lk13bd/energy"
    name: "Current"
    unit_of_measurement: "W"
    value_template: "{{ value_json.Current }}"
    json_attributes_topic: "lk13bd/energy"
    json_attributes_template: "{{ value_json.Current | tojson }}"
```
