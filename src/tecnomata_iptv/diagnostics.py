"""Convertir logs privados del motor a códigos permitidos; nunca devolver el texto."""
import re

from .i18n import t


def text_value(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def classify_error(message):
    message = text_value(message).lower()
    match = re.search(r"(?:http error|http[^\n]*?error|server returned)\s*[: ]*([45]\d\d)\b", message)
    if match:
        return {"failure": "http", "http_status": int(match[1])}
    for terms, code in [(("certificate", "tls", "ssl"), "tls"),
                        (("connection refused", "connection timed out", "network is unreachable"), "network"),
                        (("failed to resolve", "name or service not known"), "dns"),
                        (("decoder", "unsupported codec", "no video or audio streams"), "codec")]:
        if any(term in message for term in terms):
            return {"failure": code}
    return None


def failure_message(diagnostic):
    code = diagnostic.get("failure")
    status = diagnostic.get("http_status")
    if code == "http":
        if status in (401, 403):
            return t('error_http_401_403', status=status)
        if status == 404:
            return t('error_http_404')
        return t('error_http_other', status=status)
    return {"tls": t('error_tls'), "network": t('error_network'), "dns": t('error_dns'),
            "codec": t('error_codec')}.get(code, t('error_playback_generic'))
