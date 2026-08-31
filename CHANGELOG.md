# Changelog

本專案採用語意化版本概念記錄公開變更。

## 3.0.0 — 2026-08-31

收斂 `Ai-to-Agent-CGM-v1`（契約優先、CI、治理、MIT）與 `Ai-to-Agent-CGM-v2`（可執行原型），
以 v1 為主線基底，併入 v2 的三個成熟模組。

### Added

- `scripts/metabolic_panel.py`：CGM 變異與範圍面板（平均血糖、GMI、CV%、TIR/TBR/TAR、隔夜穩定度）與低血糖事件清單（Level 1 < 70、Level 2 < 54）。
- `scripts/apply_food_table.py`：個人常吃食物表確定性覆蓋，命中食物以 per-100 g 值 × 份量區間重算營養，GI 以可利用碳水加權。
- `schemas/personal-food-table.schema.json`、`schemas/metabolic-panel.schema.json` 與對應範例。
- `docs/architecture-deck.html`：v2 帶來的 12 頁架構總覽簡報。
- `reference/`：v2 的 LINE × n8n × Gemini 工作流與食物表種子，定位為「原型接線，非 App 後端」。
- 新增單元測試 `test_metabolic_panel.py`、`test_apply_food_table.py`；CI 增加新 Schema 驗證與「範例可重現」步驟。

### Changed

- `scripts/analyze_cgm.py` 的 iAUC 改為 Wolever 增量法：跨基準線段只取基準以上的三角形面積。`analysis_version` 升為 `1.1.0`，輸出新增 `iauc_method` 欄位。
- `analysis-record` schema 新增必填欄位 `iauc_method`。
- `docs/02`、`docs/03`、`docs/04` 補上食物表、面板、低血糖事件與 Wolever iAUC 說明。

### Notes

- 授權沿用 v1 的 MIT（v2 為 CC BY-SA 4.0，未帶入）。
- 範例 CGM 曲線未跌破基準，故 iAUC 數值與 v1 相同；差異僅在跨基準情形，已於 `test_analyze_cgm.py` 覆蓋。

## 1.0.0 — 2026-08-31（沿自 v1）

### Added

- 第一可行方案的完整 README 與六份實作文件。
- 餐點與 CGM 分析 JSON Schema。
- Meal Vision Agent 與 Coach Agent 契約提示。
- 固定式 CGM 指標計算程式。
- 合成餐次與 CGM 範例資料。
- 單元測試與 GitHub Actions CI。
- 隱私、安全、醫療邊界與品質發布報告。
