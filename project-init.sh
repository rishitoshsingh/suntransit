#!/bin/bash

set -e

echo "📦 Waiting for Kafka to be ready..."
until docker exec kafka bash -c "nc -z localhost 9092"; do
  sleep 1
done
echo "✅ Kafka is up."

echo "📄 Creating topic 'vehicle_positions' if not exists..."
docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --if-not-exists \
  --topic vehicle_positions \
  --partitions 1 \
  --replication-factor 1 \
  --config retention.ms=7200000

echo "✅ Kafka topic created."
echo "🚀 Submitting Spark jobs to suntransit-spark..."

for job in ./spark-jobs/*.py; do
  job_name=$(basename "$job")
  echo "🔁 Submitting $job_name"
  docker exec --user spark suntransit-spark spark-submit \
    --master spark://spark:7077 \
    --conf "spark.jars.ivy=/tmp/.ivy2" \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
    /app/"$job_name"
done

echo "✅ All jobs submitted." 