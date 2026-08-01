# 外卖商品 MCP 验收报告

日期：2026-08-02  
门店：萌萌书店(关天培店) / userId=4151410 / area=47

## 工具精简（本轮）

| 变更 | 说明 |
|------|------|
| 合并 list×4 | → `pospal_waimai_list_products(mapping_status=all\|mapped\|unmapped_platform\|unmapped_pospal)` |
| 合并 mapping_summary | → 并入 `pospal_waimai_shop_status.mappingSummary` |
| 全局 default profile | 默认 42 工具；`POSPAL_MCP_PROFILE=advanced` 为 49 |

## 当前外卖 MCP 工具（11）

| 工具 | 类型 |
|------|------|
| pospal_waimai_shop_status | 读（含 mappingSummary） |
| pospal_waimai_list_products | 读 |
| pospal_waimai_list_mapping_failures | 读 |
| pospal_waimai_get_platform_product | 读 |
| pospal_waimai_get_mapped_product | 读 |
| pospal_waimai_list_categories | 读 |
| pospal_waimai_bind_product | 写 |
| pospal_waimai_unbind_product | 写 |
| pospal_waimai_pull_products | 写（需 confirm） |
| pospal_waimai_set_shelf | 写 |
| pospal_waimai_save_platform_product | 写（需 confirm） |

## 验收结果（2026-08-02）

```bash
uv run pytest tests/ -q          # 33 passed
uv run python scripts/acceptance_waimai.py   # PASS=24 FAIL=0
```

映射覆盖率抽样：已映射 147 / 银豹未映射 10811 / 美团未映射 1118。

## 边界

不含：平台授权、余额充值、自动接单、短信提醒等运营设置。
底层 `WaimaiService` 方法仍保留（list_mapped / mapping_summary 等），供 SDK 与验收脚本直接调用。
