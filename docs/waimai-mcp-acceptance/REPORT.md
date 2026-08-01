# 外卖商品 MCP 验收报告

日期：2026-08-01  
门店：萌萌书店(关天培店) / userId=4151410 / area=47

## 本地环境

- MCP HTTP：`http://127.0.0.1:8000/mcp`（`uv run python server.py`）
- 单元测试：`uv run pytest tests/test_mcp.py` → 4 passed
- 只读验收：`uv run python scripts/acceptance_waimai.py` → PASS=14 FAIL=0

## 新增工具（15）

| 工具 | 类型 |
|------|------|
| pospal_waimai_shop_status | 读 |
| pospal_waimai_mapping_summary | 读 |
| pospal_waimai_list_pospal_products | 读 |
| pospal_waimai_list_mapped_products | 读 |
| pospal_waimai_list_unmapped_platform_products | 读 |
| pospal_waimai_list_unmapped_pospal_products | 读 |
| pospal_waimai_list_mapping_failures | 读 |
| pospal_waimai_get_platform_product | 读 |
| pospal_waimai_get_mapped_product | 读 |
| pospal_waimai_list_categories | 读 |
| pospal_waimai_bind_product | 写 |
| pospal_waimai_unbind_product | 写 |
| pospal_waimai_pull_products | 写（需 confirm） |
| pospal_waimai_set_shelf | 写 |
| pospal_waimai_save_platform_product | 写（需 confirm） |

## ego-browser 交叉验证

| 指标 | MCP | 后台 UI（DOM） | 结果 |
|------|-----|----------------|------|
| 已映射 | 146 | 已映射(146) | 一致 |
| 银豹未映射 | 10809 | 银豹未映射(10809) | 一致 |
| 美团未映射 | 1118 | 美团未映射(1118) | 一致 |
| 最近拉取 | 2026-08-01 11:07:22 | 拉取商品时间：2026-08-01 11:07:22 | 一致 |
| 匹配失败 | 1 条，sku=20069177233，蓝巨人篮球 | 同左 | 一致 |

### 截图

- `01-goods-mapping.png` — 商品映射管理（美团已映射列表）
- `02-associa-fail.png` — 接单匹配失败明细
- `03-associa-status.png` — 门店授权映射概览

## 边界

不含：平台授权、余额充值、自动接单、短信提醒等运营设置。
