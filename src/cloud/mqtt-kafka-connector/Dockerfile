# Use an official Python runtime as the parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Install the required libraries
RUN pip install paho-mqtt confluent-kafka

# Run factory.py when the container launches
CMD ["python", "./mqtt_kafka_connector.py"]