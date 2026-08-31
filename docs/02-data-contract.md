# 資料契約

## 1. Meals 表

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---:|---|
| meal_id | string | 是 | 每餐唯一識別碼 |
| user_id | string | 是 | 去識別使用者代碼 |
| image_ref | string | 是 | 受控影像參照，不建議公開 URL |
| captured_at | datetime | 否 | 原始拍攝時間 |
| uploaded_at | datetime | 否 | Drive 接收時間 |
| meal_start_at | datetime | 是 | 使用者確認的實際進食時間 |
| meal_end_at | datetime | 否 | 實際結束時間 |
| timezone | string | 是 | IANA 時區，如 Asia/Taipei |
| meal_type | enum | 是 | breakfast/lunch/dinner/snack/other |
| foods_json | JSON | 是 | 食物拆解、份量、信心與來源 |
| carbs_g_low/high | number | 是 | 總碳水區間 |
| available_carbs_g_low/high | number | 是 | 可利用碳水區間 |
| protein_g_low/high | number | 是 | 蛋白質區間 |
| fat_g_low/high | number | 是 | 脂肪區間 |
| fiber_g_low/high | number | 是 | 纖維區間 |
| estimated_gl_low/high | number | 否 | 推估 GL 區間 |
| confidence | number | 是 | 0–1 整體信心 |
| user_confirmed | boolean | 是 | 是否已人工確認 |
| context_json | JSON | 否 | 順序、活動、睡眠、壓力等 |
| model_id | string | 是 | 使用的模型與版本 |
| data_source_refs | JSON | 是 | 營養資料來源與版本 |

正式 JSON 驗證規則見 `schemas/meal-record.schema.json`。

## 2. CGM CSV

最低必要欄位：

```csv
timestamp,glucose_mg_dl
2026-08-31T11:45:00+08:00,96
```

規則：

- timestamp 必須包含時區；若原始檔沒有時區，匯入時必須明確指定。
- 統一轉為 mg/dL。若來源為 mmol/L，使用 `mg/dL = mmol/L × 18.0182`。
- 保存原始檔，清理後的資料另存新版本。
- 不可默默移除低值或高值；所有排除應留下原因碼。

## 3. Analysis 表

| 欄位 | 說明 |
|---|---|
| meal_id | 對應餐點 |
| baseline_mg_dl | 餐前基準 |
| peak_mg_dl | 餐後峰值 |
| delta_peak_mg_dl | 峰值增幅 |
| time_to_peak_min | 達峰時間 |
| iauc_120 | 120 分鐘 iAUC，單位 mg·min/dL |
| iauc_180 | 180 分鐘 iAUC |
| recovery_time_min | 恢復時間，未恢復則為 null |
| cgm_coverage_pct | 觀察窗資料覆蓋率 |
| quality_class | A_CLEAN/B_CONTEXTUAL/X_EXCLUDED |
| quality_reasons | 原因碼清單 |
| analysis_version | 計算規格版本 |

## 4. 去識別規範

公開示例禁止包含姓名、電子郵件、電話、Google 帳號、Drive 原始連結、裝置序號、精確位置或可反推身分的自由文字。`user_id` 應使用隨機研究代碼，不應使用病歷號或電話末碼。

## 5. Personal Food Table 表（v3）

個人常吃食物的離線查表，供 `scripts/apply_food_table.py` 對高頻品項做確定性覆蓋。正式驗證規則見 `schemas/personal-food-table.schema.json`，種子見 `examples/personal-food-table.json`。

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---:|---|
| name | string | 是 | 品項名，比對 `foods[].name`（正規化完全比對 → 別名 → 子字串包含） |
| aliases | string | 否 | 逗號／頓號／分號分隔的別名 |
| carb_per_100g | number | 否 | 每 100 g 總碳水 → `carbs_g` |
| net_carb_per_100g | number | 否 | 每 100 g 可利用碳水 → `available_carbs_g`（缺則以 `carb_per_100g` 代入） |
| protein_per_100g | number | 否 | → `protein_g` |
| fat_per_100g | number | 否 | → `fat_g` |
| fiber_per_100g | number | 否 | → `fiber_g` |
| gi | number | 否 | 該食物標準 GI（參考值，非個人實測反應） |
| default_portion_g | number | 否 | `foods[]` 缺份量時的預設克數 |

命中的食物：以 per-100 g 值 × 確認份量區間得到該食物的營養**區間**貢獻，`source` 標記為 `personal_table`。未命中者維持 `source = "vision"`，交由 Nutrition Matching Agent 處理。GI 以可利用碳水中點加權；覆蓋餐點宣告可利用碳水中點 ≥ 80% 時 `gi_source = personal_table`，否則 `partial`。

## 6. Metabolic Panel 表（v3）

`scripts/metabolic_panel.py` 由 CGM 序列產生的變異與範圍面板，schema 見 `schemas/metabolic-panel.schema.json`，範例見 `examples/metabolic-panel.json`。

| 欄位 | 說明 |
|---|---|
| mean_glucose_mg_dl | 期間平均血糖 |
| gmi_pct | 由平均血糖估算之 A1c（Bergenstal 2018） |
| cv_pct / cv_stable | 血糖變異係數；< 36% 視為穩定 |
| sd_mg_dl | 標準差 |
| tir_70_180_pct | 目標範圍內時間佔比 |
| tbr_lt70_pct / tbr_lt54_pct | 低血糖時間佔比（Level 1 / Level 2） |
| tar_gt180_pct / tar_gt250_pct | 高血糖時間佔比（Level 1 / Level 2） |
| overnight_mean_mg_dl / overnight_cv_pct | 00:00–06:00 當地時間的平均與 CV（資料不足為 null） |

低血糖事件（< 70、< 54 mg/dL）另以 CSV 逐筆輸出，供報告頂端安全提示，不併入餐後指標。

