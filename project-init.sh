#!/bin/bash

set -e

echo "📦 Waiting for Kafka to be ready..."
until docker exec kafka bash -c "nc -z localhost 9092"; do
  sleep 1
done
echo "✅ Kafka is up."

for topic in valley_metro_positions mbta_positions; do
  echo "📄 Creating topic '$topic' if not exists..."
  docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions 1 \
    --replication-factor 1 \
    --config retention.ms=7200000
done

echo "✅ Kafka topic(s) created."
