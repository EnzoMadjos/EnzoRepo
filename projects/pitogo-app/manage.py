#!/usr/bin/env python3
"""
Management script for PITOGO app (quick init/seed helpers for Sprint 1).

Usage:
  python manage.py init-db
  python manage.py seed
  python manage.py create-sample
  python manage.py gen-keys
  python manage.py sign-patch <patch.zip>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import config
from db import get_session, init_db
from models import Base, CertificateType, Household, Resident


def seed_certificate_types(session):
    types = [
        ("CLEAR", "Barangay Clearance", "certs/clearance.html"),
        ("RESID", "Certificate of Residency", "docs/residency.html"),
        ("INDIG", "Certificate of Indigency", "docs/indigency.html"),
        ("BUSINESS", "Business Clearance", "certs/business_clearance.html"),
        ("COHAB", "Cohabitation Certificate", "certs/cohabitation.html"),
        ("SSS", "SSS Membership", "certs/sss_membership.html"),
    ]
    for code, name, template in types:
        existing = session.query(CertificateType).filter_by(code=code).first()
        if not existing:
            ct = CertificateType(code=code, name=name, template=template)
            session.add(ct)
    session.commit()


def create_admin_user():
    users_file = config.SECURE_DIR / "users.json"
    if users_file.exists():
        users = json.loads(users_file.read_text(encoding="utf-8"))
    else:
        users = {}
    if "admin" not in users:
        import hashlib

        def _hash(p):
            return hashlib.sha256(p.encode()).hexdigest()

        users["admin"] = {
            "password_hash": _hash("admin123"),
            "role": "admin",
            "display_name": "Administrator",
        }
        users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")
        print("Created default admin user in users.json (admin/admin123)")
    else:
        print("Admin user already exists in users.json")


def gen_keys():
    """Generate RSA-4096 keypair for patch signing.

    Writes:
      secure/patch_private.pem  — KEEP SECRET, sign patches with this
      secure/patch_public.pem   — deploy to every installed instance
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    priv_path = config.SECURE_DIR / "patch_private.pem"
    pub_path = config.SECURE_DIR / "patch_public.pem"

    if priv_path.exists() or pub_path.exists():
        print("Keys already exist:")
        if priv_path.exists():
            print(f"  {priv_path}")
        if pub_path.exists():
            print(f"  {pub_path}")
        ans = input("Overwrite? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return

    print("Generating RSA-4096 keypair…")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    priv_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    priv_path.chmod(0o600)
    pub_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"✓ Private key: {priv_path}  (chmod 600 — keep secret!)")
    print(f"✓ Public key:  {pub_path}  (deploy this to every installed instance)")


def sign_patch(zip_path: str):
    """Sign a patch.zip with the private key and write <zip>.sig beside it."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    priv_path = config.SECURE_DIR / "patch_private.pem"
    if not priv_path.exists():
        print(f"Private key not found at {priv_path}. Run: python manage.py gen-keys")
        sys.exit(1)

    p = Path(zip_path)
    if not p.exists():
        print(f"File not found: {p}")
        sys.exit(1)

    private_key = load_pem_private_key(priv_path.read_bytes(), password=None)
    data = p.read_bytes()
    sig = private_key.sign(
        data,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    sig_path = p.with_suffix(p.suffix + ".sig")
    sig_path.write_bytes(sig)
    print(f"✓ Signed: {p.name}")
    print(f"✓ Signature: {sig_path.name}  ({len(sig)} bytes)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["init-db", "seed", "create-sample", "gen-keys", "sign-patch"])
    parser.add_argument("args", nargs="*", help="Extra arguments (e.g. patch file for sign-patch)")
    args = parser.parse_args()
    if args.cmd == "init-db":
        init_db(Base)
        print("Initialized DB")
    elif args.cmd == "seed":
        session = get_session()
        seed_certificate_types(session)
        session.close()
        create_admin_user()
        print("Seeded certificate types and ensured admin user")
    elif args.cmd == "create-sample":
        session = get_session()
        h = Household(
            address_line="123 Main St",
            barangay="Pitogo",
            city="Pitogo City",
            zip_code="0000",
        )
        session.add(h)
        session.commit()
        r = Resident(first_name="Juan", last_name="Dela Cruz", household_id=h.id)
        session.add(r)
        session.commit()
        print("Created sample household and resident")
        session.close()
    elif args.cmd == "gen-keys":
        gen_keys()
    elif args.cmd == "sign-patch":
        if not args.args:
            print("Usage: python manage.py sign-patch <patch.zip>")
            sys.exit(1)
        sign_patch(args.args[0])


if __name__ == "__main__":
    main()
