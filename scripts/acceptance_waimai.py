#!/usr/bin/env python3
"""外卖商品 MCP 只读验收（不写平台数据）。"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastpospal.client import PospalClient  # noqa: E402
from fastpospal.raw.waimai import WaimaiService  # noqa: E402

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


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

    status = svc.shop_status()
    shops = status.get("shops") or []
    report.check("shop_status", status.get("successed") is True, f"shops={len(shops)}")

    summary = svc.mapping_summary(source_type="MEITUAN_WAIMAI")
    report.check(
        "mapping_summary",
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

    pospal = svc.list_pospal_products(page_size=5)
    report.check(
        "list_pospal_products",
        pospal.get("successed") is True and pospal.get("totalRecord", 0) > 0,
        f"total={pospal.get('totalRecord')} page={len(pospal.get('products') or [])}",
    )

    mapped = svc.list_mapped_products(page_size=5)
    report.check(
        "list_mapped_products",
        mapped.get("successed") is True,
        f"total={mapped.get('totalRecord')} page={len(mapped.get('products') or [])}",
    )

    unmapped_open = svc.list_unmapped_platform_products(page_size=5)
    report.check(
        "list_unmapped_platform",
        unmapped_open.get("successed") is True,
        f"total={unmapped_open.get('totalRecord')}",
    )

    unmapped_pos = svc.list_unmapped_pospal_products(page_size=5)
    report.check(
        "list_unmapped_pospal",
        unmapped_pos.get("successed") is True,
        f"total={unmapped_pos.get('totalRecord')}",
    )

    fails = svc.list_mapping_failures(page_size=5)
    report.check(
        "list_mapping_failures",
        fails.get("successed") is True,
        f"total={fails.get('totalRecord')}",
    )

    cats = svc.list_pos_categories()
    report.check(
        "list_pos_categories",
        cats.get("successed") is True and len(cats.get("categories") or []) > 0,
        f"count={len(cats.get('categories') or [])}",
    )

    open_cats = svc.list_platform_categories(source_type="MEITUAN_WAIMAI")
    report.check(
        "list_platform_categories",
        open_cats.get("successed") is True,
        f"count={len(open_cats.get('categories') or [])}",
    )

    # 详情：优先用已映射样本
    products = mapped.get("products") or []
    if products:
        sample = products[0]
        dish_id = str(sample.get("dishId") or "")
        product_uid = str(sample.get("productUid") or "")
        if dish_id:
            detail = svc.get_platform_product(dish_id=dish_id)
            report.check(
                "get_platform_product",
                detail.get("successed") is True
                and bool((detail.get("product") or {}).get("dishId")),
                f"dishId={dish_id}",
            )
        else:
            report.check("get_platform_product", False, "mapped sample missing dishId")
        if product_uid:
            detail2 = svc.get_mapped_product_details(product_uid=product_uid)
            report.check(
                "get_mapped_product",
                detail2.get("successed") is True,
                f"productUid={product_uid}",
            )
        else:
            report.check("get_mapped_product", False, "mapped sample missing productUid")
    else:
        report.check("get_platform_product", False, "no mapped products")
        report.check("get_mapped_product", False, "no mapped products")

    # 计费保护：未 confirm 不得真拉
    pull_guard = svc.pull_platform_products(confirm=False)
    report.check(
        "pull_requires_confirm",
        pull_guard.get("successed") is False,
        str(pull_guard.get("error") or "")[:80],
    )

    report.print_report()
    failed = sum(1 for r in report.results if r["status"] == FAIL)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
