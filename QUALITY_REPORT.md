# v3 發布品質報告

檢查日期：2026-08-31
版本：3.0.0

## 完整性結論

本版本收斂 v1 與 v2，達到「公開架構 ＋ 可執行、可驗證的分析核心」的 GitHub 發布標準。它不是完整商用 App，也不宣稱已串接 Google、CGM 原廠或臨床系統。

| 項目 | 結果 | 證據 |
|---|---|---|
| v3 範圍與排除項目 | 通過 | README、系統架構文件 |
| 版本沿革與收斂說明 | 通過 | README §0、CHANGELOG 3.0.0 |
| 端到端資料流 | 通過 | Mermaid 架構、Google Workspace 設定 |
| 資料契約（餐點／分析／食物表／面板） | 通過 | 4 份 JSON Schema、對應 JSON 範例、CI 驗證 |
| Agent 責任與禁止事項 | 通過 | Agent 契約與 prompts |
| CGM 固定計算（Wolever iAUC） | 通過 | `scripts/analyze_cgm.py`、`test_analyze_cgm.py` |
| 代謝面板與低血糖事件 | 通過 | `scripts/metabolic_panel.py`、`test_metabolic_panel.py` |
| 個人食物表覆蓋 | 通過 | `scripts/apply_food_table.py`、`test_apply_food_table.py` |
| 可重現範例 | 通過 | examples、CI「範例可重現」步驟、15 項單元測試 |
| 自動化品質檢查 | 通過 | GitHub Actions CI（compile、unittest、schema、範例、密鑰掃描） |
| 隱私與敏感資料保護 | 通過 | PRIVACY、SECURITY、gitignore、CI 掃描 |
| 醫療安全邊界 | 通過 | README、臨床分析協定、Coach 契約、低血糖獨立提示 |
| 版本與授權 | 通過 | VERSION、CHANGELOG、MIT License |

## 已知限制

- 2D 影像份量估計存在天然不確定性；v3 以區間與待確認項表達，不輸出假精確值。
- 個人食物表數值需由使用者以 TFDA／USDA 或包裝標示校正；種子檔僅為範例。
- 預設 CGM 採五分鐘間隔；其他頻率需先驗證覆蓋率算法。
- 隔夜面板需涵蓋當地 00:00–06:00 的資料，短窗範例會回傳 null。
- `reference/` 的 n8n 工作流為單人原型接線，不是 Web／App 後端。
- 正式臨床、研究或商業用途仍需額外的法規、資安、同意與驗證工作。

## 發布決策

**GO：可作為 v3.0.0 公開架構與可持續開發基底上傳 GitHub。**
