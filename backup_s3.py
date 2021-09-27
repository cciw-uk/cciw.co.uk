#!/usr/bin/env python

import json
import os
import os.path
import subprocess
from datetime import datetime

import boto3

THISDIR = os.path.dirname(os.path.abspath(__file__))


def main():
    secrets = json.load(open(os.path.join(THISDIR, "config", "secrets.json")))

    # Database credentials
    DB_HOST = "localhost"

    DB_NAME = secrets["PRODUCTION_DB_NAME"]
    DB_USER = secrets["PRODUCTION_DB_USER"]
    DB_PASSWORD = secrets["PRODUCTION_DB_PASSWORD"]
    AWS_BACKUPS = secrets["AWS"]["BACKUPS"]

    session = boto3.Session(
        aws_access_key_id=AWS_BACKUPS["ACCESS_KEY_ID"],
        aws_secret_access_key=AWS_BACKUPS["SECRET_ACCESS_KEY"],
        region_name=AWS_BACKUPS["REGION_NAME"],
    )

    ENV = os.environ.copy()
    ENV["PGPASSWORD"] = DB_PASSWORD
    ENV["PGHOST"] = DB_HOST

    OUTPUT_DIR = "/tmp"
    filename = f"db-cciw.django.{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.pgdump"
    full_path = os.path.join(OUTPUT_DIR, filename)

    cmd = [
        "pg_dump",
        "-Fc",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-O",
        "-f",
        full_path,
    ]
    print(" ".join(cmd))
    subprocess.check_call(cmd, env=ENV)

    s3 = session.resource("s3")
    print("Uploading to S3")
    s3.Bucket(AWS_BACKUPS["BUCKET_NAME"]).put_object(Key="db/" + filename, Body=open(full_path, "rb"))

    os.unlink(full_path)


if __name__ == "__main__":
    main()
