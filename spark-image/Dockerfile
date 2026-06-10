FROM apache/spark:3.5.2

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app /tmp/.ivy2 && chown -R 185:185 /app /tmp/.ivy2

COPY spark-image/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --upgrade pip && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY spark-image/log4j.properties /opt/spark/conf/log4j.properties

COPY spark-jobs /app

WORKDIR /app

USER 185

RUN curl -s https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar -o /opt/spark/jars/hadoop-aws-3.3.4.jar
RUN curl -s https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar -o /opt/spark/jars/aws-java-sdk-bundle-1.12.262.jar
RUN curl -s https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.2/spark-sql-kafka-0-10_2.12-3.5.2.jar -o /opt/spark/jars/spark-sql-kafka-0-10_2.12-3.5.2.jar
RUN curl -s https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.2/kafka-clients-3.5.2.jar -o /opt/spark/jars/kafka-clients-3.5.2.jar
RUN curl -s https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.2/spark-token-provider-kafka-0-10_2.12-3.5.2.jar -o /opt/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.2.jar
RUN curl -s https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar -o /opt/spark/jars/commons-pool2-2.11.1.jar
RUN curl -s https://jdbc.postgresql.org/download/postgresql-42.7.3.jar -o /opt/spark/jars/postgresql-42.7.3.jar
