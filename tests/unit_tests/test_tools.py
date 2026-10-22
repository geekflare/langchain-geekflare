"""Unit tests with the HTTP layer mocked."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from geekflare_api.api.api_tool_api import ApiToolApi
from langchain_core.tools import ToolException

import langchain_geekflare
from langchain_geekflare import (
    GeekflareAPIWrapper,
    GeekflareDnsRecords,
    GeekflareScrape,
    GeekflareSearch,
    GeekflareUrlToPdf,
)
from langchain_geekflare.tools import _GeekflareTool


def _all_tools() -> List[type]:
    return [
        getattr(langchain_geekflare, name)
        for name in langchain_geekflare.__all__
        if isinstance(getattr(langchain_geekflare, name), type)
        and issubclass(getattr(langchain_geekflare, name), _GeekflareTool)
    ]


class _FakeApi(list):
    """Recorded requests, plus the response the fake API returns next."""

    def __init__(self) -> None:
        super().__init__()
        self.state: Dict[str, Any] = {
            "status": 200,
            "body": {"apiStatus": "success", "apiCode": 200, "data": {"ok": True}},
        }


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> _FakeApi:
    """Replace every ``*_without_preload_content`` call; record the requests."""
    calls = _FakeApi()

    for attr in dir(ApiToolApi):
        if not attr.endswith("_without_preload_content"):
            continue

        def fake(self: Any, *args: Any, _attr: str = attr, **kwargs: Any) -> Any:
            request = next(v for k, v in kwargs.items() if k.endswith("_dto"))
            calls.append({"method": _attr, "body": request.to_dict(), "kwargs": kwargs})
            return SimpleNamespace(
                status=calls.state["status"], data=json.dumps(calls.state["body"]).encode()
            )

        monkeypatch.setattr(ApiToolApi, attr, fake)

    return calls


def test_every_tool_has_unique_name() -> None:
    names = [cls(geekflare_api_key="k").name for cls in _all_tools()]
    assert len(names) == len(set(names)) == 15


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEEKFLARE_API_KEY", "env-key")
    tool = GeekflareSearch()
    assert tool.api_wrapper.geekflare_api_key.get_secret_value() == "env-key"


def test_explicit_api_key_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEEKFLARE_API_KEY", "env-key")
    tool = GeekflareSearch(geekflare_api_key="explicit")
    assert tool.api_wrapper.geekflare_api_key.get_secret_value() == "explicit"


def test_key_is_not_exposed_in_repr() -> None:
    tool = GeekflareSearch(geekflare_api_key="super-secret")
    assert "super-secret" not in repr(tool)


def test_search_body_and_result(fake_api: Any) -> None:
    tool = GeekflareSearch(geekflare_api_key="k")
    result = tool.invoke(
        {"query": "best crm", "serp": True, "city": "London,England,United Kingdom",
         "include_domains": ["g2.com"]}
    )
    assert result["data"] == {"ok": True}
    call = fake_api[-1]
    assert call["method"] == "search_without_preload_content"
    assert call["body"]["query"] == "best crm"
    assert call["body"]["serp"] is True
    assert call["body"]["city"] == "London,England,United Kingdom"
    assert call["body"]["includeDomains"] == ["g2.com"]


def test_scrape_aliases_and_template(fake_api: Any) -> None:
    tool = GeekflareScrape(geekflare_api_key="k")
    tool.invoke({"url": "https://example.com", "formats": ["markdown-llm"],
                 "render_js": True, "template": "product"})
    body = fake_api[-1]["body"]
    assert body["format"] == ["markdown-llm"]
    assert body["renderJS"] is True
    assert body["template"] == "product"
    assert body["extractionMode"] == "template"


def test_pdf_paper_format_alias(fake_api: Any) -> None:
    GeekflareUrlToPdf(geekflare_api_key="k").invoke(
        {"url": "https://example.com", "paper_format": "letter"}
    )
    assert fake_api[-1]["body"]["format"] == "letter"


def test_none_values_are_not_sent(fake_api: Any) -> None:
    GeekflareDnsRecords(geekflare_api_key="k").invoke({"url": "https://example.com"})
    assert fake_api[-1]["body"] == {"url": "https://example.com"}


def test_timeout_is_passed(fake_api: Any) -> None:
    GeekflareDnsRecords(
        api_wrapper=GeekflareAPIWrapper(geekflare_api_key="k", timeout=12)
    ).invoke({"url": "https://example.com"})
    assert fake_api[-1]["kwargs"]["_request_timeout"] == 12


def test_http_error_raises_tool_exception(fake_api: Any) -> None:
    fake_api.state["status"] = 401
    fake_api.state["body"] = {"apiCode": 401, "message": "Invalid x-api-key"}
    wrapper = GeekflareAPIWrapper(geekflare_api_key="bad")
    with pytest.raises(ToolException, match="Invalid x-api-key"):
        wrapper.call("search", {"query": "x"})


def test_tool_returns_error_text_instead_of_raising(fake_api: Any) -> None:
    fake_api.state["status"] = 401
    fake_api.state["body"] = {"apiCode": 401, "message": "Invalid x-api-key"}
    out = GeekflareSearch(geekflare_api_key="bad").invoke({"query": "x"})
    assert isinstance(out, str) and "Invalid x-api-key" in out


async def test_async_invoke(fake_api: Any) -> None:
    result = await GeekflareSearch(geekflare_api_key="k").ainvoke({"query": "x"})
    assert result["data"] == {"ok": True}
