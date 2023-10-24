import logging

import paho.mqtt.client as mqtt
import socket
from confluent_kafka import Producer

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Kafka configuration
KAFKA_BROKER = "kafka:9092"
KAKFA_CLIENT_ID = socket.gethostname()
# KAFKA_DATA_TOPIC = "factory-data"
# KAFKA_STATUS_TOPIC = "factory-status"

# MQTT configuration
MQTT_BROKER_HOST = "mosquitto"
MQTT_BROKER_PORT = 1883
MQTT_DATA_TOPIC_PREFIX = "factory/machines"
MQTT_STATUS_TOPIC = "factory/machines/status"

logging.info(
    f"Connecting to Kafka Broker {KAFKA_BROKER} with client.id {KAKFA_CLIENT_ID}..."
)
conf = {"bootstrap.servers": KAFKA_BROKER, "client.id": KAKFA_CLIENT_ID}
producer = Producer(conf)


def on_connect(client, userdata, flags, rc):
    logging.info(
        f"Connected to MQTT broker. Subscribing to topics: {MQTT_DATA_TOPIC_PREFIX}/M0x/data, {MQTT_STATUS_TOPIC}"
    )
    client.subscribe(
        [
            (MQTT_STATUS_TOPIC, 0),
            (f"{MQTT_DATA_TOPIC_PREFIX}/M01/data", 0),
            (f"{MQTT_DATA_TOPIC_PREFIX}/M02/data", 0),
            (f"{MQTT_DATA_TOPIC_PREFIX}/M03/data", 0),
        ]
    )


def on_message(client, userdata, message):
    # Determine Kafka topic based on the incoming MQTT topic
    if "status" in message.topic:
        kafka_topic = f"factory_machine_status"
    else:
        machine_name = message.topic.split("/")[2]
        kafka_topic = f"factory_machine_{machine_name}_data"

    # Send the MQTT message to Kafka
    producer.produce(kafka_topic, message.payload)
    producer.flush()  # Ensure that the message gets sent


if __name__ == "__main__":
    logging.info("Starting MQTT to Kafka connector...")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)

    # Block and process MQTT messages
    client.loop_forever()
