import pytest
from tecnomata_iptv.diagnostics import classify_error, failure_message, text_value


def test_mpv_event_reason_is_bytes():
    assert text_value(b"error") == "error"
    assert text_value("error") == "error"


@pytest.mark.parametrize("message, expected", [
    ("HTTP error 403 Forbidden https://secret.example/live/user/password/1.ts", {"failure": "http", "http_status": 403}),
    (b"HTTP error 404 Not Found", {"failure": "http", "http_status": 404}),
    ("TLS certificate verify failed for private server", {"failure": "tls"}),
    ("Connection refused: private-server", {"failure": "network"}),
    ("Unable to open decoder for h264", {"failure": "codec"}),
])
def test_logs_produce_only_safe_codes(message, expected):
    assert classify_error(message) == expected
    assert "secret" not in failure_message(expected)
    assert "password" not in failure_message(expected)


def test_unrecognized_log_is_discarded():
    assert classify_error("Opening https://user:password@example.invalid/private") is None
