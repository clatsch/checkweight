import RPi.GPIO as GPIO
from hx711 import HX711
import random
import time
from time import sleep
import json
import os
from paho.mqtt import client as mqtt_client

# load MQTT configurations from environment variables
MQTT_BROKER = os.environ.get("MQTT_BROKER", 'localhost')
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "checkweight")

# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 1000)}'

def connect_mqtt():
    """
    Connect to the MQTT broker
    """
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            # publish_message(mqtt_client, 'Connected to MQTT Broker!')
            print("connected")
        else:
            publish_message(mqtt_client, 'Failed to connect!')
            print(f"Failed to connect, return code {rc}")

    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
    except:
        publish_message(mqtt_client, 'Failed to connect to MQTT broker!')
        print("Failed to connect to MQTT broker")
        return None
    return client

def publish_weight(client, weight):
    if client:
        data = json.dumps({"ATTENTION, you exceeded the maximum weight! Current weight ": weight})
        client.publish(MQTT_TOPIC, data)
    else:
        print("MQTT client not connected. Could not publish weight")

def publish_message(client, msg):
    if client:
        data = json.dumps(msg)
        client.publish(MQTT_TOPIC, data)
    else:
        print("MQTT client not connected. Could not publish weight")


def subscribe(client: mqtt_client):
    client.subscribe(MQTT_TOPIC)
    print('subscribed')
    def on_message(client, userdata, msg):
        # print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        payload = json.loads(msg.payload.decode())
        if 'knownWeight' in payload:
            global knownWeight
            knownWeight = payload['knownWeight']
            print("Known weight set to:", knownWeight)

        if 'maxWeight' in payload:
            global maxWeight
            maxWeight = payload['maxWeight']
            maxWeight = float(maxWeight)
            print("Maximum weight set to:", maxWeight)

        elif 'weight' in payload:
            global weight


    client.on_message = on_message
    client.loop_start()


try:
    # set up GPIO
    print("starting...")
    GPIO.setmode(GPIO.BCM)
    hx = HX711(dout_pin=6, pd_sck_pin=5)
    buzzer = 23
    GPIO.setup(buzzer,GPIO.OUT)
    # tare the scale
    if not hx.zero():
        print("Tare successful")
    else:
        print("Tare failed")
    # get the weight
    mqtt_client = connect_mqtt()


    reading = hx.get_raw_data_mean()
    if reading:  # always check if you get correct value or only False
            # now the value is close to 0
        publish_message(mqtt_client, 'Data subtracted by offset but still not converted to units yet.')
        # print('Data subtracted by offset but still not converted to units:',
        #       reading)
    else:
        print('invalid data', reading)

    subscribe(mqtt_client)
    # mqtt_client.loop_start()

    publish_message(mqtt_client, 'Put known weight on the scale and enter the weight in grams. Finally submit it with SET KNOWN WEIGHT. Do not remove the object until told so.')
    knownWeight = None
    # input('Put known weight on the scale and then press Enter')
    while knownWeight is None:
        time.sleep(0.1)
    reading = hx.get_data_mean()

    if reading:
        # print('Mean value from HX711 subtracted by offset:', reading)

        maxWeight = None

        # Wait for known_weight_grams to be set before continuing

        # print('Enter maxWeight')
        publish_message(mqtt_client, 'Enter the maximum weight in grams and submit it with SET MAX WEIGHT.')
        # print('Enter max weight')
        while maxWeight is None:
            time.sleep(0.1)

        try:
            value = float(knownWeight)
            maxWeight = int(maxWeight)
            print(value, 'grams')

        except ValueError:
            print('Expected integer or float and I have got: ', knownWeight)

        ratio = reading / value
        hx.set_scale_ratio(ratio)
        print('Ratio is set.')
        mqtt_client.loop_stop()
        publish_message(mqtt_client, 'Ratio is set. You can remove the known weight.')

    else:
        raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading: ', reading)


    while True:
        # subscribe(mqtt_client)
        # mqtt_client.loop_start()
        weight = hx.get_weight_mean(20)
        weightRounded = round(weight/10)*10
        if weightRounded < 0:
            weightRounded = 0
            print(weightRounded)
        else:
            print(weightRounded)

        if weightRounded > maxWeight:
            print(weightRounded)
            GPIO.output(buzzer,GPIO.HIGH)
            sleep(0.4) # Delay in seconds
            GPIO.output(buzzer,GPIO.LOW)
            publish_weight(mqtt_client, weightRounded)
        # else:
        #     print("Invalid weight")


except (KeyboardInterrupt, SystemExit):
    print("Cleaning up")
    publish_message(mqtt_client, 'Bye...')
    knownWeight = None
    maxWeight = None
    mqtt_client.loop_stop()
    hx.power_down()
    hx.power_up()
    GPIO.cleanup()
