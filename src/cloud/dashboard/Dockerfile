# Use an official Python runtime as the parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Install the required libraries
RUN pip install confluent-kafka Flask Flask-SocketIO eventlet

# Run factory.py when the container launches
CMD ["python", "./webserver.py"]