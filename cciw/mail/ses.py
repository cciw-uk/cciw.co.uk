import io

import boto3
from django.conf import settings


def download_ses_message_from_s3(message_id):
    AWS_INCOMING_MAIL = settings.AWS_INCOMING_MAIL
    session = boto3.Session(aws_access_key_id=AWS_INCOMING_MAIL['ACCESS_KEY_ID'],
                            aws_secret_access_key=AWS_INCOMING_MAIL['SECRET_ACCESS_KEY'],
                            region_name=AWS_INCOMING_MAIL['REGION_NAME'])

    s3 = session.resource('s3')
    bucket = s3.Bucket(name=AWS_INCOMING_MAIL['BUCKET_NAME'])
    store = io.BytesIO()
    bucket.download_fileobj(message_id, store)
    return store.getvalue()
