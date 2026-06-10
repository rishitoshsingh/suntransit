export DOCKER_HOST=unix:///var/run/docker.sock

for agency in massachusetts_bay_transportation_authority valley_metro; do
  env_file="/app/env/${agency}.env"
  common_env_file="/app/env/.env"
  credentials_env_file="/app/env/credentials.env"
  echo "🚀 Launching delay calculator for $agency with envs $common_env_file and $env_file"
  docker exec \
  --user spark spark-master bash -c "
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
      --conf spark.executor.memory=1800mb \
      --conf spark.sql.adaptive.enabled=true \
      --conf spark.sql.adaptive.coalescePartitions.enabled=true \
      --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
      --conf spark.hadoop.fs.s3a.block.size=134217728 \
      --conf spark.hadoop.fs.s3a.buffer.dir=/tmp \
      --conf spark.hadoop.fs.s3a.committer.name=magic \
      --conf spark.hadoop.fs.s3a.committer.magic.enabled=true \
      --conf spark.hadoop.mapreduce.outputcommitter.factory.scheme.s3a=org.apache.hadoop.fs.s3a.commit.S3ACommitterFactory \
      --py-files /app/batch/offset.py \
      /app/batch/delay_calculator.py >> /tmp/${agency}.log
  "
done