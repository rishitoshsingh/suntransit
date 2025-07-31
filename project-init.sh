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

echo "🚀 Submitting Spark jobs to suntransit-spark..."

for redis_agency_env in massachusetts_bay_transportation_authority valley_metro; do
  redis_env_file="/app/env/${redis_agency_env}.env"
  common_env_file="/app/env/.env"
  credentials_env_file="/app/env/credentials.env"
  echo "🚀 Launching producer for $redis_agency_env with envs $common_env_file and $redis_env_file"

  docker exec -d --user spark spark-master bash -c "
    set -a
    [ -f $common_env_file ] && source $common_env_file
    [ -f $redis_env_file ] && source $redis_env_file
    [ -f $credentials_env_file ] && source $credentials_env_file
    set +a

    nohup spark-submit \
      --master spark://spark-master:7077 \
      --conf 'spark.jars.ivy=/tmp/.ivy2' \
      --conf spark.executor.cores=1 \
      --conf spark.cores.max=1 \
      --conf spark.executor.memory=900m \
      --jars /opt/bitnami/spark/jars/spark-sql-kafka-0-10_2.12-3.5.2.jar,\
/opt/bitnami/spark/jars/kafka-clients-3.5.2.jar,\
/opt/bitnami/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.2.jar,\
/opt/bitnami/spark/jars/commons-pool2-2.11.1.jar \
      /app/push_redis.py >> /tmp/REDIS-${redis_agency_env}.log
  "
done

echo "✅ All jobs submitted." 