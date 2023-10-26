import json
import logging

from flask import Flask, render_template
from flask_socketio import SocketIO
from confluent_kafka import Consumer, KafkaError

import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
KAFKA_BROKER = "kafka:9092"
KAFKA_STATUS_TOPIC = "factory_machine_status"

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Default machine statuses
machines_status = {
    "M01": "Unknown",
    "M02": "Unknown",
    "M03": "Unknown",
}

current_toggled_machine = None


def kafka_consumer():
    try:
        logger.info("Initializing Kafka consumer...")
        conf = {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": "dashboard-consumer-12345",
            "enable.auto.commit": True,
            "auto.offset.reset": "latest",
        }

        consumer = Consumer(conf)

        logging.info("Subscribing to Kafka topics...")
        topics = [
            KAFKA_STATUS_TOPIC,
            "factory_machine_M01_data",
            "factory_machine_M02_data",
            "factory_machine_M03_data",
        ]
        consumer.subscribe(topics)
        logging.info(f"Subscribed to topics: {', '.join(topics)}")
        logger.info("Kafka consumer initialized and subscribed.")

        while True:
            message = consumer.poll(0.5)
            if message is None:
                continue
            if message.error():
                logger.error(
                    f"Kafka error on topic {message.topic()}: {message.error()}"
                )
                if message.error().code() != KafkaError._PARTITION_EOF:
                    raise SystemExit("Critical Kafka error. Exiting application...")
            else:
                process_message(message)

    except Exception as e:
        logger.critical(f"Fatal error in Kafka consumer: {e}")
        raise SystemExit("Exiting due to fatal error in Kafka consumer...")


def process_message(message):
    try:
        if message.topic().startswith(KAFKA_STATUS_TOPIC):
            msg = message.value().decode("utf-8")
            machine_status = json.loads(msg)
            machine_id = machine_status["machine_id"]
            status = machine_status["status"]
            machines_status[machine_id] = status
            logger.info(f"Processed status for machine {machine_id}: {status}")
            socketio.emit(f"{KAFKA_STATUS_TOPIC}", machine_status)
        else:
            msg = message.value().decode("utf-8")
            machine_data = json.loads(msg)
            machine_id = machine_data["machine_id"]
            if current_toggled_machine and current_toggled_machine == machine_id:
                logger.info(f"Processed vibration data for machine {machine_id}")
                socketio.emit("update-chart", machine_data)
    except json.JSONDecodeError:
        logger.error(
            f"Failed to decode JSON message from topic {message.topic()}: {message.value().decode('utf-8')}"
        )
    except Exception as e:
        logger.error(f"Error processing message from topic {message.topic()}: {e}")


@socketio.on("toggle-machine-data")
def handle_toggle(data):
    global current_toggled_machine

    machine_id = data.get("machine_id")

    if not machine_id:
        logger.error("Received toggle event without machine_id")
        return

    if machine_id != current_toggled_machine:
        logger.info(
            f"Data toggle enabled for machine {machine_id}. Previous toggled machine was {current_toggled_machine}."
        )
        current_toggled_machine = machine_id
        socketio.emit("start-chart")
    else:
        logger.info(f"Data toggle disabled for machine {machine_id}.")
        current_toggled_machine = None
        socketio.emit("stop-chart")


@socketio.on("connect")
def handle_connection():
    logger.info("Client connected.")
    socketio.emit("initial-status", machines_status)


@app.route("/")
def index():
    return render_template("index.html", machines_status=machines_status)


def main():
    logger.info("Starting web server with integrated Kafka consumer...")
    socketio.start_background_task(kafka_consumer)
    socketio.run(app, host="0.0.0.0", port=5050, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as se:
        logging.error(se)
        raise
    except Exception as e:
        logging.critical(f"Uncaught exception: {e}")
        raise
