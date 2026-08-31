# reference/ — 原型接線（非產品後端）

這裡的內容來自 `Ai-to-Agent-CGM-v2`，作為「同一份資料契約的一個可執行參考實作」。
它適合在單人原型期快速把資料跑起來，**不是 Web／App 的後端架構**。

- `n8n/cgm-coach.workflow.json` — LINE 官方帳號 → Gemini 結構化估算 → Google Sheets 的 n8n 工作流，
  含一鍵校正 postback 與個人常吃食物表覆蓋。
- `n8n/personal_food_table.sample.csv` — 食物表種子（**數值為範例，需以 TFDA／USDA 校正**）。
  正式的 schema 與 JSON 版種子在 `../schemas/personal-food-table.schema.json`、`../examples/personal-food-table.json`。
- `n8n/README.md` — 憑證、環境變數、節點說明。

## 與本 repo 主線的關係

| 主線（`scripts/`、`schemas/`、`docs/`） | 這裡（`reference/`） |
|---|---|
| 廠商中立、契約優先、有 CI、可長成 App | 綁定 LINE + n8n + Gemini + Sheets 的原型接線 |
| 確定性分析引擎吃 CSV／JSON，吐 schema 驗證的結果 | 擷取與 LLM 呼叫邏輯寫在 n8n Code node |
| Web／App 後端照 `schemas/*.json` 開發，Day 1 用 Postgres | 單人原型期用 Google Sheets |

App 化時：保留 `scripts/` 的分析引擎，重寫擷取層為你的前端 + 後端，**不要把商業邏輯留在 n8n**。
