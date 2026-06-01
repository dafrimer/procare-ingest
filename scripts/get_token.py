#!/usr/bin/env python3
"""
Interactive script to obtain a Procare Online auth token.
Run with: python scripts/get_token.py
"""
import getpass
import json
import sys

try:
    import httpx
except ImportError:
    print("httpx is required: pip install httpx")
    sys.exit(1)

AUTH_URL = "https://online-auth.procareconnect.com/sessions/"


def main():
    print("=== Procare Token Extractor ===")
    print(f"Auth URL: {AUTH_URL}")
    print()

    email = input("Procare Email: ").strip()
    if not email:
        print("Email is required")
        sys.exit(1)

    password = getpass.getpass("Procare Password: ")
    if not password:
        print("Password is required")
        sys.exit(1)

    payload = {
        "email": email,
        "password": password,
        "role": "carer",
        "platform": "web",
        "preserve_sites": True,
    }

    print("\nAuthenticating...")
    try:
        resp = httpx.post(AUTH_URL, json=payload, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"Authentication failed: {e.response.status_code} {e.response.text}")
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Request error: {e}")
        sys.exit(1)

    data = resp.json()
    token = data.get("auth_token")
    if not token:
        print("No auth_token in response:")
        print(json.dumps(data, indent=2))
        sys.exit(1)

    sites = data.get("sites", [])
    user = data.get("user", {})

    print("\n=== Authentication Successful ===")
    print(f"User: {user.get('first_name', '')} {user.get('last_name', '')} ({user.get('email', '')})")
    print(f"\nAuth Token:\n{token}")
    print("\nSites:")
    for i, site in enumerate(sites, 1):
        print(f"  [{i}] ID: {site.get('id')} | Name: {site.get('name')} | Base URL: {site.get('base_url')}")

    if sites:
        first = sites[0]
        print(f"\n=== Recommended .env settings ===")
        print(f"PROCARE_AUTH_TOKEN={token}")
        print(f"PROCARE_SITE_URL={first.get('base_url', '')}")
        print(f"PROCARE_SITE_ID={first.get('id', '')}")
    else:
        print(f"\n=== Recommended .env settings ===")
        print(f"PROCARE_AUTH_TOKEN={token}")


if __name__ == "__main__":
    main()
