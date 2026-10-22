"""Thin wrapper around the official Geekflare Python SDK (``geekflare-api``)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Tuple

import geekflare_api
from geekflare_api import models
from geekflare_api.api.api_tool_api import ApiToolApi
from langchain_core.tools import ToolException
from langchain_core.utils import secret_from_env
from pydantic import BaseModel, ConfigDict, Field, SecretStr

DEFAULT_BASE_URL = "https://api.geekflare.com"
DEFAULT_TIMEOUT = 180.0

# endpoint -> (ApiToolApi method prefix, request model, request kwarg name)
_ENDPOINTS: Dict[str, Tuple[str, type, str]] = {
    "search": ("search", models.SearchRequestDto, "search_request_dto"),
    "web_scrape": ("web_scrape", models.WebScrapeDto, "web_scrape_dto"),
    "meta_scrape": ("meta_scrape", models.MetaScrapeDto, "meta_scrape_dto"),
    "brand": ("brand", models.BrandDto, "brand_dto"),
    "screenshot": ("screenshot", models.ScreenshotDto, "screenshot_dto"),
    "url2_pdf": ("url2_pdf", models.Url2PdfDto, "url2_pdf_dto"),
    "site_status": ("site_status", models.SiteStatusDto, "site_status_dto"),
    "dns_record": ("dns_record", models.DnsRecordDto, "dns_record_dto"),
    "dns_sec": ("dns_sec", models.DnsSecDto, "dns_sec_dto"),
    "tls_scan": ("tls_scan", models.TlsScanDto, "tls_scan_dto"),
    "redirect_check": ("redirect_check", models.RedirectCheckDto, "redirect_check_dto"),
    "broken_link": ("broken_link", models.BrokenLinkDto, "broken_link_dto"),
    "load_time": ("load_time", models.LoadTimeDto, "load_time_dto"),
    "mixed_content": ("mixed_content", models.MixedContentDto, "mixed_content_dto"),
    "lighthouse": ("lighthouse", models.LighthouseDto, "lighthouse_dto"),
}


class GeekflareAPIWrapper(BaseModel):
    """Calls Geekflare API endpoints and returns the parsed JSON response.

    The API key is read from the ``GEEKFLARE_API_KEY`` environment variable
    unless passed explicitly.
    """

    geekflare_api_key: SecretStr = Field(
        default_factory=secret_from_env("GEEKFLARE_API_KEY")
    )
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT

    model_config = ConfigDict(extra="forbid")

    def _api(self) -> Tuple[geekflare_api.ApiClient, ApiToolApi]:
        configuration = geekflare_api.Configuration(host=self.base_url)
        configuration.api_key["x-api-key"] = self.geekflare_api_key.get_secret_value()
        client = geekflare_api.ApiClient(configuration)
        return client, ApiToolApi(client)

    def call(self, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Call ``endpoint`` with a camelCase JSON ``body``."""
        method_name, request_model, kwarg = _ENDPOINTS[endpoint]
        try:
            request = request_model.from_dict(body)
        except Exception as e:  # pydantic validation error from the SDK model
            raise ToolException(f"Invalid arguments for Geekflare {endpoint}: {e}") from e

        client, api = self._api()
        try:
            method = getattr(api, f"{method_name}_without_preload_content")
            response = method(**{kwarg: request}, _request_timeout=self.timeout)
            status = response.status
            raw = response.data
        except Exception as e:  # network errors, timeouts
            raise ToolException(f"Geekflare {endpoint} request failed: {e}") from e
        finally:
            client.rest_client.pool_manager.clear()

        try:
            data = json.loads(raw)
        except ValueError:
            data = {"message": raw.decode("utf-8", errors="replace")}

        if status >= 400 or (isinstance(data, dict) and data.get("apiStatus") == "failure"):
            message = data.get("message") if isinstance(data, dict) else None
            raise ToolException(
                f"Geekflare {endpoint} returned HTTP {status}: {message or data}"
            )
        return data

    async def acall(self, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of :meth:`call` (runs the SDK in a worker thread)."""
        return await asyncio.to_thread(self.call, endpoint, body)
