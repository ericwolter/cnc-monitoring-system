import json
import logging
import multiprocessing
import os
import random
import time

import h5py
import paho.mqtt.client as mqtt

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# MQTT broker configuration
BROKER_HOST = "mosquitto"
BROKER_PORT = 1883
DATA_TOPIC = "factory/machines/data"
STATUS_TOPIC = "factory/machines/status"


def evaluate_process_health(vibration_data):
    """Theoretical machine learning model classification."""

    FALSE_POSITIVE_RATE = 0.05  # 5% chance to misclassify a good machine as "bad"
    FALSE_NEGATIVE_RATE = 0.03  # 3% chance to misclassify a bad machine as "good"

    # Classification based on randomness for simplicity
    classification = "bad" if random.random() < 0.5 else "good"

    # Introduce false positives and negatives
    if classification == "good" and random.random() < FALSE_POSITIVE_RATE:
        return "bad"
    elif classification == "bad" and random.random() < FALSE_NEGATIVE_RATE:
        return "good"

    return classification


def publish_mqtt_message(client, topic, payload_dict):
    """Publishes a message to the given MQTT topic in JSON format."""
    json_payload = json.dumps(payload_dict)
    client.publish(topic, json_payload)


def machine_simulation(machine_id):
    """Simulate a machine producing sensor data and sending it to MQTT broker."""
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()

    # Define the frequency
    FREQUENCY_SLEEP_TIME = 1.0 / 2000  # For 2kHz
    # Define anomaly rate
    TRUE_ANOMALY_RATE = 0.01  # For 1%
    # Define wait times
    MAINTENANCE_TIME = 30  # seconds
    RELOAD_TIME = 2  # seconds

    # Define the path to the h5 file
    machine_name = f"M0{machine_id + 1}"
    process_name = f"OP07"

    publish_mqtt_message(
        client, STATUS_TOPIC, {"machine_id": machine_name, "status": "Initializing"}
    )

    while True:
        publish_mqtt_message(
            client, STATUS_TOPIC, {"machine_id": machine_name, "status": "Starting"}
        )

        # Decide between good and bad run based on anomaly rate
        label = "bad" if random.random() < TRUE_ANOMALY_RATE else "good"

        # Get all available runs under the chosen label
        run_dir = f"/data/{machine_name}/{process_name}/{label}"
        available_runs = [file for file in os.listdir(run_dir) if file.endswith(".h5")]

        # Randomly pick one run from the available runs
        chosen_run = random.choice(available_runs)
        file_path = os.path.join(run_dir, chosen_run)

        # Read data from h5 file
        with h5py.File(file_path, "r") as hf:
            vibration_data = list(hf["vibration_data"])

        # Initialize timestamp
        relative_timestamp = 0

        publish_mqtt_message(
            client, STATUS_TOPIC, {"machine_id": machine_name, "status": "Running"}
        )

        # Iterate over the vibration data
        for data in vibration_data:
            message = {
                "machine_id": machine_name,
                "process_id": process_name,
                "timestamp": relative_timestamp,
                "vibration_data": data.tolist(),  # Directly using the [x, y, z] array
            }

            publish_mqtt_message(client, DATA_TOPIC, message)
            relative_timestamp += FREQUENCY_SLEEP_TIME
            time.sleep(FREQUENCY_SLEEP_TIME)

        # After data is exhausted, classify using our machine learning model
        classification_result = evaluate_process_health(data)

        publish_mqtt_message(
            client,
            STATUS_TOPIC,
            {
                "machine_id": machine_name,
                "status": "Completed",
                "classification": classification_result,
            },
        )

        if classification_result == "bad":
            publish_mqtt_message(
                client,
                STATUS_TOPIC,
                {"machine_id": machine_name, "status": "Maintenance Mode"},
            )
            time.sleep(MAINTENANCE_TIME)

        publish_mqtt_message(
            client, STATUS_TOPIC, {"machine_id": machine_name, "status": "Reloading"}
        )
        time.sleep(RELOAD_TIME)


if __name__ == "__main__":
    logging.info("Starting factory simulation...")

    # Start multiple machine simulations
    machines = [
        multiprocessing.Process(target=machine_simulation, args=(i,)) for i in range(3)
    ]
    for machine in machines:
        machine.start()

    logging.info("Factory simulation running...")
