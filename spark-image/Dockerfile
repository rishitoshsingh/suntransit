# Start from the official Bitnami Spark image
FROM bitnami/spark:3.5.2

# Switch to the root user to perform administrative tasks
USER root
RUN install_packages curl
# Bitnami images run Spark as user 1001. We ensure this user exists and has a name.
# Create a group and user 'spark' with the expected UID/GID.
# Create directories and set ownership. This prevents permission errors.
RUN groupadd -r spark -g 1001 && \
    useradd -r -u 1001 -g spark -d /home/spark -m spark && \
    mkdir -p /app /tmp/.ivy2 && \
    chown -R 1001:1001 /app /tmp/.ivy2 && \
    # Also ensure the default bitnami home is owned correctly
    chown -R 1001:1001 /opt/bitnami

# Copy and install python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY log4j.properties /opt/bitnami/spark/conf/log4j.properties

# Set the working directory for our jobs
WORKDIR /app

# Switch to the non-root user we just configured.
# All subsequent commands and the container's main process will run as this user.
USER 1001

RUN curl https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar --output /opt/bitnami/spark/jars/aws-java-sdk-bundle-1.12.262.jar
RUN curl https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.2/spark-sql-kafka-0-10_2.12-3.5.2.jar --output /opt/bitnami/spark/jars/spark-sql-kafka-0-10_2.12-3.5.2.jar
RUN curl https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.2/kafka-clients-3.5.2.jar --output /opt/bitnami/spark/jars/kafka-clients-3.5.2.jar
RUN curl https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.2/spark-token-provider-kafka-0-10_2.12-3.5.2.jar --output /opt/bitnami/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.2.jar
RUN curl https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar --output /opt/bitnami/spark/jars/commons-pool2-2.11.1.jar