#!/usr/bin/env python

import os
import subprocess
from datetime import datetime
from pathlib import Path

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        backup_db()


def backup_db():
    SECRETS = settings.SECRETS

    # Database credentials
    DB_HOST = "localhost"

    DB_NAME = SECRETS["PRODUCTION_DB_NAME"]
    DB_USER = SECRETS["PRODUCTION_DB_USER"]
    DB_PASSWORD = SECRETS["PRODUCTION_DB_PASSWORD"]

    AWS_BACKUPS = SECRETS["AWS"]["BACKUPS"]

    session = boto3.Session(
        aws_access_key_id=AWS_BACKUPS["ACCESS_KEY_ID"],
        aws_secret_access_key=AWS_BACKUPS["SECRET_ACCESS_KEY"],
        region_name=AWS_BACKUPS["REGION_NAME"],
    )

    ENV = os.environ.copy()
    ENV["PGPASSWORD"] = DB_PASSWORD
    ENV["PGHOST"] = DB_HOST

    OUTPUT_DIR = Path("/tmp")
    filename = f"db-cciw.django.{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.pgdump"
    full_path = OUTPUT_DIR / filename

    cmd = [
        "pg_dump",
        "-Fc",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-O",
        "-f",
        str(full_path),
    ]
    print(" ".join(cmd))
    subprocess.check_call(cmd, env=ENV)

    s3 = session.resource("s3")
    print("Uploading to S3")
    s3.Bucket(AWS_BACKUPS["BUCKET_NAME"]).put_object(Key="db/" + filename, Body=open(full_path, "rb"))

    full_path.unlink()
