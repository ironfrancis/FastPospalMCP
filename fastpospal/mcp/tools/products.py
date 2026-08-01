from __future__ import annotations

from typing import Any

from fastpospal.mcp.instance import mcp
from fastpospal.mcp.deps import get_service
from fastpospal.mcp.fields import (
    Barcode,
    CategoryUid,
    PageIndex,
    PageSize,
    ProductEnable,
    ProductId,
    ProductKeyword,
    ProductOrderColumn,
    SortAsc,
)
from fastpospal.mcp.profile import ADVANCED_TOOL_TAG


@mcp.tool(tags={ADVANCED_TOOL_TAG})
def pospal_list_products(
    keyword: ProductKeyword = "",
    page_index: PageIndex = 1,
    page_size: PageSize = 20,
    enable: ProductEnable = "1",
    order_column: ProductOrderColumn = "",
    asc: SortAsc = False,
) -> dict[str, Any]:
    """【advanced】分页查询商品列表（原始层，含完整字段）。

    日常搜索优先 pospal_sem_find_products；管理员浏览用 pospal_sem_list_products_admin。
    已知 productId 查详情用 pospal_get_product。
    排序在服务端完成：查"库存最多/最少的商品"应传 order_column="stock"，取第一页即可。
    """
    return get_service().list_products(
        keyword=keyword,
        page_index=page_index,
        page_size=page_size,
        enable=enable,
        order_column=order_column,
        asc=asc,
    )


@mcp.tool
def pospal_get_product(product_id: ProductId) -> dict[str, Any]:
    """按 productId 获取商品详情 JSON。

    productId 为数字 ID（非 productUid）。更新商品前可先调用以获取完整 payload。
    """
    return get_service().get_product(product_id)


@mcp.tool(tags={ADVANCED_TOOL_TAG})
def pospal_find_product_by_barcode(barcode: Barcode) -> dict[str, Any]:
    """【advanced】按条码精确查商品详情（原始层完整 JSON）。

    日常按名称/条码搜索请用 pospal_sem_find_products。
    """
    return get_service().find_product_by_barcode(barcode)


@mcp.tool
def pospal_create_product(
    name: str,
    barcode: Barcode = "",
    category_uid: CategoryUid = "",
    sell_price: str = "9.99",
    buy_price: str = "5.00",
) -> dict[str, Any]:
    """【写】创建测试商品。

    barcode 为空则自动生成；category_uid 为空则用第一个分类。仅测试账号使用。
    """
    return get_service().create_product(
        name,
        barcode or None,
        category_uid=category_uid or None,
        sell_price=sell_price,
        buy_price=buy_price,
    )


@mcp.tool
def pospal_update_product(
    product_id: ProductId,
    name: str = "",
    sell_price: str = "",
    buy_price: str = "",
    enable: str = "",
) -> dict[str, Any]:
    """【写】更新商品字段（仅传需要修改的字段）。

    enable：1=启用, 0=禁用。至少提供一个非空字段，否则报错。
    """
    changes: dict[str, Any] = {}
    if name:
        changes["name"] = name
    if sell_price:
        changes["sellPrice"] = sell_price
    if buy_price:
        changes["buyPrice"] = buy_price
    if enable:
        changes["enable"] = enable
    if not changes:
        raise ValueError("至少提供一个要修改的字段")
    return get_service().update_product(product_id, **changes)


@mcp.tool
def pospal_delete_product(product_id: ProductId) -> dict[str, Any]:
    """【写】删除商品（不可恢复，仅测试账号使用）。"""
    return get_service().delete_product(product_id)
