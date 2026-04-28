"""Pydantic schemas for top certificate types (draft).

These are minimal schemas to be expanded after Council mapping.
"""

from typing import Optional

from pydantic import BaseModel


class ClearanceSchema(BaseModel):
    full_name: str
    address: str
    purpose: str
    issued_by: Optional[str] = None


class ResidencySchema(BaseModel):
    full_name: str
    address: str
    years: Optional[str] = None
    purpose: Optional[str] = None


class IndigencySchema(BaseModel):
    full_name: str
    address: str
    purpose: Optional[str] = None


class BusinessClearanceSchema(BaseModel):
    business_name: str
    owner_name: str
    address: str
    purpose: Optional[str] = None


class CohabitationSchema(BaseModel):
    partner_a: str
    partner_b: str
    address: str
    duration: Optional[str] = None


class SSSMembershipSchema(BaseModel):
    full_name: str
    sss_no: Optional[str] = None
    membership_type: Optional[str] = None
