"""LangChain standard unit tests for a representative set of Geekflare tools."""

from typing import Type

from langchain_tests.unit_tests import ToolsUnitTests

from langchain_geekflare import GeekflareDnsRecords, GeekflareScrape, GeekflareSearch


class TestGeekflareSearchUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[GeekflareSearch]:
        return GeekflareSearch

    @property
    def tool_constructor_params(self) -> dict:
        return {"geekflare_api_key": "test-key"}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"query": "latest python release", "limit": 5}

    @property
    def init_from_env_params(self) -> tuple:
        return {"GEEKFLARE_API_KEY": "env-key"}, {}, {}


class TestGeekflareScrapeUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[GeekflareScrape]:
        return GeekflareScrape

    @property
    def tool_constructor_params(self) -> dict:
        return {"geekflare_api_key": "test-key"}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"url": "https://example.com", "formats": ["markdown"]}


class TestGeekflareDnsRecordsUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[GeekflareDnsRecords]:
        return GeekflareDnsRecords

    @property
    def tool_constructor_params(self) -> dict:
        return {"geekflare_api_key": "test-key"}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"url": "https://example.com", "types": ["A", "MX"]}
