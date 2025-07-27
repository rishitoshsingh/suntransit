# 🚌 SunTransit: Real-Time Public Transport Delay Tracker

SunTransit is a scalable, distributed system that processes GTFS real-time feeds and historical schedules to compute transit delays, publish them via Kafka, and store them in S3 for downstream analytics.

Built using Apache Spark, Kafka, Redis, and AWS S3, the system is containerized using Docker and deployable on both standalone clusters and Kubernetes.

---

## System 

![SunTransit System Dataflow](./dataflow.png)

The diagram below illustrates the end-to-end data flow in SunTransit, from GTFS real-time feed ingestion, through Spark-based delay computation, Kafka event streaming, Redis offset management, and S3-based storage for analytics.

## 🔧 Project Features

* ✅ GTFS real-time trip delay calculator using Spark
* ✅ Kafka producer to push delay events to a topic
* ✅ Redis-based stateful offset tracking for fault tolerance
* ✅ S3-based storage for hourly, agency-wise partitioned Parquet files
* ✅ Support for both standalone Spark cluster and Kubernetes

---

## 📁 Project Structure

```
.
├── batch/                       # Spark batch jobs
│   ├── delay_calculator.py     # Main batch job
│   └── offset.py               # Redis-based offset tracking
├── env/                        # Per-agency and shared .env files
│   ├── valley_metro.env
│   └── .env
├── spark-image/                # Docker image for Spark + dependencies
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 🚀 Getting Started

### 1️⃣ Build Spark Image

```bash
docker build -t suntransit-spark:latest ./spark-image
```

### 2️⃣ Launch Docker Compose (Standalone Spark)

```bash
docker-compose up -d
```

---

## 🧪 Run Spark Job

```bash
for agency in valley_metro; do
  docker exec --user spark suntransit-spark bash -c "
    set -a
    source /app/env/.env
    source /app/env/${agency}.env
    set +a

    spark-submit \
      --master spark://spark-master:7077 \
      --conf spark.sql.session.timeZone=America/Phoenix \
      --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
      --conf spark.hadoop.fs.s3a.path.style.access=true \
      --conf spark.hadoop.fs.s3a.access.key=\$AWS_ACCESS_KEY_ID \
      --conf spark.hadoop.fs.s3a.secret.key=\$AWS_SECRET_ACCESS_KEY \
      --conf spark.hadoop.fs.s3a.endpoint=s3.\$AWS_REGION.amazonaws.com \
      --conf spark.hadoop.fs.s3a.aws.credentials.provider=org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider \
      --py-files /app/batch/offset.py \
      /app/batch/delay_calculator.py >> /tmp/\${agency}.log 2>&1
  "
done
```

---

## ☁️ Deploy on Kubernetes (Optional)

1. Push Docker image to registry:

```bash
docker tag suntransit-spark your-dockerhub-username/suntransit-spark:latest
docker push your-dockerhub-username/suntransit-spark:latest
```

2. Apply Spark Operator:

```bash
helm repo add spark-operator https://googlecloudplatform.github.io/spark-on-k8s-operator
helm install spark-operator spark-operator/spark-operator --namespace spark-operator --create-namespace
```

3. Submit job via `SparkApplication` CRD.

---

## ⚙️ Environment Variables

Each agency gets its own `.env` file inside `/app/env/`.

### Sample `.env` for `valley_metro.env`

```env
S3_BUCKET=s3a://suntransit/valley_metro
KAFKA_TOPIC=valley_metro_delay
KAFKA_BROKER=kafka:9092
GTFS_AGENCY=ValleyMetro
MONGODB_URL=mongodb://mongo:27017
MONGODB_DB=suntransit
MONGODB_COLLECTION=valley_metro_trips
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-west-2
TIMEZONE=America/Phoenix
```

---

## 🚩 Output

Delays are written to S3 as hourly-partitioned Parquet files:

```
s3a://suntransit/valley_metro/
  └── agency=ValleyMetro/
      └── day=2025-07-22/
          └── hour=22-00/
              └── part-*.parquet
```

---

## 📊 Future Improvements

* [ ] Add job scheduler (via Airflow or K8s CronJob)
* [ ] Support for PostgreSQL or Delta Lake
* [ ] Monitoring and metrics with Prometheus + Grafana
* [ ] Use AWS IAM roles for authentication instead of access keys

---

## 🧐 Tech Stack

| Tech         | Purpose                     |
| ------------ | --------------------------- |
| Apache Spark | Batch processing            |
| Kafka        | Delay event messaging       |
| Redis        | Offset checkpointing        |
| S3 (S3A)     | Partitioned Parquet storage |
| Docker       | Containerization            |
| Kubernetes   | Orchestration (optional)    |

---

## 👨‍💼 Author

Built with ❤️ by [@rishitoshsingh](https://github.com/rishitoshsingh)
~Written by ChatGPT

---
