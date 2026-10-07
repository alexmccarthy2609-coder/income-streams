"""Validate user-submitted URLs. The server fetches them, so internal/private
addresses must be refused (otherwise users could probe your own network)."""
import ipaddress
import socket
from urllib.parse import urlparse


class InvalidURL(ValueError):
    pass


def normalise(raw: str) -> str:
    raw = raw.strip()
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise InvalidURL("Enter a web address like https://example.com")
    if p.username or p.password:
        raise InvalidURL("URLs with credentials aren't allowed")
    return p._replace(fragment="").geturl()


def assert_public(url: str) -> None:
    host = urlparse(url).hostname
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise InvalidURL(f"Couldn't find the site '{host}'")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise InvalidURL("Private or internal addresses can't be monitored")
