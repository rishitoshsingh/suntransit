#!/bin/bash

# Start Kafka in the background
/etc/confluent/docker/run &

# Wait until Kafka is ready
echo "⏳ Waiting for Kafka to be ready..."
cub kafka-ready -b localhost:9092 1 30

# Run your topic creation script
/create-topics.sh

# Wait indefinitely (so container doesn't exit)
/bin/bash