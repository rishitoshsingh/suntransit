#!/bin/bash

echo "Creating topic: vehicle_positions with 2-hour retention"

kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --if-not-exists \
  --topic vehicle_positions \
  --partitions 1 \
  --replication-factor 1 \
  --config retention.ms=7200000