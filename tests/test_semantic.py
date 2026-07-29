from __future__ import annotations

from typing import Any

from fastpospal.semantic.categories import (
    build_categorys_json,
    flatten_categories,
    match_categories_by_keyword,
    pick_sales_amount_column,
    pick_sales_quantity_column,
)
from fastpospal.semantic.service import PospalSemanticService
from fastpospal.semantic.shops import resolve_shop_id, shop_name_to_id


def test_shop_name_to_id():
    assert shop_name_to_id("关天培店") == "4151410"
    assert shop_name_to_id("") == "4151410"


def test_resolve_shop_id():
    assert resolve_shop_id("山阳湖店") == 4455361


def test_flatten_categories_flat_list():
    nodes = [
        {"uid": "1", "name": "冷饮", "parentUid": ""},
        {"uid": "2", "name": "雪糕", "parentUid": "1"},
    ]
    flat = flatten_categories(nodes)
    assert len(flat) == 2
    assert flat[1]["parent_name"] == "冷饮"


def test_match_categories_by_keyword():
    categories = [
        {"id": "1", "name": "冷饮", "parent_name": ""},
        {"id": "2", "name": "雪糕", "parent_name": "冷饮"},
    ]
    matches = match_categories_by_keyword(categories, "雪糕")
    assert len(matches) == 1
    assert matches[0]["id"] == "2"


def test_build_categorys_json():
    assert build_categorys_json([]) == "[]"
    payload = build_categorys_json(["abc"])
    assert "abc" in payload
    assert "-12345" in payload


def test_pick_sales_quantity_column_english_alias():
    cols = ["商品名称", "barcode", "totoalProductNum", "totalAmount"]
    assert pick_sales_quantity_column(cols) == "totoalProductNum"
    assert pick_sales_amount_column(cols) == "totalAmount"


def test_pick_sales_columns_chinese():
    cols = ["商品名称", "销售数量", "实收金额", "利润"]
    assert pick_sales_quantity_column(cols) == "销售数量"
    assert pick_sales_amount_column(cols) == "实收金额"


def test_aggregate_sale_items_english_columns():
    svc = PospalSemanticService(raw=None)  # type: ignore[arg-type]
    items = [
        {
            "商品名称": "布鲁可 A",
            "totoalProductNum": "1",
            "totalAmount": "35",
        },
        {
            "商品名称": "布鲁可 B",
            "totoalProductNum": "2",
            "totalAmount": "20",
        },
        {
            "商品名称": "布鲁可 C",
            "totoalProductNum": "0",
            "totalAmount": "0",
        },
    ]
    result = svc._aggregate_sale_items(items, limit=10)
    assert result["success"] is True
    summary = result["data"]["summary"]
    assert summary["product_rows"] == 3
    assert summary["total_quantity"] == 3.0
    assert summary["total_amount"] == 55.0


class _FakeRaw:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.last_kwargs: dict[str, Any] = {}

    def product_sale_summary(self, **kwargs: Any) -> dict[str, Any]:
        self.last_kwargs = kwargs
        return self.payload


def test_query_sales_detail_search_recomputes_summary_when_keyword_ignored():
    raw = _FakeRaw(
        {
            "totalRecord": 100,
            "summary": {"记录数": "100", "总销量": "233", "总实收": "469.45"},
            "items": [
                {
                    "流水号": "1",
                    "productName": "布鲁可 74201",
                    "barcode": "111",
                    "totoalProductNum": "1",
                    "totalAmount": "35",
                    "totalProfit": "13.89",
                },
                {
                    "流水号": "2",
                    "productName": "其他商品",
                    "barcode": "222",
                    "totoalProductNum": "5",
                    "totalAmount": "50",
                    "totalProfit": "10",
                },
            ],
        }
    )
    svc = PospalSemanticService(raw=raw)  # type: ignore[arg-type]
    result = svc.query_sales_detail(search="布鲁可", start_date="2026-07-29", end_date="2026-07-29")
    assert raw.last_kwargs.get("keyword") == "布鲁可"
    assert result["success"] is True
    data = result["data"]
    assert data["total"] == 1
    assert data["summary"]["记录数"] == "1"
    assert data["summary"]["总销量"] == "1"
    assert data["summary"]["总实收"] == "35"


def test_query_sales_detail_search_trusts_server_when_already_filtered():
    raw = _FakeRaw(
        {
            "totalRecord": 6,
            "summary": {"记录数": "6", "总销量": "6", "总实收": "145"},
            "items": [
                {
                    "流水号": "1",
                    "productName": "布鲁可 74201",
                    "barcode": "111",
                    "totoalProductNum": "1",
                    "totalAmount": "35",
                },
                {
                    "流水号": "2",
                    "productName": "布鲁可 71405",
                    "barcode": "222",
                    "totoalProductNum": "1",
                    "totalAmount": "10",
                },
            ],
        }
    )
    svc = PospalSemanticService(raw=raw)  # type: ignore[arg-type]
    result = svc.query_sales_detail(search="布鲁可", start_date="2026-07-29", end_date="2026-07-29")
    data = result["data"]
    assert data["total"] == 6
    assert data["summary"]["总实收"] == "145"
    assert len(data["items"]) == 2
