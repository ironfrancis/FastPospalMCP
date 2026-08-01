"""外卖平台商品管理 API（waimai-api{area}.pospal.cn）。"""

from __future__ import annotations

from typing import Any

from fastpospal.raw.client import PospalApiError, PospalClient


def _normalize_open_pictures(value: Any) -> str:
    """前端提交时 openPictures 必须是逗号分隔字符串。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        urls: list[str] = []
        for item in value:
            if isinstance(item, dict):
                url = item.get("url") or ""
            else:
                url = str(item or "")
            if url:
                urls.append(url)
        return ",".join(urls)
    return str(value)


def _normalize_open_save_request(
    open_save_request: dict[str, Any],
    *,
    user_id: int,
    source_type: str,
    op_type: str,
) -> dict[str, Any]:
    """对齐银豹后台单品编辑弹窗的扁平 openSave body。"""
    body = dict(open_save_request)
    body["userId"] = user_id
    body["sourceType"] = source_type
    body["openPictures"] = _normalize_open_pictures(body.get("openPictures"))
    body.pop("sourceTypeName", None)

    skus = [dict(s) for s in (body.get("openSkuList") or [])]
    for sku in skus:
        # 后台编辑页提交时强制 openWeightUnit=g
        if sku.get("openWeight") is not None or sku.get("openWeightUnit"):
            sku["openWeightUnit"] = "g"
    body["openSkuList"] = skus

    if op_type == "UPDATE":
        if not body.get("dishId"):
            raise PospalApiError(
                "UPDATE 需要 dishId；请先 list_mapped_products / get_mapped_product（mode=UPDATE）再改价"
            )
        if "openSkuUpdateList" not in body and "openSkuAddList" not in body:
            updates: list[dict[str, Any]] = []
            adds: list[dict[str, Any]] = []
            for sku in skus:
                if sku.get("dishSkuId"):
                    updates.append(sku)
                else:
                    adds.append(sku)
            body["openSkuUpdateList"] = updates
            body["openSkuAddList"] = adds
        body.setdefault("productAttributePackageAddList", [])
        body.setdefault("productAttributePackageDeleteList", [])
        body.setdefault("productAttributePackageUpdateList", [])

    return body

# 常用平台枚举（与后台 sourceType 一致）
SOURCE_TYPES = {
    "MEITUAN_WAIMAI": "美团外卖",
    "MEITUAN_PINHAOFAN": "美团拼好饭",
    "ELEME_WAIMAI": "淘宝闪购",
    "ELEME_PINTUAN": "淘宝闪购爆品团",
    "ELEBE_WAIMAI": "饿百零售",
    "JDDJ_MIAOSONG": "京东秒送",
    "DOUYIN_WAIMAI": "抖音随心团",
    "DOUYIN_HOUR": "抖音小时达",
}


def _unwrap(resp: dict[str, Any]) -> dict[str, Any]:
    """统一外卖 API 错误处理。"""
    if resp.get("status") == "error" or resp.get("errorCode", 0) not in (0, None):
        messages = resp.get("messages") or [resp.get("msg") or "外卖 API 调用失败"]
        if isinstance(messages, list):
            detail = "; ".join(str(m) for m in messages)
        else:
            detail = str(messages)
        raise PospalApiError(detail)
    return resp


class WaimaiService:
    """外卖商品映射 / 平台商品管理。"""

    def __init__(self, client: PospalClient) -> None:
        self.client = client

    def _uid(self, user_id: int | None) -> int:
        uid = user_id if user_id is not None else self.client.user_id
        if uid is None:
            raise PospalApiError("缺少 userId，请先登录")
        return int(uid)

    # ── 只读 ──────────────────────────────────────────────

    def mapping_summary(
        self,
        *,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post(
                "/waimai/dish/mappingCount",
                {"userId": uid, "sourceType": source_type},
            )
        )
        result = resp.get("result") or {}
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "sourceTypeName": SOURCE_TYPES.get(source_type, source_type),
            "mappingCount": result.get("mappingCount", 0),
            "notMappingCount": result.get("notMappingCount", 0),
            "openNotMappingCount": result.get("openNotMappingCount", 0),
            "lastPullTime": result.get("lastPullTime"),
            "area": self.client.area,
        }

    def list_pospal_products(
        self,
        *,
        source_type: str = "MEITUAN_WAIMAI",
        keyword: str = "",
        page_index: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
        cat_id: str = "",
        mapping_status: int | None = None,
    ) -> dict[str, Any]:
        """银豹侧商品列表（含各平台映射状态）。"""
        uid = self._uid(user_id)
        payload: dict[str, Any] = {
            "userId": uid,
            "sourceType": source_type,
            "curPage": page_index,
            "pageSize": page_size,
        }
        if keyword:
            payload["keyWordSearch"] = keyword
        if cat_id:
            payload["catId"] = cat_id
        if mapping_status is not None:
            payload["mappingStatus"] = mapping_status
        resp = _unwrap(self.client.waimai_post("/waimai/dish/pospalProductList", payload))
        page = resp.get("result") or {}
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "totalRecord": page.get("totalSize", 0),
            "pageIndex": page.get("curPage", page_index),
            "pageSize": page.get("pageSize", page_size),
            "products": page.get("result") or [],
        }

    def list_mapped_products(
        self,
        *,
        source_type: str = "MEITUAN_WAIMAI",
        keyword: str = "",
        open_keyword: str = "",
        page_index: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """已映射商品列表（平台 ↔ 银豹）。"""
        uid = self._uid(user_id)
        payload: dict[str, Any] = {
            "userId": uid,
            "sourceType": source_type,
            "curPage": page_index,
            "pageSize": page_size,
        }
        if keyword:
            payload["keyWordSearch"] = keyword
        if open_keyword:
            payload["openKeyWordSearch"] = open_keyword
        resp = _unwrap(self.client.waimai_post("/waimai/dish/bindNormalList", payload))
        page = resp.get("result") or {}
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "totalRecord": page.get("totalSize", 0),
            "pageIndex": page.get("curPage", page_index),
            "pageSize": page.get("pageSize", page_size),
            "products": page.get("result") or [],
        }

    def list_unmapped_platform_products(
        self,
        *,
        source_type: str = "MEITUAN_WAIMAI",
        keyword: str = "",
        page_index: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """平台未映射商品列表。"""
        uid = self._uid(user_id)
        payload: dict[str, Any] = {
            "userId": uid,
            "sourceType": source_type,
            "curPage": page_index,
            "pageSize": page_size,
        }
        if keyword:
            payload["openKeyWordSearch"] = keyword
        resp = _unwrap(self.client.waimai_post("/waimai/dish/unbindOpenList", payload))
        page = resp.get("result") or {}
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "totalRecord": page.get("totalSize", 0),
            "pageIndex": page.get("curPage", page_index),
            "pageSize": page.get("pageSize", page_size),
            "products": page.get("result") or [],
        }

    def list_unmapped_pospal_products(
        self,
        *,
        source_type: str = "MEITUAN_WAIMAI",
        keyword: str = "",
        page_index: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """银豹未映射商品列表。"""
        uid = self._uid(user_id)
        payload: dict[str, Any] = {
            "userId": uid,
            "sourceType": source_type,
            "curPage": page_index,
            "pageSize": page_size,
        }
        if keyword:
            payload["keyWordSearch"] = keyword
        resp = _unwrap(self.client.waimai_post("/waimai/dish/unbindNormalList", payload))
        page = resp.get("result") or {}
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "totalRecord": page.get("totalSize", 0),
            "pageIndex": page.get("curPage", page_index),
            "pageSize": page.get("pageSize", page_size),
            "products": page.get("result") or [],
        }

    def list_mapping_failures(
        self,
        *,
        source_type: str = "",
        page_index: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """接单商品匹配失败明细。"""
        uid = self._uid(user_id)
        payload: dict[str, Any] = {
            "userId": uid,
            "curPage": page_index,
            "pageSize": page_size,
        }
        if source_type:
            payload["sourceType"] = source_type
        resp = _unwrap(self.client.waimai_post("/waimai/shop/associatedLog", payload))
        page = resp.get("result") or {}
        return {
            "successed": True,
            "userId": uid,
            "totalRecord": page.get("totalSize", 0),
            "pageIndex": page.get("curPage", page_index),
            "pageSize": page.get("pageSize", page_size),
            "failures": page.get("result") or [],
        }

    def get_platform_product(
        self,
        *,
        dish_id: str,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
        dish_sku_id: str = "",
        product_uid: str = "",
    ) -> dict[str, Any]:
        """平台商品详情（含 SKU）。编辑已上架商品时用此接口。"""
        uid = self._uid(user_id)
        payload: dict[str, Any] = {
            "userId": uid,
            "sourceType": source_type,
            "dishId": dish_id,
        }
        if dish_sku_id:
            payload["dishSkuId"] = dish_sku_id
        if product_uid:
            payload["productUid"] = product_uid
        resp = _unwrap(self.client.waimai_post("/waimai/dish/openProductDetails", payload))
        return {
            "successed": True,
            "mode": "UPDATE",
            "product": resp.get("result") or {},
        }

    def get_mapped_product_details(
        self,
        *,
        product_uid: str,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
        dish_id: str = "",
        dish_sku_id: str = "",
    ) -> dict[str, Any]:
        """按银豹 productUid 取外卖商品详情。

        - 已映射：返回 openProductDetails（含 dishId，可供 UPDATE）
        - 未映射：返回 productDetails 创建模板（mode=CREATE），不可直接 UPDATE
        """
        uid = self._uid(user_id)

        # 若调用方已知 dishId，直接走编辑详情
        if dish_id:
            return self.get_platform_product(
                dish_id=dish_id,
                source_type=source_type,
                user_id=uid,
                dish_sku_id=dish_sku_id,
                product_uid=product_uid,
            )

        # 先取创建模板，并从 SKU 条码反查是否已映射
        create_resp = _unwrap(
            self.client.waimai_post(
                "/waimai/dish/productDetails",
                {
                    "userId": uid,
                    "sourceType": source_type,
                    "productUid": product_uid,
                },
            )
        )
        create_product = create_resp.get("result") or {}
        barcodes: list[str] = []
        for sku in create_product.get("openSkuList") or []:
            code = sku.get("eDishSkuId") or sku.get("barcode") or ""
            if code:
                barcodes.append(str(code).split("#")[0])

        mapped_row: dict[str, Any] | None = None
        for code in barcodes:
            page = self.list_mapped_products(
                source_type=source_type,
                keyword=code,
                page_index=1,
                page_size=20,
                user_id=uid,
            )
            for row in page.get("products") or []:
                if str(row.get("productUid") or "") == str(product_uid):
                    mapped_row = row
                    break
            if mapped_row:
                break

        if not mapped_row:
            return {
                "successed": True,
                "mode": "CREATE",
                "mapped": False,
                "hint": "该银豹商品尚未映射到外卖平台；可用 op_type=CREATE 创建，或先 mapping_bind。不要对缺 dishId 的模板做 UPDATE。",
                "product": create_product,
            }

        detail = self.get_platform_product(
            dish_id=str(mapped_row.get("dishId") or ""),
            source_type=source_type,
            user_id=uid,
            dish_sku_id=str(mapped_row.get("dishSkuId") or ""),
            product_uid=str(product_uid),
        )
        return {
            "successed": True,
            "mode": "UPDATE",
            "mapped": True,
            "mapping": {
                "dishId": mapped_row.get("dishId"),
                "dishSkuId": mapped_row.get("dishSkuId"),
                "productUid": mapped_row.get("productUid"),
                "barcode": mapped_row.get("barcode") or mapped_row.get("eDishSkuId"),
                "openProductName": mapped_row.get("openProductName"),
                "openPrice": mapped_row.get("openPrice"),
            },
            "product": detail.get("product") or {},
        }

    def list_pos_categories(self, *, user_id: int | None = None) -> dict[str, Any]:
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post("/waimai/category/queryPosCategoryList", {"userId": uid})
        )
        return {"successed": True, "categories": resp.get("result") or []}

    def list_platform_categories(
        self,
        *,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post(
                "/waimai/category/queryOpenCategoryList",
                {"userId": uid, "sourceType": source_type},
            )
        )
        return {
            "successed": True,
            "sourceType": source_type,
            "categories": resp.get("result") or [],
        }

    def shop_status(self, *, user_id: int | None = None) -> dict[str, Any]:
        """门店×平台授权与映射概览（只读，便于选平台）。"""
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post(
                "/waimai/shop/status",
                {"userId": uid, "curPage": 1, "pageSize": 50},
            )
        )
        page = resp.get("result") or {}
        return {
            "successed": True,
            "totalRecord": page.get("totalSize", 0),
            "shops": page.get("result") or [],
        }

    # ── 写操作 ────────────────────────────────────────────

    def bind_product(
        self,
        *,
        dish_sku_id: str,
        dish_id: str,
        barcode: str,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """建立平台 SKU ↔ 银豹商品条码映射。"""
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post(
                "/waimai/dish/mappingBind",
                {
                    "userId": uid,
                    "sourceType": source_type,
                    "mappingBinds": [
                        {
                            "dishSkuId": dish_sku_id,
                            "dishId": dish_id,
                            "barcode": barcode,
                        }
                    ],
                },
            )
        )
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "dishSkuId": dish_sku_id,
            "dishId": dish_id,
            "barcode": barcode,
            "result": resp.get("result"),
        }

    def unbind_product(
        self,
        *,
        dish_sku_id: str,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """解除平台商品映射。"""
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post(
                "/waimai/dish/mappingUnbind",
                {
                    "userId": uid,
                    "sourceType": source_type,
                    "dishSkuId": dish_sku_id,
                },
            )
        )
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "dishSkuId": dish_sku_id,
            "result": resp.get("result"),
        }

    def pull_platform_products(
        self,
        *,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """从外卖平台拉取商品（计费接口，需 confirm=True）。"""
        if not confirm:
            return {
                "successed": False,
                "error": "拉取平台商品会调用平台管理接口并可能计费，请传 confirm=True 确认",
                "hint": "仅在明确需要刷新平台商品缓存时使用",
            }
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post(
                "/waimai/shop/pull",
                {"userId": uid, "sourceType": source_type},
                params={"skipErrorMessage": "true"},
            )
        )
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "result": resp.get("result"),
        }

    def set_shelf(
        self,
        *,
        dish_ids: list[str],
        open_status: int,
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """批量上下架。open_status：1=上架，0=下架。"""
        if open_status not in (0, 1):
            raise PospalApiError("open_status 只能是 1（上架）或 0（下架）")
        if not dish_ids:
            raise PospalApiError("dish_ids 不能为空")
        uid = self._uid(user_id)
        resp = _unwrap(
            self.client.waimai_post(
                "/waimai/dish/batchShelf/submit",
                {
                    "userId": uid,
                    "sourceType": source_type,
                    "openStatus": open_status,
                    "isBindTab": False,
                    "dishSelectRequest": {"dishIds": dish_ids},
                },
            )
        )
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "openStatus": open_status,
            "dishIds": dish_ids,
            "result": resp.get("result"),
        }

    def save_platform_product(
        self,
        *,
        open_save_request: dict[str, Any],
        source_type: str = "MEITUAN_WAIMAI",
        user_id: int | None = None,
        op_type: str = "UPDATE",
        confirm: bool = False,
    ) -> dict[str, Any]:
        """创建或更新平台商品（计费接口）。

        单品创建/编辑走扁平 body（与后台编辑弹窗一致），不要包 openSaveRequestDTOMap。
        推荐：get_mapped_product / get_platform_product → 改价 → save(confirm=True)。
        """
        if not confirm:
            return {
                "successed": False,
                "error": "创建/更新外卖商品会调用平台管理接口并可能计费，请传 confirm=True 确认",
            }
        if op_type not in ("CREATE", "UPDATE"):
            raise PospalApiError("op_type 只能是 CREATE 或 UPDATE")
        uid = self._uid(user_id)
        payload = _normalize_open_save_request(
            open_save_request,
            user_id=uid,
            source_type=source_type,
            op_type=op_type,
        )
        resp = _unwrap(self.client.waimai_post("/waimai/dish/openSave", payload))
        return {
            "successed": True,
            "userId": uid,
            "sourceType": source_type,
            "opType": op_type,
            "dishId": payload.get("dishId"),
            "result": resp.get("result"),
        }
