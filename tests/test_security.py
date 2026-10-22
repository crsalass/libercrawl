import pytest
from app.security import validate_engine_url, validate_target


def test_local_engine_only():
    assert validate_engine_url("http://127.0.0.1:3002/") == "http://127.0.0.1:3002"
    assert validate_engine_url("http://[::1]:3002") == "http://[::1]:3002"
    for bad in ["https://service.example.com", "http://example.com:3002", "http://127.0.0.1:3002/path",
                "http://user:pass@localhost:3002", "https://localhost:3002"]:
        with pytest.raises(ValueError):
            validate_engine_url(bad)


@pytest.mark.parametrize("bad", ["file:///etc/passwd", "http://127.0.0.1", "http://10.0.0.2",
    "http://localhost", "http://metadata.google.internal", "http://example.local",
    "http://user:pass@example.org", "https://example.org:8080", "https://example.org#secret",
    "ftp://example.org", "https://example.org@localhost/path", "http://[::1]"])
def test_block_private_targets(bad):
    with pytest.raises(ValueError):
        validate_target(bad, resolve_dns=False)


def test_public_syntax_allowed():
    assert validate_target("https://www.example.org/product?a=1", resolve_dns=False) == "https://www.example.org/product?a=1"
