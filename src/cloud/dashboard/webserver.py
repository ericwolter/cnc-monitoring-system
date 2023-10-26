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

current_toggled_machine = None


def kafka_consumer():
    try:
        logger.info("Kafka consumer connecting...")
        conf = {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": "dashboard-consumer-12345",
            "enable.auto.commit": True,
            "auto.offset.reset": "latest",
        }

        consumer = Consumer(conf)
        logger.info(f"Subscribing to {KAFKA_STATUS_TOPIC} topic")
        consumer.subscribe(
            [
                KAFKA_STATUS_TOPIC,
                "factory_machine_M01_data",
                "factory_machine_M02_data",
                "factory_machine_M03_data",
            ]
        )

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
                    sys.exit(-2)
            else:
                if message.topic().startswith(KAFKA_STATUS_TOPIC):
                    msg = message.value().decode("utf-8")
                    machine_status = json.loads(msg)

                    logger.info(f"Received machine status: {machine_status}")

                    # Update the machines_status dictionary with the new status
                    machine_id = machine_status["machine_id"]
                    status = machine_status["status"]
                    machines_status[machine_id] = status

                    socketio.emit(f"{KAFKA_STATUS_TOPIC}", machine_status)
                else:
                    msg = message.value().decode("utf-8")
                    machine_data = json.loads(msg)
                    # Only emit if the machine is currently toggled on
                    if (
                        current_toggled_machine
                        and current_toggled_machine == machine_data["machine_id"]
                    ):
                        logger.info(
                            f"Received vibration data for toggled-on machine {machine_data['machine_id']}"
                        )
                        socketio.emit("update-chart", machine_data)

    except Exception as e:
        logger.error(f"consumer error: {e}")
        sys.exit(-1)


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
        socketio.run(app, host="0.0.0.0", port=5050, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"server error: {e}")
