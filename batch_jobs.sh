for agency in valley_metro; do
  env_file="/app/env/${agency}.env"
  common_env_file="/app/env/.env"
  credentials_env_file="/app/env/credentials.env"
  echo "🚀 Launching delay calculator for $agency with envs $common_env_file and $env_file"

  docker exec \
  -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  --user spark spark-master bash -c "
    set -a
    [ -f $common_env_file ] && source $common_env_file
    [ -f $env_file ] && source $env_file
    [ -f $credentials_env_file ] && source $credentials_env_file
    set +a
    spark-submit \
      --master spark://spark-master:7077 \
      --conf 'spark.jars.ivy=/tmp/.ivy2' \
      --conf spark.executor.cores=1 \
      --conf spark.cores.max=1 \
      --conf spark.executor.memory=1800mb \
      --conf "spark.sql.session.timeZone=America/Phoenix" \
      --jars /opt/bitnami/spark/jars/hadoop-aws-3.3.4.jar,\
/opt/bitnami/spark/jars/aws-java-sdk-bundle-1.12.262.jar,\
/opt/bitnami/spark/jars/spark-sql-kafka-0-10_2.12-3.5.2.jar,\
/opt/bitnami/spark/jars/kafka-clients-3.5.2.jar,\
/opt/bitnami/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.2.jar,\
/opt/bitnami/spark/jars/commons-pool2-2.11.1.jar \
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