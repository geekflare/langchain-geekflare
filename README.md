# langchain-geekflare

LangChain tools for the [Geekflare API](https://geekflare.com): live web search (including full Google SERP results), scraping public pages to Markdown or structured JSON, page metadata, brand data, screenshots, URL-to-PDF, and website diagnostics (uptime, DNS, DNSSEC, TLS, redirects, broken links, load time, mixed content, Lighthouse).

Built on the official Python SDK, [`geekflare-api`](https://pypi.org/project/geekflare-api/).

## Installation

```bash
pip install -U langchain-geekflare
```

## Setup

Get an API key at [dash.geekflare.com](https://dash.geekflare.com) (free tier available) and set it as an environment variable:

```bash
export GEEKFLARE_API_KEY="your-api-key"
```

You can also pass it directly: `GeekflareSearch(geekflare_api_key="...")`.

## Tools

| Tool | Name | What it does |
| --- | --- | --- |
| `GeekflareSearch` | `geekflare_search` | Web, news, or image search; `serp=True` returns the full Google results page (AI Overview, People Also Ask) by country or city |
| `GeekflareScrape` | `geekflare_scrape` | Page content as Markdown, text, HTML, or JSON; `template="product"` or `"contact"` for structured data |
| `GeekflareMetaScrape` | `geekflare_meta_scrape` | Title, description, canonical, Open Graph, Twitter Card tags |
| `GeekflareBrand` | `geekflare_brand` | Logos, brand colors, fonts, social profiles |
| `GeekflareScreenshot` | `geekflare_screenshot` | Viewport, full-page, or element screenshot (hosted image URL) |
| `GeekflareUrlToPdf` | `geekflare_url_to_pdf` | Page as PDF (hosted file URL) |
| `GeekflareSiteStatus` | `geekflare_site_status` | Is the site up, and its HTTP status |
| `GeekflareDnsRecords` | `geekflare_dns_records` | A, AAAA, CNAME, MX, NS, SOA, TXT, CAA, SRV records |
| `GeekflareDnsSec` | `geekflare_dnssec` | DNSSEC configured and validating |
| `GeekflareTlsScan` | `geekflare_tls_scan` | Certificate details and expiry, supported TLS versions |
| `GeekflareRedirectCheck` | `geekflare_redirect_check` | Redirect chain with status codes |
| `GeekflareBrokenLinks` | `geekflare_broken_links` | Broken links on a page |
| `GeekflareLoadTime` | `geekflare_load_time` | Page load timing |
| `GeekflareMixedContent` | `geekflare_mixed_content` | HTTP resources on HTTPS pages |
| `GeekflareLighthouse` | `geekflare_lighthouse` | Lighthouse performance, SEO, accessibility, best-practices scores |

Each tool returns the API's JSON response as a dict. API errors (invalid key, no credits, unreachable site) come back to the agent as a short error message instead of raising.

## Usage

### Call a tool directly

```python
from langchain_geekflare import GeekflareSearch, GeekflareScrape

search = GeekflareSearch()
results = search.invoke({"query": "latest stable python release", "limit": 5})

scrape = GeekflareScrape()
page = scrape.invoke({"url": "https://example.com", "formats": ["markdown"]})
```

Google results page for a city:

```python
search.invoke({
    "query": "best project management software",
    "serp": True,
    "city": "London,England,United Kingdom",
})
```

### Use with an agent

```python
from langchain.agents import create_agent
from langchain_geekflare import (
    GeekflareSearch,
    GeekflareScrape,
    GeekflareTlsScan,
    GeekflareDnsRecords,
)

agent = create_agent(
    model="anthropic:claude-sonnet-5-5",
    tools=[GeekflareSearch(), GeekflareScrape(), GeekflareTlsScan(), GeekflareDnsRecords()],
)

agent.invoke({"messages": [{"role": "user", "content": "Is the TLS setup on example.com healthy?"}]})
```

Async is supported on every tool: `await tool.ainvoke({...})`.

## Notes

- Every call spends Geekflare credits on your account; see [pricing](https://geekflare.com/pricing/).
- Use the tools for publicly accessible pages only.
- The tools send the URLs, queries, and options you pass to `api.geekflare.com`. See the [Geekflare privacy policy](https://geekflare.com/privacy/).

## Development

```bash
uv venv --python 3.12 && uv pip install -e . --group test
pytest --disable-socket --allow-unix-socket tests/unit_tests
GEEKFLARE_API_KEY=... pytest tests/integration_tests
```

## Links

- API docs: <https://docs.geekflare.com>
- Python SDK: <https://github.com/geekflare/geekflare-api-python>
- MCP server: <https://docs.geekflare.com/mcp/overview>
