from __future__ import annotations

import os
import uuid
from typing import Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from api.core.config import get_settings


def _s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
    )


def _ensure_local_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _ensure_s3_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except (BotoCoreError, ClientError):
        try:
            client.create_bucket(Bucket=bucket)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Failed to create bucket: {bucket}") from exc


def ensure_bucket_ready() -> None:
    settings = get_settings()
    if settings.storage_backend.lower() != "s3":
        return
    client = _s3_client()
    _ensure_s3_bucket(client, settings.s3_bucket)


def save_file(contents: bytes, filename: str) -> str:
    settings = get_settings()
    key = f"uploads/{uuid.uuid4()}-{filename}"

    if settings.storage_backend.lower() == "s3":
        try:
            client = _s3_client()
            _ensure_s3_bucket(client, settings.s3_bucket)
            client.put_object(Bucket=settings.s3_bucket, Key=key, Body=contents)
            return f"s3://{settings.s3_bucket}/{key}"
        except (BotoCoreError, ClientError) as e:
            # Fall back to local storage
            print(f"S3 upload failed: {e}. Falling back to local storage.")
            pass

    _ensure_local_dir(settings.local_upload_dir)
    file_path = os.path.join(settings.local_upload_dir, f"{uuid.uuid4()}-{filename}")
    with open(file_path, "wb") as f:
        f.write(contents)
    return f"file://{os.path.abspath(file_path)}"
