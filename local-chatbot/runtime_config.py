from settings import WEB_ACCESS_ALLOWLIST, WEB_FETCH_ENABLED

web_fetch_enabled = WEB_FETCH_ENABLED
web_access_allowlist = list(WEB_ACCESS_ALLOWLIST)


def set_web_fetch_enabled(enabled: bool) -> None:
    global web_fetch_enabled
    web_fetch_enabled = enabled


def set_web_access_allowlist(allowlist: list[str]) -> None:
    global web_access_allowlist
    web_access_allowlist = allowlist
