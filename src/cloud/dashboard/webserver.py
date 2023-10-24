import json
import logging

from flask import Flask, render_template
from flask_socketio import SocketIO
from confluent_kafka import Consumer, KafkaError

import sys

# Constants
KAFKA_BROKER = "kafka:9092"
KAFKA_STATUS_TOPIC = "factory_machine_status"

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Default machine statuses
machines_status = {
    "M01": "Unknown",
    "M02": "Unknown",
    "M03": "Unknown",
}


def kafka_consumer():
    try:
        logger.info("Kafka consumer connecting...")
        conf = {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": "dashboard-consumer-12345",
            "enable.auto.commit": True,
            "logger": "confluent_kafka",
        }

        consumer = Consumer(conf)
        logger.info(f"Subscribing to {KAFKA_STATUS_TOPIC} topic")
        consumer.subscribe([KAFKA_STATUS_TOPIC])

        while True:
            message = consumer.poll(0.5)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    logger.info(
                        "Reached end of %s [%d] at offset %d",
                        message.topic(),
                        message.partition(),
                        message.offset(),
                    )
                else:
                    logger.error(f"Kafka error: {message.error()}")
            else:
                msg = message.value().decode("utf-8")
                machine_data = json.loads(msg)

                # Update the machines_status dictionary with the new status
                machine_id = machine_data["machine_id"]
                status = machine_data["status"]
                machines_status[machine_id] = status

                socketio.emit(f"{KAFKA_STATUS_TOPIC}", machine_data)

    except Exception as e:
        logger.error(f"consumer error: {e}")
        sys.exit(-1)


@socketio.on("connect")
def handle_connection():
    logger.info("Client connected.")

    # Emit the cached machine statuses to the newly connected client
    socketio.emit("initial-status", machines_status)


@app.route("/")
def index():
    return render_template("index.html", machines_status=machines_status)


if __name__ == "__main__":
    try:
        logger.info("Starting Kafka consumer...")
        socketio.start_background_task(kafka_consumer)
        logger.info("Starting webserver...")
        socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"server error: {e}")
