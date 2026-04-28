import ipaddress
import re
import socket
import ssl
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Dict, Optional

USER_AGENT = "ATLAS-WebFetch/1.0"
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
MAX_RESPONSE_BYTES = 5_000_000


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.result: list[str] = []
        self.last_tag: Optional[str] = None
        self._skip = False  # inside script/style

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True
        if tag in {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.result.append("\n")
        self.last_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.result.append("\n")
        self.last_tag = None

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self.result.append(text + " ")

    def get_text(self) -> str:
        text = "".join(self.result)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def normalize_url(url: str) -> urllib.parse.ParseResult:
    url = url.strip()
    if not url:
        raise ValueError("URL must not be empty")
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL scheme must be http or https")
    if not parsed.netloc:
        raise ValueError("URL must include a host")
    return parsed


def is_private_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return any(ip in network for network in PRIVATE_NETWORKS)
    except ValueError:
        return False


def resolve_host(hostname: str) -> list[str]:
    try:
        addresses = []
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            ip = sockaddr[0]
            addresses.append(ip)
        return sorted(set(addresses))
    except socket.gaierror:
        return []


def validate_url(parsed: urllib.parse.ParseResult) -> None:
    host = parsed.hostname
    if host is None:
        raise ValueError("URL host is invalid")
    if host.lower() == "localhost":
        raise ValueError("Localhost access is not allowed")
    try:
        ip = ipaddress.ip_address(host)
        if is_private_address(host):
            raise ValueError("Private or local network addresses are not allowed")
    except ValueError:
        addresses = resolve_host(host)
        if not addresses:
            return
        for address in addresses:
            if is_private_address(address):
                raise ValueError(
                    "Resolved host points to a private or local network address"
                )


def fetch_url_content(url: str, timeout: int = 15) -> Dict[str, str]:
    parsed = normalize_url(url)
    validate_url(parsed)
    normalized_url = urllib.parse.urlunparse(parsed)
    request = urllib.request.Request(normalized_url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Response is too large")
        charset = response.headers.get_content_charset() or "utf-8"
        try:
            html = raw.decode(charset, errors="replace")
        except Exception:
            html = raw.decode("utf-8", errors="replace")
        return {
            "url": response.geturl(),
            "status": str(response.status),
            "reason": response.reason,
            "headers": dict(response.headers),
            "html": html,
        }


def extract_text_from_html(html: str, max_chars: int = 12000) -> str:
    extractor = TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    return text[:max_chars]


def check_internet(timeout: int = 5) -> bool:
    try:
        request = urllib.request.Request(
            "https://www.google.com",
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=timeout):
            return True
    except Exception:
        return False
