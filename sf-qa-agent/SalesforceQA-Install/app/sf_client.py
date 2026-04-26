from __future__ import annotations

from typing import Any

from simple_salesforce import Salesforce, SFType
from simple_salesforce.exceptions import SalesforceError


class SalesforceClient:
    def __init__(
        self,
        username: str,
        password: str,
        security_token: str,
        domain: str = "login",
        consumer_key: str = "",
        consumer_secret: str = "",
        access_token: str = "",
        instance_url: str = "",
    ) -> None:
        self._username = username
        self._password = password
        self._security_token = security_token
        self._domain = domain
        self._consumer_key = consumer_key or None
        self._consumer_secret = consumer_secret or None
        self._access_token = access_token
        self._instance_url = instance_url
        self._sf: Salesforce | None = None

    def _connect(self) -> Salesforce:
        if self._sf is not None:
            return self._sf
        # If we already have a valid access token from login, use it directly
        # to avoid a second SOAP/OAuth round-trip (which would fail on newer orgs)
        if self._access_token and self._instance_url:
            self._sf = Salesforce(
                instance_url=self._instance_url,
                session_id=self._access_token,
            )
        else:
            self._sf = Salesforce(
                username=self._username,
                password=self._password,
                security_token=self._security_token,
                consumer_key=self._consumer_key,
                consumer_secret=self._consumer_secret,
                domain=self._domain,
            )
        return self._sf

    @property
    def instance_url(self) -> str:
        return self._connect().base_url.split("/services")[0]

    @property
    def org_id(self) -> str:
        return self._connect().sf_org_id or ""

    def create_record(self, object_type: str, fields: dict[str, Any]) -> dict[str, str]:
        """Create a record and return {"id": "...", "url": "..."}."""
        sf = self._connect()
        sf_obj: SFType = getattr(sf, object_type)
        result = sf_obj.create(fields)
        record_id: str = result["id"]
        record_url = f"{self.instance_url}/{record_id}"
        return {"id": record_id, "url": record_url}

    def query(self, soql: str) -> list[dict[str, Any]]:
        sf = self._connect()
        result = sf.query_all(soql)
        return result.get("records", [])

    def describe(self, object_type: str) -> dict[str, Any]:
        sf = self._connect()
        sf_obj: SFType = getattr(sf, object_type)
        return sf_obj.describe()

    @classmethod
    def from_session(cls, session) -> "SalesforceClient":
        """Build a client from an auth.SessionData object."""
        return cls(
            username=session.username,
            password=session.sf_password,
            security_token=session.sf_security_token,
            domain=session.sf_domain,
            consumer_key=session.consumer_key,
            consumer_secret=session.consumer_secret,
            access_token=session.access_token,
            instance_url=session.instance_url,
        )
