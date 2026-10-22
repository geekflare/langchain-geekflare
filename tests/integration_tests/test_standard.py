"""LangChain standard integration tests. Need a real ``GEEKFLARE_API_KEY``."""

import os
from typing import Type

import pytest
from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_geekflare import GeekflareDnsRecords, GeekflareSearch

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEEKFLARE_API_KEY"), reason="GEEKFLARE_API_KEY not set"
)


class TestGeekflareSearchIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[GeekflareSearch]:
        return GeekflareSearch

    @property
    def tool_constructor_params(self) -> dict:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"query": "geekflare api", "limit": 3}


class TestGeekflareDnsRecordsIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[GeekflareDnsRecords]:
        return GeekflareDnsRecords

    @property
    def tool_constructor_params(self) -> dict:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"url": "https://example.com", "types": ["A"]}
