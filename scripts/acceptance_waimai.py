#!/usr/bin/env python3
"""外卖商品只读验收：底层 WaimaiService + MCP 工具包装。"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastpospal.client import PospalClient  # noqa: E402
from fastpospal.mcp import mcp  # noqa: E402
from fastpospal.mcp.profile import ADVANCED_TOOL_TAG  # noqa: E402
from fastpospal.raw.waimai import WaimaiService  # noqa: E402

PASS, FAIL = "PASS", "FAIL"

EXPECTED_WAIMAI_MCP = {
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

REMOVED_WAIMAI_MCP = {
    "pospal_waimai_mapping_summary",
    "pospal_waimai_list_pospal_products",
    "pospal_waimai_list_mapped_products",
    "pospal_waimai_list_unmapped_platform_products",
    "pospal_waimai_list_unmapped_pospal_products",
}


class Report:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        self.results.append(
            {"name": name, "status": PASS if condition else FAIL, "detail": detail}
        )

    def print_report(self) -> None:
        p = sum(1 for r in self.results if r["status"] == PASS)
        f = sum(1 for r in self.results if r["status"] == FAIL)
        print("\n" + "=" * 72)
        print(f"外卖验收  PASS={p}  FAIL={f}")
        print("=" * 72)
        for r in self.results:
            icon = "✅" if r["status"] == PASS else "❌"
            detail = f" — {r['detail']}" if r["detail"] else ""
            print(f"{icon} {r['name']}{detail}")


def _accept_raw(report: Report, svc: WaimaiService) -> None:
    status = svc.shop_status()
    shops = status.get("shops") or []
    report.check("raw_shop_status", status.get("successed") is True, f"shops={len(shops)}")

    summary = svc.mapping_summary(source_type="MEITUAN_WAIMAI")
    report.check(
        "raw_mapping_summary",
        summary.get("successed") is True and "mappingCount" in summary,
        json.dumps(
            {
                "mappingCount": summary.get("mappingCount"),
                "notMappingCount": summary.get("notMappingCount"),
                "openNotMappingCount": summary.get("openNotMappingCount"),
            },
            ensure_ascii=False,
        ),
    )

    for name, fn in (
        ("raw_list_pospal", lambda: svc.list_pospal_products(page_size=5)),
        ("raw_list_mapped", lambda: svc.list_mapped_products(page_size=5)),
        ("raw_list_unmapped_platform", lambda: svc.list_unmapped_platform_products(page_size=5)),
        ("raw_list_unmapped_pospal", lambda: svc.list_unmapped_pospal_products(page_size=5)),
    ):
        data = fn()
        report.check(
            name,
            data.get("successed") is True,
            f"total={data.get('totalRecord')} page={len(data.get('products') or [])}",
        )

    fails = svc.list_mapping_failures(page_size=5)
    report.check(
        "raw_list_mapping_failures",
        fails.get("successed") is True,
        f"total={fails.get('totalRecord')}",
    )

    cats = svc.list_pos_categories()
    report.check(
        "raw_list_pos_categories",
        cats.get("successed") is True and len(cats.get("categories") or []) > 0,
        f"count={len(cats.get('categories') or [])}",
    )

    open_cats = svc.list_platform_categories(source_type="MEITUAN_WAIMAI")
    report.check(
        "raw_list_platform_categories",
        open_cats.get("successed") is True,
        f"count={len(open_cats.get('categories') or [])}",
    )

    mapped = svc.list_mapped_products(page_size=5)
    products = mapped.get("products") or []
    if products:
        sample = products[0]
        dish_id = str(sample.get("dishId") or "")
        product_uid = str(sample.get("productUid") or "")
        if dish_id:
            detail = svc.get_platform_product(dish_id=dish_id)
            report.check(
                "raw_get_platform_product",
                detail.get("successed") is True
                and bool((detail.get("product") or {}).get("dishId")),
                f"dishId={dish_id}",
            )
        else:
            report.check("raw_get_platform_product", False, "mapped sample missing dishId")
        if product_uid:
            detail2 = svc.get_mapped_product_details(product_uid=product_uid)
            report.check(
                "raw_get_mapped_product",
                detail2.get("successed") is True,
                f"productUid={product_uid}",
            )
        else:
            report.check("raw_get_mapped_product", False, "mapped sample missing productUid")
    else:
        report.check("raw_get_platform_product", False, "no mapped products")
        report.check("raw_get_mapped_product", False, "no mapped products")

    pull_guard = svc.pull_platform_products(confirm=False)
    report.check(
        "raw_pull_requires_confirm",
        pull_guard.get("successed") is False,
        str(pull_guard.get("error") or "")[:80],
    )


def _unwrap_tool_result(result: Any) -> Any:
    if hasattr(result, "data") and result.data is not None:
        return result.data
    if hasattr(result, "structured_content") and result.structured_content is not None:
        return result.structured_content
    if hasattr(result, "content"):
        texts = []
        for block in result.content or []:
            text = getattr(block, "text", None)
            if text:
                texts.append(text)
        if len(texts) == 1:
            try:
                return json.loads(texts[0])
            except json.JSONDecodeError:
                return {"_text": texts[0]}
        return {"_texts": texts}
    return result


async def _call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    try:
        result = await mcp.call_tool(name, arguments or {})
        return _unwrap_tool_result(result)
    except Exception as exc:  # noqa: BLE001 — 验收需要把工具错误当成数据
        return {"successed": False, "error": str(exc)}


async def _accept_mcp(report: Report) -> None:
    mcp.disable(tags={ADVANCED_TOOL_TAG})

    tools = await mcp.list_tools()
    names = {t.name for t in tools if t.name.startswith("pospal_waimai_")}
    report.check(
        "mcp_waimai_toolset",
        names == EXPECTED_WAIMAI_MCP,
        f"count={len(names)} missing={sorted(EXPECTED_WAIMAI_MCP - names)} "
        f"extra={sorted(names - EXPECTED_WAIMAI_MCP)}",
    )
    report.check(
        "mcp_removed_legacy_lists",
        REMOVED_WAIMAI_MCP.isdisjoint(names),
        f"still_present={sorted(REMOVED_WAIMAI_MCP & names)}",
    )

    status = await _call_tool(
        "pospal_waimai_shop_status",
        {"source_type": "MEITUAN_WAIMAI"},
    )
    summary = (status or {}).get("mappingSummary") or {}
    report.check(
        "mcp_shop_status_with_mapping_summary",
        bool(status.get("successed")) and "mappingCount" in summary,
        json.dumps(
            {
                "shops": len(status.get("shops") or []),
                "mappingCount": summary.get("mappingCount"),
                "notMappingCount": summary.get("notMappingCount"),
                "openNotMappingCount": summary.get("openNotMappingCount"),
            },
            ensure_ascii=False,
        ),
    )

    for status_name, mapping_status in (
        ("mcp_list_all", "all"),
        ("mcp_list_mapped", "mapped"),
        ("mcp_list_unmapped_platform", "unmapped_platform"),
        ("mcp_list_unmapped_pospal", "unmapped_pospal"),
    ):
        data = await _call_tool(
            "pospal_waimai_list_products",
            {
                "mapping_status": mapping_status,
                "source_type": "MEITUAN_WAIMAI",
                "page_size": 5,
            },
        )
        report.check(
            status_name,
            bool(data.get("successed")),
            f"total={data.get('totalRecord')} page={len(data.get('products') or [])}",
        )

    fails = await _call_tool("pospal_waimai_list_mapping_failures", {"page_size": 5})
    report.check(
        "mcp_list_mapping_failures",
        bool(fails.get("successed")),
        f"total={fails.get('totalRecord')}",
    )

    cats = await _call_tool(
        "pospal_waimai_list_categories",
        {"source_type": "MEITUAN_WAIMAI"},
    )
    report.check(
        "mcp_list_categories",
        bool(cats.get("successed")),
        f"pos={len(cats.get('posCategories') or [])} "
        f"platform={len(cats.get('platformCategories') or [])}",
    )

    pull_guard = await _call_tool(
        "pospal_waimai_pull_products",
        {"source_type": "MEITUAN_WAIMAI", "confirm": False},
    )
    ok = isinstance(pull_guard, dict) and (
        pull_guard.get("successed") is False or bool(pull_guard.get("error"))
    )
    report.check("mcp_pull_requires_confirm", ok, str(pull_guard)[:120])


def main() -> int:
    account = os.environ.get("POSPAL_ACCOUNT", "")
    password = os.environ.get("POSPAL_PASSWORD", "")
    if not account or not password:
        print("缺少 POSPAL_ACCOUNT / POSPAL_PASSWORD")
        return 1

    report = Report()
    client = PospalClient(account=account, password=password)
    client.login()
    svc = WaimaiService(client)

    report.check("area_parsed", bool(client.area), f"area={client.area}")
    report.check(
        "waimai_host",
        client.waimai_host.startswith("https://waimai-api"),
        client.waimai_host,
    )

    _accept_raw(report, svc)
    asyncio.run(_accept_mcp(report))

    report.print_report()
    failed = sum(1 for r in report.results if r["status"] == FAIL)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
