import RPi.GPIO as GPIO
from hx711 import HX711
import random
import time
import json
import os
from paho.mqtt import client as mqtt_client

# load MQTT configurations from environment variables
MQTT_BROKER = os.environ.get("MQTT_BROKER", 'localhost')
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "python/checkweight")

# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 1000)}'

def connect_mqtt():
    """
    Connect to the MQTT broker
    """
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print(f"Failed to connect, return code {rc}")

    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
    except:
        print("Failed to connect to MQTT broker")
        return None
    return client

def publish_weight(client, weight):
    """
    Publish the weight to the MQTT topic
    """
    if client:
        data = json.dumps({"weight": weight})
        result = client.publish(MQTT_TOPIC, data)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            print(f"Sent weight {weight} to topic {MQTT_TOPIC}")
        else:
            print(f"Failed to send message to topic {MQTT_TOPIC}")
    else:
        print("MQTT client not connected. Could not publish weight")

try:
    # set up GPIO
    GPIO.setmode(GPIO.BCM)
    hx = HX711(dout_pin=6, pd_sck_pin=5)
    # tare the scale
    if not hx.zero():
        print("Tare successful")
    else:
        print("Tare failed")
    # get the weight
    mqtt_client = connect_mqtt()

    # -----------------------------

    reading = hx.get_raw_data_mean()
    if reading:  # always check if you get correct value or only False
        # now the value is close to 0
        print('Data subtracted by offset but still not converted to units:',
              reading)
    else:
        print('invalid data', reading)

    # In order to calculate the conversion ratio to some units, in my case I want grams,
    # you must have known weight.
    input('Put known weight on the scale and then press Enter')
    reading = hx.get_data_mean()
    if reading:
        print('Mean value from HX711 subtracted by offset:', reading)
        known_weight_grams = input(
            'Write how many grams it was and press Enter: ')
        try:
            value = float(known_weight_grams)
            print(value, 'grams')
        except ValueError:
            print('Expected integer or float and I have got:',
                  known_weight_grams)

        # set scale ratio for particular channel and gain which is
        # used to calculate the conversion to units. Required argument is only
        # scale ratio. Without arguments 'channel' and 'gain_A' it sets
        # the ratio for current channel and gain.
        ratio = reading / value  # calculate the ratio for channel A and gain 128
        hx.set_scale_ratio(ratio)  # set ratio for current channel
        print('Ratio is set.')
    else:
        raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading:', reading)



    # -----------------------------


    while True:
        weight = hx.get_weight_mean(20)
        if weight:
            print(f"Weight: {weight}")
            # connect to MQTT broker
            # publish the weight
            publish_weight(mqtt_client, weight)
        else:
            print("Invalid weight")

except (KeyboardInterrupt, SystemExit):
    print("Cleaning up")
    hx.power_down()
    hx.power_up()
    GPIO.cleanup()