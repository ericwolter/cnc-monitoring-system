import json
import logging
import multiprocessing
import os
import random
import time

import h5py
import paho.mqtt.client as mqtt
import numpy as np
import onnxruntime

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ONNX configuration
ONNX_FILE_PATH = "/model/best.onnx"
ONNX_ORT_SESSION = onnxruntime.InferenceSession(ONNX_FILE_PATH)
ONNX_INPUT_NAME = ONNX_ORT_SESSION.get_inputs()[0].name


class ONNXModelEvaluator:
    """Class to handle ONNX model operations and evaluations."""

    MIN_VALUE = -2500.0
    MAX_VALUE = 2500.0
    SEQ_LENGTH = 4000
    THRESHOLD = 0.01392  # Empirically determined threshold

    @staticmethod
    def normalize_data(data):
        """Normalize the provided data."""
        normalized_data = (
            2
            * (
                (data - ONNXModelEvaluator.MIN_VALUE)
                / (ONNXModelEvaluator.MAX_VALUE - ONNXModelEvaluator.MIN_VALUE)
            )
            - 1
        )
        return normalized_data

    @staticmethod
    def infer_and_compute_loss(data_normalized):
        """Use the ONNX model to infer and compute the loss."""
        losses = []
        num_chunks = len(data_normalized) // ONNXModelEvaluator.SEQ_LENGTH

        for i in range(num_chunks):
            chunk = data_normalized[
                i
                * ONNXModelEvaluator.SEQ_LENGTH : (i + 1)
                * ONNXModelEvaluator.SEQ_LENGTH
            ]
            chunk = chunk.reshape(1, ONNXModelEvaluator.SEQ_LENGTH, 3).astype(
                np.float32
            )
            ort_inputs = {ONNX_INPUT_NAME: chunk}
            ort_outs = ONNX_ORT_SESSION.run(None, ort_inputs)
            reconstruction = np.array(ort_outs).squeeze()
            loss = np.mean((reconstruction - chunk) ** 2)
            losses.append(loss)

        return np.mean(losses)

    @classmethod
    def evaluate(cls, vibration_data):
        """
        ONNX Evaluation Strategy:
        Uses a trained ONNX model to evaluate the vibration data and determine the health of the process.
        The model determines the quality based on the mean squared error (MSE) between the original and reconstructed data.
        """
        data_normalized = cls.normalize_data(vibration_data)
        mse_loss = cls.infer_and_compute_loss(data_normalized)
        return "bad" if mse_loss > cls.THRESHOLD else "good"


def simple_evaluation(label):
    """
    Simple Evaluation Strategy:
    Directly returns the label without any additional processing.
    This strategy simulates a naive approach where the system blindly trusts the input label.
    """
    return label


def cautious_evaluation(label):
    """
    Cautious Evaluation Strategy:
    If the label is "bad", it immediately returns "bad".
    For a "good" label, there's a 50% chance it might still classify it as "bad".
    This strategy simulates an overly cautious system that tends to over-classify good processes as potentially bad.
    """
    return "bad" if label == "bad" or random.random() < 0.5 else "good"


def evaluate_process_health(vibration_data, label, strategy="onnx"):
    """
    Unified function to evaluate process health based on a chosen strategy.

    Args:
    - vibration_data: The input data used for evaluation (especially relevant for ONNX evaluation).
    - label: The true label of the process (either "good" or "bad").
    - strategy: The evaluation strategy to be used ("simple", "cautious", or "onnx").

    Returns:
    - The evaluation result based on the chosen strategy.
    """
    if strategy == "simple":
        return simple_evaluation(label)
    elif strategy == "cautious":
        return cautious_evaluation(label)
    elif strategy == "onnx":
        return ONNXModelEvaluator.evaluate(vibration_data)
    else:
        # Default to cautious strategy if an unknown strategy is provided
        return cautious_evaluation(label)


class MachineSimulator:
    # MQTT broker connection details for publishing and subscribing to messages.
    MQTT_BROKER_HOST = "mosquitto"  # Hostname or IP address of the MQTT broker.
    MQTT_BROKER_PORT = 1883  # Port number the MQTT broker is listening on.

    # MQTT topic strings for publishing machine data and status updates.
    DATA_TOPIC_PREFIX = (
        "factory/machines"  # Main topic where machine data is published.
    )
    STATUS_TOPIC = "factory/machines/status"  # Main topic where machine status updates are published.

    # Rate at which anomalies (or "bad" runs) occur in the simulation.
    TRUE_ANOMALY_RATE = 0.01  # 1% anomaly rate.

    # The underlying vibration data is captured at a frequency of 2kHz.
    FREQUENCY_SLEEP_TIME = 1.0 / 2000
    # Number of data points in each published batch.
    BATCH_SIZE = 2000

    # Duration constants for various machine states.
    MAINTENANCE_TIME = (
        60  # Duration (in seconds) the machine goes into maintenance after a "bad" run.
    )
    RELOAD_TIME = 5  # Duration (in seconds) the machine takes to reload after completing a run or maintenance.

    def __init__(self, machine_id, process_name="OP07"):
        """Initialize the machine simulator with machine ID and process name."""
        self.machine_id = machine_id
        self.machine_name = f"M0{machine_id + 1}"
        self.process_name = process_name

        self.classification_strategy = "onnx"

        self.client = self._initialize_mqtt_client(
            self.MQTT_BROKER_HOST, self.MQTT_BROKER_PORT
        )

    def simulate(self):
        """Simulate the machine process by publishing data and updating status."""
        self._publish_status_message(
            {"machine_id": self.machine_name, "status": "Initializing"}
        )

        while True:
            self._publish_status_message(
                {"machine_id": self.machine_name, "status": "Starting"}
            )

            label = "bad" if random.random() < self.TRUE_ANOMALY_RATE else "good"
            file_path = self._select_run(label)
            vibration_data = self._read_vibration_data(file_path)

            self._publish_status_message(
                {"machine_id": self.machine_name, "status": "Running"}
            )

            self._publish_vibration_data(vibration_data)
            self._classify_and_update_status(vibration_data, label)

            self._publish_status_message(
                {"machine_id": self.machine_name, "status": "Reloading"}
            )
            time.sleep(self.RELOAD_TIME)

    def _initialize_mqtt_client(self, host, port):
        """Initialize and return the MQTT client for the given machine."""
        client = mqtt.Client(userdata={"machine_id": self.machine_name})
        client.connect(host, port, 60)
        client.subscribe(f"factory/machines/{self.machine_name}/control")
        client.on_message = self._on_message
        client.loop_start()
        return client

    def _on_message(self, client, userdata, message):
        """Callback for when a message is received on the control channel."""
        try:
            payload = json.loads(message.payload.decode())
            command = payload.get("command", "")
            args = payload.get("args", [])

            if command == "switch_classification_method":
                # Update the classification strategy based on the received command
                self.classification_strategy = args[0]

        except json.JSONDecodeError:
            logging.error(f"Invalid JSON received: {message.payload.decode()}")

    def _publish_status_message(self, payload):
        """Publish a status update to the MQTT broker."""
        self._publish_mqtt_message(self.STATUS_TOPIC, payload)

    def _publish_data_message(self, payload):
        """Publish vibration data to the MQTT broker."""
        topic = f"{self.DATA_TOPIC_PREFIX}/{self.machine_name}/data"
        self._publish_mqtt_message(topic, payload)

    def _publish_mqtt_message(self, topic, payload):
        """Publish a message to the given MQTT topic in JSON format."""
        json_payload = json.dumps(payload)
        self.client.publish(topic, json_payload)

    def _select_run(self, label):
        """Select and return a random run file path based on the given label."""
        run_dir = f"/data/{self.machine_name}/{self.process_name}/{label}"
        available_runs = [file for file in os.listdir(run_dir) if file.endswith(".h5")]
        chosen_run = random.choice(available_runs)
        return os.path.join(run_dir, chosen_run)

    def _read_vibration_data(self, file_path):
        """Read and return vibration data from the given .h5 file."""
        with h5py.File(file_path, "r") as hf:
            return hf["vibration_data"][:]

    def _publish_vibration_data(self, vibration_data):
        """Publish vibration data in batches to the MQTT broker."""
        for i in range(0, len(vibration_data), self.BATCH_SIZE):
            batch_data = vibration_data[i : i + self.BATCH_SIZE]
            message = {
                "machine_id": self.machine_name,
                "process_id": self.process_name,
                "sequence_start": i,
                "sequence_end": i + len(batch_data) - 1,
                "vibration_data": [datum.tolist() for datum in batch_data],
            }
            self._publish_data_message(message)

            current_batch_sleep_time = self.FREQUENCY_SLEEP_TIME * len(batch_data)
            time.sleep(current_batch_sleep_time)

    def _classify_and_update_status(self, vibration_data, label):
        """Classify the machine's state and publish status updates."""
        classification_result = evaluate_process_health(
            vibration_data, label, self.classification_strategy
        )
        self._publish_status_message(
            {
                "machine_id": self.machine_name,
                "status": "Completed",
                "label": label,
                "classification": classification_result,
                "current_model": self.classification_strategy,
            },
        )
        if classification_result == "bad":
            self._publish_status_message(
                {"machine_id": self.machine_name, "status": "Maintenance"}
            )
            time.sleep(self.MAINTENANCE_TIME)


def start_machine_simulation(machine_id):
    simulator = MachineSimulator(machine_id)
    simulator.simulate()


if __name__ == "__main__":
    logging.info("Starting factory simulation...")

    # Start multiple machine simulations
    for i in range(3):
        multiprocessing.Process(target=start_machine_simulation, args=(i,)).start()

    logging.info("Factory simulation running...")
