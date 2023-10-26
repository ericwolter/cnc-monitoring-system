# CNC Monitoring System

This repository contains a system for monitoring CNC milling machines and detecting anomalies in the machining processes using vibration data analysis.

## Introduction

The system allows monitoring the health status of CNC milling machines and detecting anomalies in real-time. It consists of:

- Edge components that run on the machines to collect vibration data and publish it via MQTT
- Cloud components to ingest the MQTT data, run analytics, and visualize on a dashboard
- Shared libraries for loading, processing, and analyzing vibration data
- Tools for managing and configuring the system
- Example datasets and notebooks for model training and evaluation

## System Architecture

The system follows an edge-cloud architecture:

### Edge Layer

- `edge/factory` - Containerized application to simulate CNC machines and publish vibration data via MQTT

It generates synthetic vibration data reflecting normal and anomalous machining processes.

### Cloud Layer  

- `cloud/mqtt-kafka-connector` - Bridge between MQTT and Kafka 
- `cloud/dashboard` - Visualize real-time machine status and vibration data charts
- `src/common` - Shared data loading and processing logic
- `notebooks` - Explore data, train models, and evaluate performance

Kafka is used for scalable ingestion. The dashboard provides real-time visibility into machine health.

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Usage

To start the system locally:
```
docker-compose up
```
Access the dashboard at http://localhost:5050

## Data

- `data/` contains example CNC machine datasets from 3 different machines
- Data structure and format is documented in `data/README.md` 
- Notebooks in `notebooks/` provide utilities for loading, visualizing and analyzing the data

## Models

- Trained models are saved in the `models/` folder
- The `notebooks/` folder contains examples of model training and evaluation

## Configuration

System configurations are located under `configs/`

## Tools

Helper scripts for managing the system are under `tools/`

## License

This system is licensed under the [MIT license](LICENSE). Data is licensed under the [CC BY 4.0](data/License.txt) license.