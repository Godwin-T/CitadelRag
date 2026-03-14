from __future__ import annotations

import tempfile
from urllib.parse import urlparse
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core import settings


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
    )


def resolve_to_local_path(storage_uri: str) -> str:
    if storage_uri.startswith("file://"):
        return storage_uri.replace("file://", "", 1)
    if storage_uri.startswith("s3://"):
        parsed = urlparse(storage_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        suffix = Path(key).suffix
        try:
            client = _s3_client()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                client.download_fileobj(bucket, key, tmp)
                return tmp.name
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Failed to download from S3: {storage_uri}") from exc
    return storage_uri
