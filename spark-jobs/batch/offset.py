import json
import logging

from confluent_kafka.admin import AdminClient
from pymongo import MongoClient


class OffsetManager:
    def __init__(self, mongo_url, db_name, collection_name, bootstrap_servers):
        self.client = MongoClient(mongo_url)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.bootstrap_servers = bootstrap_servers

    def save_offsets(self, topic, offsets, job_type):
        offsets_dict = offsets.rdd.map(
            lambda row: (str(row["partition"]), row["offset"] + 1)
        ).collectAsMap()

        update_dict = {f"offsets.{partition}": offset for partition, offset in offsets_dict.items()}

        if update_dict:
            self.collection.update_one(
                {"topic": topic, "type": job_type},
                {"$set": update_dict, "$currentDate": {"updatedTime": True}},
                upsert=True
            )

        logging.info(f"Saved offsets for topic {topic}: {offsets_dict}")

    def read_offsets(self, topic, job_type):
        doc = self.collection.find_one({"topic": topic, "type": job_type})
        if doc and "offsets" in doc:
            offset_dict = doc.get("offsets")
            if not offset_dict:
                return "earliest"

            all_partitions = self.get_all_partitions(topic)
            complete_offset_dict = {str(p): int(offset_dict.get(str(p), -2)) for p in all_partitions}
            return json.dumps({topic: complete_offset_dict})
        else:
            return "earliest"

    def get_all_partitions(self, topic):
        # admin_client = AdminClient({"bootstrap.servers": "localhost:9092"})
        admin_client = AdminClient({"bootstrap.servers": self.bootstrap_servers})
        topic_metadata = admin_client.list_topics(topic=topic, timeout=10)
        if topic not in topic_metadata.topics:
            raise ValueError(f"Topic {topic} does not exist.")
        return list(topic_metadata.topics[topic].partitions.keys())