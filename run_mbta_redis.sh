#!/bin/bash
export DOCKER_HOST=unix:///var/run/docker.sock

agency=massachusetts_bay_transportation_authority
env_file="/app/env/${agency}.env"
common_env_file="/app/env/.env"
credentials_env_file="/app/env/credentials.env"

echo "[$(date)] Killing any existing spark-submit for $agency inside container..."
docker exec --user spark spark-master pkill -f "REDIS-${agency}" 2>/dev/null || true
sleep 3

echo "[$(date)] Starting Kafka->Redis job for $agency"
docker exec --user spark spark-master bash -c "
  set -a
  [ -f $common_env_file ] && source $common_env_file
  [ -f $env_file ] && source $env_file
  [ -f $credentials_env_file ] && source $credentials_env_file
  set +a
  /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --conf 'spark.jars.ivy=/tmp/.ivy2' \
    --conf spark.executor.cores=1 \
    --conf spark.cores.max=1 \
    --conf spark.executor.memory=900m \
    --jars /opt/spark/jars/spark-sql-kafka-0-10_2.12-3.5.2.jar,/opt/spark/jars/kafka-clients-3.5.2.jar,/opt/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.2.jar,/opt/spark/jars/commons-pool2-2.11.1.jar \
    /app/push_redis.py >> /tmp/REDIS-${agency}.log
"
exit_code=$?
echo "[$(date)] $agency Redis job exited with code $exit_code"
exit $exit_code
