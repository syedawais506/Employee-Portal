from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeWebhookURLError(ValueError):
    pass


def _is_unsafe_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_outbound_webhook_url(url: str) -> None:
    """Blocks SSRF via a company-configurable outbound webhook URL (Slack
    incoming webhook / Teams connector): a company Admin controls this value,
    but the Celery worker that delivers it sits on the same internal Docker
    network as Postgres/Redis/MinIO, so an unvalidated URL would let a
    malicious or compromised Admin probe/attack internal infrastructure
    (or, on a cloud host, the instance metadata endpoint) rather than an
    actual chat webhook. Re-run at delivery time too (not just at save time)
    to close the DNS-rebinding gap — a hostname can resolve differently
    between when it's saved and when it's actually used.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise UnsafeWebhookURLError("Webhook URL must use https://")
    if not parsed.hostname:
        raise UnsafeWebhookURLError("Webhook URL must include a host")

    try:
        addr_infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise UnsafeWebhookURLError("Webhook host could not be resolved") from exc

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        if _is_unsafe_ip(ip_str):
            raise UnsafeWebhookURLError("Webhook URL resolves to a private/internal address, which isn't allowed")
