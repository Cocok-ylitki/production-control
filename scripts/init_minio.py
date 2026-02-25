"""
Инициализация бакетов MinIO.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import get_settings
from src.storage.minio_service import get_minio_client


def initialize_minio_buckets() -> None:
    settings = get_settings()
    client = get_minio_client()
    buckets = settings.minio_buckets
    for bucket_name in buckets.keys():
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Created bucket: {bucket_name}")
        else:
            print(f"Bucket already exists: {bucket_name}")


if __name__ == "__main__":
    initialize_minio_buckets()
