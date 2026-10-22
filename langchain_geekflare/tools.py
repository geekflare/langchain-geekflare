"""LangChain tools for the Geekflare API."""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Literal, Optional, Type

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_geekflare._api import GeekflareAPIWrapper

Device = Literal["desktop", "mobile"]


def _to_camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)


class _GeekflareTool(BaseTool):
    """Shared plumbing: auth, argument mapping, sync and async calls."""

    api_wrapper: GeekflareAPIWrapper = Field(default_factory=GeekflareAPIWrapper)
    handle_tool_error: bool = True

    endpoint: ClassVar[str]
    # Input fields whose API name isn't the plain camelCase of the field name.
    field_aliases: ClassVar[Dict[str, str]] = {}
    # Values always sent with the request.
    fixed_params: ClassVar[Dict[str, Any]] = {}

    def __init__(self, **kwargs: Any) -> None:
        if "geekflare_api_key" in kwargs:
            kwargs["api_wrapper"] = GeekflareAPIWrapper(
                geekflare_api_key=kwargs.pop("geekflare_api_key")
            )
        super().__init__(**kwargs)

    def _body(self, **kwargs: Any) -> Dict[str, Any]:
        body = dict(self.fixed_params)
        for key, value in kwargs.items():
            if value is None:
                continue
            body[self.field_aliases.get(key, _to_camel(key))] = value
        return body

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.api_wrapper.call(self.endpoint, self._body(**kwargs))

    async def _arun(
        self,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return await self.api_wrapper.acall(self.endpoint, self._body(**kwargs))


# ── Search and content ────────────────────────────────────────────────────────


class GeekflareSearchInput(BaseModel):
    query: str = Field(description="Search query.")
    limit: Optional[int] = Field(
        default=None, ge=1, le=100, description="Number of results (default 10)."
    )
    source: Optional[Literal["web", "news", "images"]] = Field(
        default=None, description="Search source (default web)."
    )
    time: Optional[str] = Field(
        default=None,
        description="Recency filter: any, h, d, w, m, y, or with a count such as d7.",
    )
    location: Optional[str] = Field(
        default=None, description="Country code (ISO alpha-2) for results, e.g. us."
    )
    city: Optional[str] = Field(
        default=None,
        description=(
            "City for localized results, e.g. 'London,England,United Kingdom'. "
            "Takes priority over location."
        ),
    )
    include_domains: Optional[List[str]] = Field(
        default=None, description="Only return results from these domains."
    )
    exclude_domains: Optional[List[str]] = Field(
        default=None, description="Exclude results from these domains."
    )
    serp: Optional[bool] = Field(
        default=None,
        description=(
            "Return the full Google results page: organic results, AI Overview, "
            "People Also Ask, related searches."
        ),
    )
    scrape: Optional[bool] = Field(
        default=None,
        description="Also fetch the page content of the top results. Ignored with serp.",
    )
    grounded_answer: Optional[bool] = Field(
        default=None,
        description="Add an AI answer grounded in the results. Ignored with serp.",
    )


class GeekflareSearch(_GeekflareTool):
    """Search the web, news, or images with Geekflare, or get the full Google SERP.

    Setup:
        Install ``langchain-geekflare`` and set ``GEEKFLARE_API_KEY``.

    Instantiate:
        .. code-block:: python

            from langchain_geekflare import GeekflareSearch

            tool = GeekflareSearch()

    Invoke:
        .. code-block:: python

            tool.invoke({"query": "latest python release", "limit": 5})
    """

    name: str = "geekflare_search"
    description: str = (
        "Search the live web, news, or images and return titles, URLs, and snippets. "
        "Set serp=true to get the full Google results page (rankings, AI Overview, "
        "People Also Ask) for a country or city. Use for current information and "
        "for finding sources; cite the returned URLs."
    )
    args_schema: Type[BaseModel] = GeekflareSearchInput
    endpoint: ClassVar[str] = "search"


class GeekflareScrapeInput(BaseModel):
    url: str = Field(description="Full URL of the public page to scrape.")
    formats: Optional[
        List[
            Literal[
                "markdown", "markdown-llm", "html", "html-llm", "text", "text-llm", "json"
            ]
        ]
    ] = Field(
        default=None,
        description="Output format(s), up to 3 (default markdown). *-llm variants strip boilerplate.",
    )
    render_js: Optional[bool] = Field(
        default=None,
        description="Force JavaScript rendering on or off. Omit to decide automatically.",
    )
    wait_time: Optional[float] = Field(
        default=None, ge=0, description="Seconds to wait after load before capturing."
    )
    device: Optional[Device] = Field(default=None, description="Device to emulate.")
    template: Optional[Literal["product", "contact"]] = Field(
        default=None,
        description=(
            "Return structured JSON with a ready-made template: product (title, price, "
            "availability, images, ratings) or contact (emails, phones, socials)."
        ),
    )


class GeekflareScrape(_GeekflareTool):
    """Scrape a public web page into Markdown, text, HTML, or structured JSON."""

    name: str = "geekflare_scrape"
    description: str = (
        "Fetch a public web page and return its content as clean Markdown (default), "
        "text, HTML, or JSON. Use template=product or template=contact for structured "
        "data. Only for publicly accessible pages."
    )
    args_schema: Type[BaseModel] = GeekflareScrapeInput
    endpoint: ClassVar[str] = "web_scrape"
    field_aliases: ClassVar[Dict[str, str]] = {"formats": "format", "render_js": "renderJS"}

    def _body(self, **kwargs: Any) -> Dict[str, Any]:
        body = super()._body(**kwargs)
        if "template" in body:
            body["extractionMode"] = "template"
        return body


class GeekflareMetaScrapeInput(BaseModel):
    url: str = Field(description="Full URL of the page.")
    render_js: Optional[bool] = Field(
        default=None, description="Render JavaScript before reading tags (default true)."
    )


class GeekflareMetaScrape(_GeekflareTool):
    """Read a page's title, description, canonical, Open Graph and Twitter Card tags."""

    name: str = "geekflare_meta_scrape"
    description: str = (
        "Get a page's metadata only: title, description, canonical URL, Open Graph "
        "and Twitter Card tags. Cheaper than a full scrape."
    )
    args_schema: Type[BaseModel] = GeekflareMetaScrapeInput
    endpoint: ClassVar[str] = "meta_scrape"
    field_aliases: ClassVar[Dict[str, str]] = {"render_js": "renderJS"}


class GeekflareBrandInput(BaseModel):
    url: str = Field(description="Website URL or domain, e.g. https://stripe.com.")
    mode: Optional[Literal["standard", "enriched"]] = Field(
        default=None,
        description="enriched adds company intelligence (default standard).",
    )


class GeekflareBrand(_GeekflareTool):
    """Get a website's brand identity: name, logos, colors, fonts, social profiles."""

    name: str = "geekflare_brand"
    description: str = (
        "Get a company's brand identity from its website: name, logos, brand colors, "
        "fonts, and social profiles. Fields the site doesn't publish are omitted."
    )
    args_schema: Type[BaseModel] = GeekflareBrandInput
    endpoint: ClassVar[str] = "brand"


class GeekflareScreenshotInput(BaseModel):
    url: str = Field(description="Full URL of the page.")
    full_page: Optional[bool] = Field(
        default=None, description="Capture the whole page instead of the viewport."
    )
    device: Optional[Device] = Field(default=None, description="Device to emulate.")
    type: Optional[Literal["png", "jpeg", "webp"]] = Field(
        default=None, description="Image format (default png)."
    )
    selector: Optional[str] = Field(
        default=None, description="CSS selector of a single element to capture."
    )
    theme: Optional[Literal["light", "dark", "auto"]] = Field(
        default=None, description="Color scheme to render."
    )


class GeekflareScreenshot(_GeekflareTool):
    """Capture a screenshot of a web page and return a hosted image URL."""

    name: str = "geekflare_screenshot"
    description: str = (
        "Take a screenshot of a web page (viewport, full page, or one element) and "
        "return a hosted image URL."
    )
    args_schema: Type[BaseModel] = GeekflareScreenshotInput
    endpoint: ClassVar[str] = "screenshot"


class GeekflareUrlToPdfInput(BaseModel):
    url: str = Field(description="Full URL of the page.")
    paper_format: Optional[
        Literal["a4", "letter", "legal", "a0", "a1", "a2", "a3", "a5", "a6"]
    ] = Field(default=None, description="Paper size (default a4).")
    orientation: Optional[Literal["portrait", "landscape"]] = Field(
        default=None, description="Page orientation (default portrait)."
    )


class GeekflareUrlToPdf(_GeekflareTool):
    """Render a web page as a PDF and return a hosted file URL."""

    name: str = "geekflare_url_to_pdf"
    description: str = "Convert a web page to a PDF and return a hosted download URL."
    args_schema: Type[BaseModel] = GeekflareUrlToPdfInput
    endpoint: ClassVar[str] = "url2_pdf"
    field_aliases: ClassVar[Dict[str, str]] = {"paper_format": "format"}


# ── Website diagnostics ──────────────────────────────────────────────────────


class GeekflareUrlInput(BaseModel):
    url: str = Field(description="Website URL or domain, e.g. https://example.com.")


class GeekflareUrlRedirectInput(GeekflareUrlInput):
    follow_redirect: Optional[bool] = Field(
        default=None, description="Follow redirects before checking (default false)."
    )


class GeekflareSiteStatus(_GeekflareTool):
    """Check whether a website is up and what status code it returns."""

    name: str = "geekflare_site_status"
    description: str = "Check whether a website is up or down and return its HTTP status."
    args_schema: Type[BaseModel] = GeekflareUrlRedirectInput
    endpoint: ClassVar[str] = "site_status"


class GeekflareDnsRecordsInput(GeekflareUrlInput):
    types: Optional[
        List[Literal["A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT", "CAA", "SRV"]]
    ] = Field(default=None, description="Record types to return (default all).")


class GeekflareDnsRecords(_GeekflareTool):
    """Look up a domain's DNS records."""

    name: str = "geekflare_dns_records"
    description: str = "Look up DNS records (A, AAAA, CNAME, MX, NS, SOA, TXT, CAA, SRV) for a domain."
    args_schema: Type[BaseModel] = GeekflareDnsRecordsInput
    endpoint: ClassVar[str] = "dns_record"


class GeekflareDnsSec(_GeekflareTool):
    """Check whether DNSSEC is configured and validating for a domain."""

    name: str = "geekflare_dnssec"
    description: str = "Check whether DNSSEC is enabled and validating for a domain."
    args_schema: Type[BaseModel] = GeekflareUrlInput
    endpoint: ClassVar[str] = "dns_sec"


class GeekflareTlsScan(_GeekflareTool):
    """Inspect a domain's TLS/SSL certificate and supported protocol versions."""

    name: str = "geekflare_tls_scan"
    description: str = (
        "Inspect a domain's TLS/SSL setup: certificate details and expiry, and which "
        "protocol versions (SSLv2 to TLS 1.3) are supported."
    )
    args_schema: Type[BaseModel] = GeekflareUrlInput
    endpoint: ClassVar[str] = "tls_scan"


class GeekflareRedirectCheck(_GeekflareTool):
    """Trace the redirect chain of a URL."""

    name: str = "geekflare_redirect_check"
    description: str = "Trace every redirect hop of a URL with status codes."
    args_schema: Type[BaseModel] = GeekflareUrlInput
    endpoint: ClassVar[str] = "redirect_check"


class GeekflareBrokenLinks(_GeekflareTool):
    """Find broken links on a web page."""

    name: str = "geekflare_broken_links"
    description: str = "Find broken links on a web page."
    args_schema: Type[BaseModel] = GeekflareUrlRedirectInput
    endpoint: ClassVar[str] = "broken_link"


class GeekflareLoadTime(_GeekflareTool):
    """Measure how long a page takes to load."""

    name: str = "geekflare_load_time"
    description: str = "Measure a page's load time, including DNS, connect, TLS, and first byte."
    args_schema: Type[BaseModel] = GeekflareUrlRedirectInput
    endpoint: ClassVar[str] = "load_time"


class GeekflareMixedContent(_GeekflareTool):
    """Find HTTP resources loaded on an HTTPS page."""

    name: str = "geekflare_mixed_content"
    description: str = "Find insecure HTTP resources loaded on an HTTPS page."
    args_schema: Type[BaseModel] = GeekflareUrlRedirectInput
    endpoint: ClassVar[str] = "mixed_content"


class GeekflareLighthouseInput(GeekflareUrlInput):
    device: Optional[Device] = Field(
        default=None, description="Audit as desktop or mobile (default desktop)."
    )


class GeekflareLighthouse(_GeekflareTool):
    """Run a Google Lighthouse audit (performance, SEO, accessibility, best practices)."""

    name: str = "geekflare_lighthouse"
    description: str = (
        "Run a Google Lighthouse audit and return performance, SEO, accessibility, "
        "and best-practices scores. Slow: can take a minute or more."
    )
    args_schema: Type[BaseModel] = GeekflareLighthouseInput
    endpoint: ClassVar[str] = "lighthouse"
