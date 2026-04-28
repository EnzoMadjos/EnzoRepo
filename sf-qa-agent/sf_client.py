from __future__ import annotations

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ReadTimeout
from simple_salesforce import Salesforce, SFType
from simple_salesforce.exceptions import SalesforceError
from urllib3.util.retry import Retry


class _TimeoutSession(requests.Session):
    def __init__(self, timeout: int = 120) -> None:
        super().__init__()
        self._timeout = timeout

        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.mount("https://", adapter)
        self.mount("http://", adapter)

    def request(self, *args, **kwargs):
        # Replace None explicitly — simple_salesforce passes timeout=None which
        # setdefault would not override.
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self._timeout
        return super().request(*args, **kwargs)


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
        self._session = _TimeoutSession(timeout=120)

    def _call_with_retry(self, func, *args, **kwargs):
        """Retry transient Salesforce read timeouts before failing the step."""
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except ReadTimeout as exc:
                last_exc = exc
                if attempt == 2:
                    break
                time.sleep(1.5 * (attempt + 1))
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Salesforce request failed before executing")

    def _connect(self) -> Salesforce:
        if self._sf is not None:
            return self._sf
        # If we already have a valid access token from login, use it directly
        # to avoid a second SOAP/OAuth round-trip (which would fail on newer orgs)
        if self._access_token and self._instance_url:
            self._sf = Salesforce(
                instance_url=self._instance_url,
                session_id=self._access_token,
                session=self._session,
            )
        else:
            self._sf = Salesforce(
                username=self._username,
                password=self._password,
                security_token=self._security_token,
                consumer_key=self._consumer_key,
                consumer_secret=self._consumer_secret,
                domain=self._domain,
                session=self._session,
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
        result = self._call_with_retry(sf_obj.create, fields)
        record_id: str = result["id"]
        return {"id": record_id, "url": f"{self.instance_url}/{record_id}"}

    def update_record(
        self, object_type: str, record_id: str, fields: dict[str, Any]
    ) -> dict[str, str]:
        """Update an existing record. Returns {"id": "...", "url": "..."}."""
        sf = self._connect()
        self._call_with_retry(getattr(sf, object_type).update, record_id, fields)
        return {"id": record_id, "url": f"{self.instance_url}/{record_id}"}

    def delete_record(self, object_type: str, record_id: str) -> None:
        """Permanently delete a record."""
        sf = self._connect()
        self._call_with_retry(getattr(sf, object_type).delete, record_id)

    def clone_record(
        self, object_type: str, record_id: str, overrides: dict[str, Any]
    ) -> dict[str, str]:
        """Clone a record — fetches fields, strips read-only ones, creates a copy with optional overrides."""
        sf = self._connect()
        sf_obj: SFType = getattr(sf, object_type)
        source = self._call_with_retry(sf_obj.get, record_id)
        meta = self._call_with_retry(sf_obj.describe)
        createable = {f["name"] for f in meta["fields"] if f["createable"]}
        fields: dict[str, Any] = {
            k: v for k, v in source.items() if k in createable and v is not None
        }
        fields.update(overrides)
        result = self._call_with_retry(sf_obj.create, fields)
        new_id: str = result["id"]
        return {"id": new_id, "url": f"{self.instance_url}/{new_id}"}

    def query(self, soql: str) -> list[dict[str, Any]]:
        sf = self._connect()
        result = self._call_with_retry(sf.query_all, soql)
        return result.get("records", [])

    def describe(self, object_type: str) -> dict[str, Any]:
        sf = self._connect()
        sf_obj: SFType = getattr(sf, object_type)
        return self._call_with_retry(sf_obj.describe)

    def describe_all_objects(self) -> list[dict[str, str]]:
        """Lightweight list of all sObjects in the org: [{name, label, queryable}]."""
        sf = self._connect()
        result = self._call_with_retry(sf.describe)
        return [
            {"name": o["name"], "label": o["label"], "queryable": o["queryable"]}
            for o in result.get("sobjects", [])
        ]

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
