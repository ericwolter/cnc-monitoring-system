import logging
import socket
from confluent_kafka import Producer, KafkaException
import paho.mqtt.client as mqtt

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Constants
KAFKA_BROKER = "kafka:9092"
KAFKA_CLIENT_ID = socket.gethostname()
MQTT_BROKER_HOST = "mosquitto"
MQTT_BROKER_PORT = 1883
MQTT_DATA_TOPIC_PREFIX = "factory/machines"
MQTT_STATUS_TOPIC = "factory/machines/status"


def configure_kafka():
    logging.info("Initializing Kafka configuration...")
    conf = {"bootstrap.servers": KAFKA_BROKER, "client.id": KAFKA_CLIENT_ID}
    logging.info("Kafka configuration initialized.")
    return Producer(conf)


def on_connect(client, userdata, flags, rc):
    if rc != 0:
        logging.error(f"Failed to connect to MQTT broker. Return code: {rc}")
        raise SystemExit(f"Fatal error: MQTT connection failed with return code {rc}")

    topics = [
        (MQTT_STATUS_TOPIC, 0),
        (f"{MQTT_DATA_TOPIC_PREFIX}/M01/data", 1),
        (f"{MQTT_DATA_TOPIC_PREFIX}/M02/data", 1),
        (f"{MQTT_DATA_TOPIC_PREFIX}/M03/data", 1),
    ]
    logging.info("Subscribing to MQTT topics...")
    client.subscribe(topics)
    logging.info(f"Subscribed to topics: {', '.join([topic[0] for topic in topics])}")


def on_message(client, userdata, message):
    try:
        if "status" in message.topic:
            kafka_topic = "factory_machine_status"
        else:
            machine_name = message.topic.split("/")[2]
            kafka_topic = f"factory_machine_{machine_name}_data"

        producer.produce(kafka_topic, message.payload)
        logging.debug(
            f"Forwarded message from {message.topic} to Kafka topic {kafka_topic}"
        )

    except KafkaException as ke:
        logging.error(
            f"Kafka error while processing message from {message.topic}: {ke}"
        )
        raise SystemExit("Fatal Kafka error. Exiting application...")

    except Exception as e:
        logging.error(
            f"Unexpected error while processing message from {message.topic}: {e}"
        )
        raise SystemExit("Fatal unexpected error. Exiting application...")


def main():
    logging.info("Starting MQTT to Kafka connector...")

    global producer
    producer = configure_kafka()

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    logging.info("Connected to MQTT broker. Entering message processing loop...")
    client.loop_forever()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as se:
        logging.error(se)
        raise
    except Exception as e:
        logging.critical(f"Uncaught exception: {e}")
        raise
