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

def subscribe(client: mqtt_client):
    client.subscribe(MQTT_TOPIC)
    def on_message(client, userdata, msg):
        # print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        payload = json.loads(msg.payload.decode())
        if 'knownWeight' in payload:
            global known_weight_grams
            known_weight_grams = payload['knownWeight']
            print("knownWeight", known_weight_grams)

        if 'maxWeight' in payload:
            global maxWeight
            maxWeight = payload['maxWeight']
            print("maxWeight", maxWeight)

        elif 'weight' in payload:
            global weight
        else:
            print("Invalid data")

    client.on_message = on_message


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

    input('Put known weight on the scale and then press Enter')
    reading = hx.get_data_mean()
    if reading:
        print('Mean value from HX711 subtracted by offset:', reading)
        known_weight_grams = None
        maxWeight = None


        mqtt_client.loop_start()
        subscribe(mqtt_client)

        # Wait for known_weight_grams to be set before continuing
        while known_weight_grams is None:
            time.sleep(0.1)

        print('Enter maxWeight')
        while maxWeight is None:
            time.sleep(0.1)

        try:
            value = float(known_weight_grams)
            print(value, 'grams')
            maxWeight = float(maxWeight)
            mqtt_client.loop_stop()
        except ValueError:
            print('Expected integer or float and I have got:', known_weight_grams)

        ratio = reading / value
        hx.set_scale_ratio(ratio)
        print('Ratio is set.')

    else:
        raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading:', reading)


    while True:
        # subscribe(mqtt_client)
        mqtt_client.loop_start()
        weight = hx.get_weight_mean(20)

        if weight > maxWeight:
            print(f"Weight: {weight}")
            # connect to MQTT broker
            # publish the weight
            publish_weight(mqtt_client, weight)
        # else:
        #     print("Invalid weight")


except (KeyboardInterrupt, SystemExit):
    print("Cleaning up")
    mqtt_client.loop_stop()
    hx.power_down()
    hx.power_up()
    GPIO.cleanup()
