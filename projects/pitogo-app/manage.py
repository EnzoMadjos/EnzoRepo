#!/usr/bin/env python3
"""
Management script for PITOGO app (quick init/seed helpers for Sprint 1).

Usage:
  python manage.py init-db
  python manage.py seed
  python manage.py create-sample
"""

from __future__ import annotations

import argparse
import json
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["init-db", "seed", "create-sample"])
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


if __name__ == "__main__":
    main()
