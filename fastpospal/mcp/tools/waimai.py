"""外卖平台商品管理 MCP 工具（创建/映射/上下架）。"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from fastpospal.mcp.deps import get_waimai
from fastpospal.mcp.fields import (
    Barcode,
    PageIndex,
    PageSize,
    ProductKeyword,
    ProductUid,
    WaimaiConfirm,
    WaimaiDishId,
    WaimaiDishSkuId,
    WaimaiOpenStatus,
    WaimaiOpType,
    WaimaiSourceType,
)
from fastpospal.mcp.instance import mcp

UserId = Annotated[
    int | None,
    Field(description="门店 userId；留空默认当前登录门店"),
]


@mcp.tool
def pospal_waimai_shop_status(user_id: UserId = None) -> dict[str, Any]:
    """查询门店在各外卖平台的授权与映射概览（只读）。

    返回每平台：是否已关联、平台商品数、已映射数、最近拉取时间、匹配失败数。
    用于确认当前可操作的 source_type，不包含授权/计费等运营设置。
    """
    return get_waimai().shop_status(user_id=user_id)


@mcp.tool
def pospal_waimai_mapping_summary(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """查询指定平台的商品映射覆盖率摘要。

    返回 mappingCount（已映射）、notMappingCount（银豹未映射）、
    openNotMappingCount（平台未映射）、lastPullTime。
    """
    return get_waimai().mapping_summary(source_type=source_type, user_id=user_id)


@mcp.tool
def pospal_waimai_list_pospal_products(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    keyword: ProductKeyword = "",
    page_index: PageIndex = 1,
    page_size: PageSize = 20,
    user_id: UserId = None,
) -> dict[str, Any]:
    """分页查询银豹商品列表（含各外卖平台映射状态）。

    创建外卖商品或建立映射前的主入口；keyword 支持名称/拼音码/商品编码。
    """
    return get_waimai().list_pospal_products(
        source_type=source_type,
        keyword=keyword,
        page_index=page_index,
        page_size=page_size,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_list_mapped_products(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    keyword: ProductKeyword = "",
    open_keyword: str = "",
    page_index: PageIndex = 1,
    page_size: PageSize = 20,
    user_id: UserId = None,
) -> dict[str, Any]:
    """分页查询已映射商品（平台商品 ↔ 银豹商品）。

    keyword 筛银豹侧；open_keyword 筛平台商品名称。
    """
    return get_waimai().list_mapped_products(
        source_type=source_type,
        keyword=keyword,
        open_keyword=open_keyword,
        page_index=page_index,
        page_size=page_size,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_list_unmapped_platform_products(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    keyword: ProductKeyword = "",
    page_index: PageIndex = 1,
    page_size: PageSize = 20,
    user_id: UserId = None,
) -> dict[str, Any]:
    """分页查询平台未映射商品（有平台货、尚未对应到银豹）。

    适合「去映射」工作流：取出 dishId/dishSkuId 后调用 pospal_waimai_bind_product。
    """
    return get_waimai().list_unmapped_platform_products(
        source_type=source_type,
        keyword=keyword,
        page_index=page_index,
        page_size=page_size,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_list_unmapped_pospal_products(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    keyword: ProductKeyword = "",
    page_index: PageIndex = 1,
    page_size: PageSize = 20,
    user_id: UserId = None,
) -> dict[str, Any]:
    """分页查询银豹未映射商品（本地有货、尚未映射到该平台）。"""
    return get_waimai().list_unmapped_pospal_products(
        source_type=source_type,
        keyword=keyword,
        page_index=page_index,
        page_size=page_size,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_list_mapping_failures(
    source_type: WaimaiSourceType = "",
    page_index: PageIndex = 1,
    page_size: PageSize = 20,
    user_id: UserId = None,
) -> dict[str, Any]:
    """查询接单时商品匹配失败明细。

    匹配失败会导致库存/报表不准；取出 dishSkuId 后应尽快建立映射。
    source_type 留空查全平台。
    """
    return get_waimai().list_mapping_failures(
        source_type=source_type,
        page_index=page_index,
        page_size=page_size,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_get_platform_product(
    dish_id: WaimaiDishId,
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """获取平台商品详情（含 SKU 列表）。编辑/映射前可先查。"""
    return get_waimai().get_platform_product(
        dish_id=dish_id,
        source_type=source_type,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_get_mapped_product(
    product_uid: ProductUid,
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """按银豹 productUid 获取已映射的平台商品详情。"""
    return get_waimai().get_mapped_product_details(
        product_uid=product_uid,
        source_type=source_type,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_list_categories(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """同时返回银豹分类与指定平台分类，便于创建/映射时选分类。"""
    svc = get_waimai()
    return {
        "successed": True,
        "posCategories": svc.list_pos_categories(user_id=user_id).get("categories") or [],
        "platformCategories": svc.list_platform_categories(
            source_type=source_type, user_id=user_id
        ).get("categories")
        or [],
        "sourceType": source_type,
    }


@mcp.tool
def pospal_waimai_bind_product(
    dish_sku_id: WaimaiDishSkuId,
    dish_id: WaimaiDishId,
    barcode: Barcode,
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """【写】建立平台 SKU 与银豹商品（条码）的映射。

    参数来自 pospal_waimai_list_unmapped_platform_products（dishSkuId/dishId）
    与银豹商品 barcode。
    """
    return get_waimai().bind_product(
        dish_sku_id=dish_sku_id,
        dish_id=dish_id,
        barcode=barcode,
        source_type=source_type,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_unbind_product(
    dish_sku_id: WaimaiDishSkuId,
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """【写】解除平台商品与银豹商品的映射。"""
    return get_waimai().unbind_product(
        dish_sku_id=dish_sku_id,
        source_type=source_type,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_pull_products(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
    confirm: WaimaiConfirm = False,
) -> dict[str, Any]:
    """【写】从外卖平台拉取最新商品到银豹侧缓存。

    会调用平台管理类接口并可能计费；必须传 confirm=True。
    平台侧新增/编辑商品后，若本地搜不到，应先拉取再映射。
    """
    return get_waimai().pull_platform_products(
        source_type=source_type,
        user_id=user_id,
        confirm=confirm,
    )


@mcp.tool
def pospal_waimai_set_shelf(
    dish_ids: Annotated[str, Field(description="平台 dishId，多个用逗号分隔")],
    open_status: WaimaiOpenStatus = 1,
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """【写】批量上架/下架平台商品。

    open_status：1=上架，0=下架。dish_ids 来自已映射或平台商品列表的 dishId。
    """
    ids = [x.strip() for x in dish_ids.split(",") if x.strip()]
    return get_waimai().set_shelf(
        dish_ids=ids,
        open_status=open_status,
        source_type=source_type,
        user_id=user_id,
    )


@mcp.tool
def pospal_waimai_save_platform_product(
    open_save_request: Annotated[
        dict[str, Any],
        Field(description="平台商品 DTO；建议先 get_platform_product 取结构再修改"),
    ],
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    op_type: WaimaiOpType = "UPDATE",
    user_id: UserId = None,
    confirm: WaimaiConfirm = False,
) -> dict[str, Any]:
    """【写】创建或更新外卖平台商品（计费接口，需 confirm=True）。

    op_type：CREATE=以此创建外卖商品，UPDATE=编辑外卖商品。
    字段因平台而异；推荐流程：get_mapped_product / get_platform_product → 修改 → save。
    """
    return get_waimai().save_platform_product(
        open_save_request=open_save_request,
        source_type=source_type,
        user_id=user_id,
        op_type=op_type,
        confirm=confirm,
    )
