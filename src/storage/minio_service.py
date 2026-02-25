import os
from datetime import datetime, timedelta
from io import BytesIO
from typing import BinaryIO, Iterator

from minio import Minio

from src.core.config import get_settings

settings = get_settings()

CONTENT_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".json": "application/json",
}


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


class MinIOService:
    """Сервис для работы с MinIO."""

    def __init__(self):
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def upload_file(
        self,
        bucket: str,
        file_path: str,
        object_name: str | None = None,
        expires_days: int = 7,
    ) -> str:
        """
        Загрузить файл в MinIO.
        Returns:
            Pre-signed URL для скачивания.
        """
        if object_name is None:
            object_name = os.path.basename(file_path)
        content_type = self._get_content_type(file_path)
        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=content_type,
        )
        url = self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days),
        )
        return url

    def upload_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> int:
        """Загрузить bytes/stream в MinIO. Возвращает размер в байтах."""
        if isinstance(data, bytes):
            size = len(data)
            data = BytesIO(data)
        else:
            size = data.getbuffer().nbytes if hasattr(data, "getbuffer") else len(data.read())
            if hasattr(data, "seek"):
                data.seek(0)
        self.client.put_object(bucket, object_name, data, length=size, content_type=content_type)
        return size

    def download_file(self, bucket: str, object_name: str, file_path: str) -> None:
        """Скачать файл из MinIO на диск."""
        self.client.fget_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
        )

    def download_bytes(self, bucket: str, object_name: str) -> bytes:
        """Скачать объект в память. Возвращает содержимое."""
        response = self.client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()

    def delete_file(self, bucket: str, object_name: str) -> None:
        """Удалить файл."""
        self.client.remove_object(bucket, object_name)

    def list_files(
        self,
        bucket: str,
        prefix: str | None = None,
    ) -> Iterator:
        """Список файлов в бакете."""
        return self.client.list_objects(
            bucket_name=bucket,
            prefix=prefix or "",
            recursive=True,
        )

    def _get_content_type(self, file_path: str) -> str:
        """Определить Content-Type по расширению."""
        ext = os.path.splitext(file_path)[1].lower()
        return CONTENT_TYPES.get(ext, "application/octet-stream")

    def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expires_days: int = 7,
    ) -> str:
        """Pre-signed URL для скачивания."""
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days),
        )



def upload_report(
    file_name: str,
    data: bytes | BinaryIO,
    content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
) -> tuple[str, int]:
    """Загружает файл отчёта в MinIO. Возвращает (url, size)."""
    svc = MinIOService()
    bucket = settings.minio_bucket_reports
    object_name = f"{settings.minio_reports_prefix}/{file_name}"
    size = svc.upload_bytes(bucket, object_name, data, content_type=content_type)
    url = svc.get_presigned_url(bucket, object_name)
    return url, size


def upload_import_file(file_name: str, data: bytes | BinaryIO) -> str:
    """Загружает файл импорта в MinIO. Возвращает object key (bucket/name) для задачи."""
    svc = MinIOService()
    bucket = settings.minio_bucket_imports
    object_name = f"{settings.minio_imports_prefix}/{file_name}"
    svc.upload_bytes(bucket, object_name, data)
    return f"{bucket}/{object_name}"


def upload_export(
    file_name: str,
    data: bytes | BinaryIO,
    content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
) -> tuple[str, int]:
    """Загружает файл экспорта в MinIO. Возвращает (url, size)."""
    svc = MinIOService()
    bucket = settings.minio_bucket_exports
    object_name = f"{settings.minio_exports_prefix}/{file_name}"
    size = svc.upload_bytes(bucket, object_name, data, content_type=content_type)
    url = svc.get_presigned_url(bucket, object_name)
    return url, size


def download_file(object_key: str) -> bytes:
    """Скачивает файл из MinIO по ключу (bucket/prefix/name). Возвращает содержимое."""
    client = get_minio_client()
    parts = object_key.split("/", 1)
    bucket = parts[0]
    object_name = parts[1] if len(parts) > 1 else object_key
    response = client.get_object(bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()


def list_objects_older_than(
    bucket: str,
    prefix: str = "",
    days: int = 30,
) -> list[tuple[str, str]]:
    """Возвращает список (bucket, object_name) объектов старше days дней."""
    client = get_minio_client()
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = []
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        if not obj.last_modified:
            continue
        mod = obj.last_modified.replace(tzinfo=None) if obj.last_modified.tzinfo else obj.last_modified
        if mod < cutoff:
            result.append((bucket, obj.name))
    return result


def delete_objects(objects: list[tuple[str, str]]) -> None:
    """Удаляет объекты из MinIO. objects: list of (bucket, object_name)."""
    client = get_minio_client()
    for bucket, name in objects:
        client.remove_object(bucket, name)


def get_presigned_url(bucket: str, object_name: str, expires: timedelta | None = None) -> str:
    if expires is None:
        expires = timedelta(days=7)
    client = get_minio_client()
    return client.presigned_get_object(bucket, object_name, expires=expires)
