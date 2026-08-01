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
    WaimaiMappingStatus,
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
def pospal_waimai_shop_status(
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    user_id: UserId = None,
) -> dict[str, Any]:
    """查询门店外卖授权与映射覆盖率（只读）。

    返回 shops（各平台授权概览）以及 mappingSummary（指定 source_type 的
    mappingCount / notMappingCount / openNotMappingCount / lastPullTime）。
    用于确认可操作平台；不含授权/计费等运营设置。
    """
    svc = get_waimai()
    status = svc.shop_status(user_id=user_id)
    status["mappingSummary"] = svc.mapping_summary(
        source_type=source_type or "MEITUAN_WAIMAI",
        user_id=user_id,
    )
    return status


@mcp.tool
def pospal_waimai_list_products(
    mapping_status: WaimaiMappingStatus = "all",
    source_type: WaimaiSourceType = "MEITUAN_WAIMAI",
    keyword: ProductKeyword = "",
    open_keyword: str = "",
    page_index: PageIndex = 1,
    page_size: PageSize = 20,
    user_id: UserId = None,
) -> dict[str, Any]:
    """分页查询外卖相关商品（按映射状态筛选）。

    mapping_status：
    - all：银豹商品列表（含各平台映射状态），创建/映射前主入口
    - mapped：已映射（平台 ↔ 银豹）；open_keyword 可筛平台侧名称
    - unmapped_platform：平台未映射（取 dishId/dishSkuId 后 bind）
    - unmapped_pospal：银豹未映射
    keyword 筛银豹侧名称/拼音码/编码。
    """
    status = (mapping_status or "all").strip().lower()
    svc = get_waimai()
    if status in ("", "all"):
        return svc.list_pospal_products(
            source_type=source_type,
            keyword=keyword,
            page_index=page_index,
            page_size=page_size,
            user_id=user_id,
        )
    if status == "mapped":
        return svc.list_mapped_products(
            source_type=source_type,
            keyword=keyword,
            open_keyword=open_keyword,
            page_index=page_index,
            page_size=page_size,
            user_id=user_id,
        )
    if status in ("unmapped_platform", "platform"):
        return svc.list_unmapped_platform_products(
            source_type=source_type,
            keyword=keyword,
            page_index=page_index,
            page_size=page_size,
            user_id=user_id,
        )
    if status in ("unmapped_pospal", "pospal"):
        return svc.list_unmapped_pospal_products(
            source_type=source_type,
            keyword=keyword,
            page_index=page_index,
            page_size=page_size,
            user_id=user_id,
        )
    raise ValueError(
        "mapping_status 须为 all / mapped / unmapped_platform / unmapped_pospal"
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
    """按银豹 productUid 获取外卖商品详情。

    返回 mode=UPDATE（已映射，含 dishId，可改价）或 mode=CREATE（未映射创建模板）。
    改价请用已映射详情改 openPrice / openSkuList[].openPrice 后再 save。
    """
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

    参数来自 pospal_waimai_list_products(mapping_status=unmapped_platform)
    的 dishSkuId/dishId，与银豹商品 barcode。
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

    op_type：CREATE=以此创建外卖商品，UPDATE=编辑已映射商品（必须带 dishId）。
    推荐：list_products(mapped) → get_mapped_product(mode=UPDATE) → 改价 → save(confirm=True)。
    """
    return get_waimai().save_platform_product(
        open_save_request=open_save_request,
        source_type=source_type,
        user_id=user_id,
        op_type=op_type,
        confirm=confirm,
    )
