"""MCP 工具暴露 profile：default（精简）/ advanced（含 raw 重复能力）。"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastmcp import FastMCP

McpProfile = Literal["default", "advanced"]

# 仅 advanced 暴露：与 sem_* 或日常运维重叠、易误选的 raw / 诊断工具
ADVANCED_TOOL_TAG = "advanced"

ADVANCED_ONLY_TOOLS = frozenset(
    {
        "pospal_login",
        "pospal_business_summary",
        "pospal_product_sale_summary",
        "pospal_list_products",
        "pospal_find_product_by_barcode",
        "pospal_list_stock",
        "pospal_list_stock_flows",
    }
)


def get_mcp_profile() -> McpProfile:
    raw = (os.environ.get("POSPAL_MCP_PROFILE") or "default").strip().lower()
    if raw in ("advanced", "full", "all"):
        return "advanced"
    return "default"


def apply_tool_profile(mcp: FastMCP) -> McpProfile:
    """按 POSPAL_MCP_PROFILE 隐藏/显示 advanced 标签工具。可重复调用。"""
    profile = get_mcp_profile()
    if profile == "advanced":
        mcp.enable(tags={ADVANCED_TOOL_TAG})
    else:
        mcp.disable(tags={ADVANCED_TOOL_TAG})
    return profile
