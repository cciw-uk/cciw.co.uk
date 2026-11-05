#!/usr/bin/env python3
"""
Create a dummy config/secrets.json suitable for local development, for use
when you don't have access to the real one on the production server
(normally fetched by `fab initial-dev-setup`).

Usage:  python3 scripts/create_dummy_secrets.py [--force]
"""

import argparse
import json
import secrets
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "config" / "secrets.json"


def make_secrets() -> dict:
    emails = ["webmaster@example.com"]
    data: dict = {
        "EMAIL_RECIPIENTS": {
            k: emails
            for k in [
                "WEBMASTER",
                "BOOKING_FORMS",
                "BOOKING_SECRETARY",
                "GENERAL_CONTACT",
                "SECRETARY",
                "VOLUNTEERING",
                "FINANCE",
            ]
        },
        "EMAIL_ENCRYPTION_PUBLIC_KEYS": [],
        "EXTERNAL_DBS_OFFICER": {
            "name": "DBS Officer",
            "email": "dbs@example.com",
            "organisation": "Example Org",
            "organisation_long": "Example Organisation Ltd",
        },
        "SMTP_HOST": "localhost",
        "SMTP_PORT": 25,
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "SMTP_USE_TLS": False,
        "AWS": {"INCOMING_MAIL": {}, "CONFIG": {}, "BACKUPS": {}},
    }
    for prefix in ["DEV", "STAGING", "PRODUCTION"]:
        data.update(
            {
                f"{prefix}_SECRET_KEY": secrets.token_urlsafe(50),
                f"{prefix}_DB_NAME": "cciw_dev",
                f"{prefix}_DB_USER": "cciw_dev",
                f"{prefix}_DB_PASSWORD": "cciw_dev",
                f"{prefix}_DB_PORT": "5432",
                f"{prefix}_MAILCHIMP_API_KEY": "dummy",
                f"{prefix}_MAILCHIMP_NEWSLETTER_LIST_ID": "dummy",
                f"{prefix}_MAILCHIMP_URL_BASE": "https://localhost.invalid/",
                f"{prefix}_PAYPAL_RECEIVER_EMAIL": "paypal@example.com",
                f"{prefix}_SENTRY_CONFIG": {"dsn": ""},
            }
        )
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    args = parser.parse_args()
    if TARGET.exists() and not args.force:
        raise SystemExit(f"{TARGET} already exists, use --force to overwrite")
    TARGET.write_text(json.dumps(make_secrets(), indent=2))
    print(f"Wrote {TARGET}")


if __name__ == "__main__":
    main()
