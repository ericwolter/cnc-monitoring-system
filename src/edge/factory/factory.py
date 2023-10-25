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
DATA_TOPIC_PREFIX = "factory/machines"
STATUS_TOPIC = "factory/machines/status"


def evaluate_process_health_cautious(vibration_data, label):
    """Machine learning model classification."""

    # Classification based on randomness for simplicity
    if label == "bad":
        return "bad"
    # i.e. 50% of true good cases are also treated as bad
    # i.e. wasteful overly cautious classifer
    classification = "bad" if random.random() < 0.5 else "good"

    return classification


def evaluate_process_health_simple(vibration_data, label):
    """Machine learning model classification."""
    return label


# This variable will store the current classification method for each machine
classification_methods = {
    "M01": evaluate_process_health_cautious,
    "M02": evaluate_process_health_cautious,
    "M03": evaluate_process_health_cautious,
}


def publish_mqtt_message(client, topic, payload_dict):
    """Publishes a message to the given MQTT topic in JSON format."""
    json_payload = json.dumps(payload_dict)
    client.publish(topic, json_payload)


def on_message(client, userdata, message):
    """Callback for when a message is received on the control channel."""
    machine_id = userdata["machine_id"]
    try:
        payload = json.loads(message.payload.decode())
        command = payload.get("command", "")
        args = payload.get("args", [])

        if command == "switch_classification_method":
            if args[0] == "simple":
                classification_methods[machine_id] = evaluate_process_health_simple
            elif args[0] == "cautious":
                classification_methods[machine_id] = evaluate_process_health_cautious
            else:
                classification_methods[machine_id] = evaluate_process_health_cautious
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON received: {message.payload.decode()}")


def machine_simulation(machine_id):
    """Simulate a machine producing sensor data and sending it to MQTT broker."""

    # Define the path to the h5 file
    machine_name = f"M0{machine_id + 1}"
    process_name = f"OP07"

    client = mqtt.Client(userdata={"machine_id": machine_name})
    client.connect(BROKER_HOST, BROKER_PORT, 60)

    # Subscribe to the machine's control channel
    client.subscribe(f"factory/machines/{machine_name}/control")
    client.on_message = on_message

    client.loop_start()

    # Define the frequency
    FREQUENCY_SLEEP_TIME = 1.0 / 2000  # For 2kHz
    BATCH_SIZE = 2000
    # Define anomaly rate
    TRUE_ANOMALY_RATE = 0.01  # For 1%
    # Define wait times
    MAINTENANCE_TIME = 60  # seconds
    RELOAD_TIME = 5  # seconds

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

        publish_mqtt_message(
            client, STATUS_TOPIC, {"machine_id": machine_name, "status": "Running"}
        )

        # Iterate over the vibration data in batches of 2000 samples
        for i in range(0, len(vibration_data), BATCH_SIZE):
            batch_data = vibration_data[i : i + BATCH_SIZE]
            message = {
                "machine_id": machine_name,
                "process_id": process_name,
                "sequence_start": i,
                "sequence_end": i + len(batch_data) - 1,
                "vibration_data": [datum.tolist() for datum in batch_data],
            }

            publish_mqtt_message(
                client, f"{DATA_TOPIC_PREFIX}/{machine_name}/data", message
            )

            # Adjust sleep time based on the size of the current batch
            current_batch_sleep_time = FREQUENCY_SLEEP_TIME * len(batch_data)
            time.sleep(current_batch_sleep_time)

        # After data is exhausted, classify using our machine learning model
        classification_result = classification_methods[machine_name](
            vibration_data, label
        )

        publish_mqtt_message(
            client,
            STATUS_TOPIC,
            {
                "machine_id": machine_name,
                "status": "Completed",
                "label": label,
                "classification": classification_result,
                "current_model": classification_methods[
                    machine_name
                ].__name__,  # Indicate the current model being used
            },
        )

        if classification_result == "bad":
            publish_mqtt_message(
                client,
                STATUS_TOPIC,
                {"machine_id": machine_name, "status": "Maintenance"},
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
