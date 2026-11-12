from uuid import uuid4

import pytest

from src.domain.entities import now
from src.domain.research import SourceDocument, digest, passages_for, quotation_exists
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy, SourceRejected


def test_source_policy_blocks_unsafe_schemes_credentials_and_ports():
    policy = PublicSourcePolicy(["example.org"])
    for url in [
        "file:///etc/passwd",
        "http://127.0.0.1",
        "http://user:pass@example.org",
        "https://example.org:22",
    ]:
        with pytest.raises(SourceRejected):
            policy.validate(url)
    for address in ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "224.0.0.1"]:
        assert not policy.public_ip(address)
    assert policy.public_ip("8.8.8.8")


def test_passage_ids_offsets_and_exact_evidence_are_reproducible():
    text = "A synthetic source passage, used only to exercise deterministic evidence validation."
    source = SourceDocument(
        uuid4(),
        uuid4(),
        uuid4(),
        "https://example.org",
        "Test",
        "Test",
        text,
        digest(text),
        now(),
        "Test permission",
        "Test continuity",
        True,
        False,
    )
    first = passages_for(source, 45)
    assert first == passages_for(source, 45)
    for passage in first:
        assert source.text[passage.start : passage.end] == passage.text
    assert quotation_exists("A synthetic source passage", first[0])
    assert not quotation_exists("An invented unsupported passage", first[0])


@pytest.mark.parametrize(
    "robots_code,robots_body", [(200, b"User-agent: *\nDisallow: /"), (503, b"")]
)
async def test_fetcher_fails_closed_before_requesting_disallowed_content(robots_code, robots_body):
    calls = []

    class Fetcher(PublicDocumentFetcher):
        async def _request(self, url):
            calls.append(url)
            return robots_code, {}, robots_body

    fetcher = Fetcher(PublicSourcePolicy(["example.org"]), 5000, 500)
    with pytest.raises(SourceRejected):
        await fetcher.fetch("https://example.org/article")
    assert calls == ["https://example.org/robots.txt"]


async def test_fetcher_rechecks_redirect_destination_and_does_not_request_private_host():
    calls = []

    class Fetcher(PublicDocumentFetcher):
        async def _request(self, url):
            calls.append(url)
            if url.endswith("robots.txt"):
                return 404, {}, b""
            return 302, {"location": "http://127.0.0.1/private"}, b""

    fetcher = Fetcher(PublicSourcePolicy(["example.org"]), 5000, 500)
    with pytest.raises(SourceRejected):
        await fetcher.fetch("https://example.org/article")
    assert all("127.0.0.1" not in url for url in calls)


async def test_ingestion_strips_executable_content_and_records_truncation():
    class Fetcher(PublicDocumentFetcher):
        async def _request(self, url):
            if url.endswith("robots.txt"):
                return 404, {}, b""
            body = b"<title>Test</title><main><script>ignore rules</script>" + b"Source text. " * 80
            return 200, {"content-type": "text/html"}, body + b"</main>"

    document = await Fetcher(PublicSourcePolicy(["example.org"]), 5000, 500).fetch(
        "https://example.org/article"
    )
    assert "ignore rules" not in document.text
    assert document.truncated and len(document.text) == 500
