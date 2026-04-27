"""
SQLAlchemy models for PITOGO app (Sprint 1 core models).

Includes: Resident, Household, User, CertificateType, CertificateIssue, Attachment.
"""
from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    Text,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class Resident(Base):
    __tablename__ = "residents"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    household_id = Column(String(36), ForeignKey("households.id"), nullable=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    birthdate = Column(Date)
    contact_number = Column(String(32))
    national_id = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # single-direction relationship to Household using Resident.household_id as FK
    household = relationship("Household", foreign_keys=[household_id])

    __table_args__ = (Index("ix_resident_name", "last_name", "first_name"),)


class Household(Base):
    __tablename__ = "households"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    head_resident_id = Column(String(36), ForeignKey("residents.id"), nullable=True)
    address_line = Column(Text, nullable=False)
    barangay = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    zip_code = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # relationship to Resident (members) omitted to avoid ambiguous foreign-key
    # mappings when both sides declare explicit foreign keys. Resident.household
    # provides a link back to Household and can be queried instead.


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(32), nullable=False, default="clerk")
    active = Column(Boolean, default=True)
    node_id = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class CertificateType(Base):
    __tablename__ = "certificate_types"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    template = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CertificateIssue(Base):
    __tablename__ = "certificate_issues"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    control_number = Column(String(64), unique=True, nullable=False, index=True)
    certificate_type_id = Column(String(36), ForeignKey("certificate_types.id"), nullable=False)
    resident_id = Column(String(36), ForeignKey("residents.id"), nullable=True)
    household_id = Column(String(36), ForeignKey("households.id"), nullable=True)
    # store the issuing username (simpler for Sprint 1) rather than FK to users.id
    issued_by = Column(String(128), nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow)
    pdf_path = Column(String(512))
    status = Column(String(32), default="issued")
    node_id = Column(String(36), nullable=False, index=True)
    local_seq = Column(Integer, nullable=False, default=1)
    meta = Column(JSON)


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    owner_type = Column(String(32), nullable=False)
    owner_id = Column(String(36), nullable=False)
    original_filename = Column(String(255))
    stored_path = Column(String(512), nullable=False)
    mime_type = Column(String(128))
    size = Column(Integer)
    checksum = Column(String(128))
    uploaded_by = Column(String(36))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

