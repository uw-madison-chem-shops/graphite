import os
import time
import pathlib
import datetime
from dataclasses import dataclass, field
from typing import List, Dict
import socket


import paho.mqtt.client as mqtt


class Topic(dict):
    def __init__(self):
        super().__init__()
        self["__value__"] = None

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            out = Topic()
            self[key] = out
            return out


homie = Topic()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("homie/#")


def on_message(client, userdata, msg):
    topics = msg.topic.split("/")
    payload = msg.payload.decode()
    # fill topic tree
    here = homie
    for t in topics[1:]:
        here = here[t]
    here["__value__"] = payload
    # tags
    tags = {}
    tags["device_id"] = topics[1]
    # case of device attribute
    device_attributes = [
        "$homie",
        "$name",
        "$state",
        "$nodes",
        "$extensions",
        "$implementation",
    ]
    if len(topics) == 3 and topics[2] in device_attributes:
        measurement = topics[2]
        fields = {"value": payload}
        write_point(measurement, tags, fields)
    # case of device node property
    elif len(topics) == 4:
        measurement = topics[3]
        tags["node"] = topics[2]
        datatype = homie[topics[1]][topics[2]][topics[3]]["$datatype"]["__value__"]
        if datatype == "float":
            fields = {"value": float(payload)}
        else:
            return
        write_point(measurement, tags, fields)


def write_point(measurement, tags, fields):
    if type(fields["value"]) not in [int, float]:
        return
    metric_path = f"{tags['device_id'].replace('-', '.')}.{tags['node']}.{measurement}"
    out = f"{metric_path} {fields['value']} -1\n"
    print(out)
    try:
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect(("graphite", 2003))
        sock.sendall((out).encode())
        sock.close()
    except Exception as e:
        print(e)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("mqtt.chem.wisc.edu", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()

