"""Manually notify IndexNow about canonical public URLs after deployment."""
import argparse
import sys

import httpx

from app.api.public_site import indexnow_payload
from app.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", action="store_true", help="Actually notify IndexNow (default is dry run)")
    args = parser.parse_args()
    payload = indexnow_payload(Settings())
    if not args.submit:
        print("Dry run: canonical URLs (key omitted):")
        print("\n".join(payload["urlList"]))
        return
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        verification = client.get(payload["keyLocation"])
        if verification.status_code != 200 or verification.text.strip() != payload["key"]:
            raise ValueError("Deploy the configured ownership file before submitting")
        response = client.post("https://api.indexnow.org/indexnow", json=payload)
        if response.status_code not in (200, 202):
            raise ValueError(f"IndexNow returned HTTP {response.status_code}")
        print(f"IndexNow HTTP {response.status_code}: accepted; indexing is not guaranteed.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, httpx.HTTPError):
        # HTTP exception URLs can contain the verification key: never dump them.
        print("IndexNow submission failed. Check HTTPS origin, key deployment and network access.", file=sys.stderr)
        sys.exit(1)
