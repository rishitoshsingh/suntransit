import json
import logging
import os
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

import psycopg2
from psycopg2.extras import execute_values
from confluent_kafka.admin import AdminClient

_JDBC_ONLY_PARAMS = {"channelBinding", "reWriteBatchedInserts", "prepareThreshold"}


def _to_psycopg2_url(raw_url: str) -> str:
    url = raw_url[5:] if raw_url.startswith("jdbc:") else raw_url
    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()
              if k not in _JDBC_ONLY_PARAMS}
    cleaned = parsed._replace(query=urlencode(params))
    return urlunparse(cleaned)


POSTGRESQL_URL = _to_psycopg2_url(os.getenv("POSTGRESQL_URL") or "")


class OffsetManager:
    def __init__(self, bootstrap_servers, postgresql_url=POSTGRESQL_URL):
        self.bootstrap_servers = bootstrap_servers
        self.postgresql_url = postgresql_url

    def _connect(self):
        return psycopg2.connect(self.postgresql_url)

    def save_offsets(self, topic, offsets, job_type):
        offsets_dict = offsets.rdd.map(
            lambda row: (str(row["partition"]), row["offset"] + 1)
        ).collectAsMap()

        if not offsets_dict:
            return

        rows = [(topic, job_type, partition, int(offset))
                for partition, offset in offsets_dict.items()]

        with self._connect() as conn, conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO kafka_offsets (topic, job_type, partition, "offset")
                VALUES %s
                ON CONFLICT (topic, job_type, partition)
                DO UPDATE SET "offset" = EXCLUDED."offset"
            """, rows)

        logging.info(f"Saved offsets for topic {topic}: {offsets_dict}")

    def read_offsets(self, topic, job_type):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT partition, "offset" FROM kafka_offsets WHERE topic = %s AND job_type = %s',
                (topic, job_type)
            )
            rows = cur.fetchall()

        if not rows:
            return "earliest"

        offset_dict = {partition: offset for partition, offset in rows}
        all_partitions = self.get_all_partitions(topic)
        complete = {str(p): int(offset_dict.get(str(p), -2)) for p in all_partitions}
        return json.dumps({topic: complete})

    def get_all_partitions(self, topic):
        admin_client = AdminClient({"bootstrap.servers": self.bootstrap_servers})
        topic_metadata = admin_client.list_topics(topic=topic, timeout=10)
        if topic not in topic_metadata.topics:
            raise ValueError(f"Topic {topic} does not exist.")
        return list(topic_metadata.topics[topic].partitions.keys())
