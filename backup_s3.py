#!/usr/bin/env python

import json
import os
import os.path
import subprocess
from datetime import datetime

import boto3

THISDIR = os.path.dirname(os.path.abspath(__file__))


def main():
    secrets = json.load(open(os.path.join(THISDIR, 'config', 'secrets.json')))

    # Database credentials
    DB_HOST = "localhost"

    DB_NAME = secrets['PRODUCTION_DB_NAME']
    DB_USER = secrets['PRODUCTION_DB_USER']
    DB_PASSWORD = secrets['PRODUCTION_DB_PASSWORD']

    session = boto3.Session(aws_access_key_id=secrets['aws_access_key_id'],
                            aws_secret_access_key=secrets['aws_secret_access_key'],
                            region_name=secrets['aws_region_name'])

    ENV = os.environ.copy()
    ENV['PGPASSWORD'] = DB_PASSWORD
    ENV['PGHOST'] = DB_HOST

    OUTPUT_DIR = "/tmp"
    filename = "db-cciw.django.{0}.pgdump".format(
        datetime.now().strftime("%Y-%m-%d_%H.%M.%S"))
    full_path = os.path.join(OUTPUT_DIR, filename)

    cmd = [
        "pg_dump",
        "-Fc",
        "-U", DB_USER,
        "-O", "-o",
        "-f", full_path,
        DB_NAME]
    print(' '.join(cmd))
    subprocess.check_call(cmd, env=ENV)

    s3 = session.resource('s3')
    print("Uploading to S3")
    s3.Bucket('cciw-backups').put_object(Key="db/" + filename, Body=open(full_path, "rb"))

    os.unlink(full_path)


if __name__ == '__main__':
    main()
