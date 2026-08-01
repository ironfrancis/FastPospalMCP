"""MCP Server 注册与工具说明测试（离线，不依赖银豹账号）。"""

from __future__ import annotations

import asyncio

import pytest

from fastpospal.mcp import mcp
from fastpospal.mcp.instance import MCP_INSTRUCTIONS
from fastpospal.mcp.profile import ADVANCED_ONLY_TOOLS, ADVANCED_TOOL_TAG

# 物理注册的全部工具（含 advanced）；default profile 会隐藏 ADVANCED_ONLY_TOOLS
REGISTERED_TOOLS = {
    "pospal_session_info",
    "pospal_login",
    "pospal_list_categories",
    "pospal_create_category",
    "pospal_update_category",
    "pospal_delete_categories",
    "pospal_list_products",
    "pospal_get_product",
    "pospal_find_product_by_barcode",
    "pospal_create_product",
    "pospal_update_product",
    "pospal_delete_product",
    "pospal_find_customer",
    "pospal_list_customers",
    "pospal_get_customer_extras",
    "pospal_create_customer",
    "pospal_update_customer",
    "pospal_delete_customer",
    "pospal_list_stock",
    "pospal_stock_change_history",
    "pospal_list_stock_flows",
    "pospal_set_product_stock_limit",
    "pospal_list_suppliers",
    "pospal_create_supplier",
    "pospal_business_summary",
    "pospal_recharge_summary",
    "pospal_list_recharge_logs",
    "pospal_product_sale_summary",
    "pospal_list_eshop_orders",
    "pospal_list_product_purchases",
    "pospal_sem_find_products",
    "pospal_sem_check_product_stock",
    "pospal_sem_query_category_sales",
    "pospal_sem_get_store_sales_summary",
    "pospal_sem_query_sales_detail",
    "pospal_sem_query_stock_flows",
    "pospal_sem_list_products_admin",
    "pospal_sem_analyze_restock_needs",
    "pospal_waimai_shop_status",
    "pospal_waimai_list_products",
    "pospal_waimai_list_mapping_failures",
    "pospal_waimai_get_platform_product",
    "pospal_waimai_get_mapped_product",
    "pospal_waimai_list_categories",
    "pospal_waimai_bind_product",
    "pospal_waimai_unbind_product",
    "pospal_waimai_pull_products",
    "pospal_waimai_set_shelf",
    "pospal_waimai_save_platform_product",
}

REMOVED_TOOLS = {
    "pospal_product_summary",
    "pospal_list_tickets",
    "pospal_openapi_status",
    "pospal_waimai_mapping_summary",
    "pospal_waimai_list_pospal_products",
    "pospal_waimai_list_mapped_products",
    "pospal_waimai_list_unmapped_platform_products",
    "pospal_waimai_list_unmapped_pospal_products",
}

DEFAULT_TOOLS = REGISTERED_TOOLS - ADVANCED_ONLY_TOOLS


def _tool_map() -> dict[str, object]:
    tools = asyncio.run(mcp.list_tools())
    return {t.name: t for t in tools}


@pytest.fixture(autouse=True)
def _reset_default_profile():
    """每个用例前后回到 default（隐藏 advanced）。"""
    mcp.disable(tags={ADVANCED_TOOL_TAG})
    yield
    mcp.disable(tags={ADVANCED_TOOL_TAG})


def test_default_profile_exposes_slim_toolset():
    names = set(_tool_map())
    assert names == DEFAULT_TOOLS
    assert ADVANCED_ONLY_TOOLS.isdisjoint(names)
    assert REMOVED_TOOLS.isdisjoint(names)


def test_advanced_profile_exposes_all_registered_tools():
    mcp.enable(tags={ADVANCED_TOOL_TAG})
    names = set(_tool_map())
    assert names == REGISTERED_TOOLS
    assert ADVANCED_ONLY_TOOLS.issubset(names)


def test_registered_count_after_cleanup():
    assert len(REGISTERED_TOOLS) == 49
    assert len(DEFAULT_TOOLS) == 42
    assert len(ADVANCED_ONLY_TOOLS) == 7


def test_instructions_include_routing_guide():
    assert "pospal_sem_find_products" in MCP_INSTRUCTIONS
    assert "pospal_sem_get_store_sales_summary" in MCP_INSTRUCTIONS
    assert "YYYY-MM-DD" in MCP_INSTRUCTIONS
    assert "pospal_waimai_shop_status" in MCP_INSTRUCTIONS
    assert "pospal_waimai_list_products" in MCP_INSTRUCTIONS
    assert "POSPAL_MCP_PROFILE" in MCP_INSTRUCTIONS
    assert "pospal_waimai_mapping_summary" not in MCP_INSTRUCTIONS
    assert "pospal_list_tickets" not in MCP_INSTRUCTIONS


def test_key_tools_have_descriptions():
    tools = _tool_map()
    sem_sales = tools["pospal_sem_get_store_sales_summary"]
    assert sem_sales.description
    assert "营业" in sem_sales.description or "销售" in sem_sales.description

    sem = tools["pospal_sem_find_products"]
    assert sem.description
    assert "推荐" in sem.description or "名称" in sem.description

    waimai_list = tools["pospal_waimai_list_products"]
    assert waimai_list.description
    assert "mapping_status" in (waimai_list.description or "")


def test_waimai_list_products_exposes_mapping_status():
    tools = _tool_map()
    schema = tools["pospal_waimai_list_products"].parameters
    props = schema.get("properties", {})
    assert "mapping_status" in props


def test_shop_status_includes_source_type_param():
    tools = _tool_map()
    schema = tools["pospal_waimai_shop_status"].parameters
    props = schema.get("properties", {})
    assert "source_type" in props


def test_semantic_tools_expose_shop_names_param():
    tools = _tool_map()
    schema = tools["pospal_sem_find_products"].parameters
    props = schema.get("properties", {})
    assert "shop_names" in props
    shop_desc = props["shop_names"].get("description", "")
    assert shop_desc
