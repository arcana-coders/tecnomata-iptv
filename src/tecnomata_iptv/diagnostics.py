"""Convertir logs privados del motor a códigos permitidos; nunca devolver el texto."""
import re


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
            return f"El servidor rechazó la reproducción (HTTP {status}). La cuenta puede cargar listas y aun así rechazar el video."
        if status == 404:
            return "El servidor no encontró el video (HTTP 404). Hay que revisar la ruta y el formato del proveedor."
        return f"El servidor no pudo entregar el video (HTTP {status})."
    return {"tls": "Falló la conexión segura con el servidor de video (TLS).",
            "network": "No se pudo conectar con el servidor de video.",
            "dns": "No se pudo resolver el servidor de video.",
            "codec": "El motor no pudo decodificar este contenido."}.get(code,
            "No se pudo reproducir este contenido. Prueba otro canal o revisa la conexión.")
