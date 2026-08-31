# Agent 契約

## 1. Meal Vision Agent

### 輸入

- 原始餐點影像。
- 使用者備註。
- 餐具或份量參考物。

### 輸出

- 食物項目與可能烹調方式。
- 份量低／高估值。
- 各項信心。
- 可見碳水來源。
- 隱藏糖、油脂與勾芡等不可見因素。
- 最多三個需要使用者確認的問題。

### 失敗條件

- 影像模糊、遮擋或不是餐點。
- 份量沒有任何參考尺度。
- 複合料理無法合理拆解。

失敗時必須請求補充，不得杜撰。

## 2. Nutrition Matching Agent

### 資料優先序

1. 實際包裝營養標示或食譜。
2. 台灣在地官方資料。
3. USDA 等權威資料。
4. 其他可追溯參考資料。

### 輸出要求

每個數值都要保存來源 ID、資料版本、生熟狀態、換算方式與查詢日期。GI 與 GL 是標準參考，不可改寫成個人實測結果。

### Personal Food Table 快速路徑（v3）

高頻品項可先經 `scripts/apply_food_table.py` 以個人常吃食物表做確定性覆蓋：命中的食物直接用表中 per-100 g 值 × 確認份量得到營養區間，`source = personal_table`；未命中或複合料理仍走完整配對流程，`source = vision`。表中的 GI 仍是標準參考值，聚合方式為可利用碳水加權，不得標示為個人實測反應。

## 3. Data Quality Agent

輸出品質類別與原因碼，不改寫原始資料。建議原因碼：

- `TIME_UNCONFIRMED`
- `LOW_CGM_COVERAGE`
- `OVERLAPPING_INTAKE`
- `POST_MEAL_ACTIVITY`
- `PREVIOUS_MEAL_UNRECOVERED`
- `SENSOR_ANOMALY`
- `PORTION_LOW_CONFIDENCE`
- `NUTRITION_SOURCE_WEAK`

## 4. Coach Agent

### 回答順序

1. 先說資料品質與證據等級。
2. 描述已觀察到的曲線與營養特徵。
3. 分開「資料顯示」與「可能解釋」。
4. 提出下一次只改一個因素的實驗。
5. 顯示醫療與安全邊界。

### 禁止

- 把相關描述成因果。
- 使用羞辱或道德化語言評價食物。
- 診斷疾病。
- 建議自行停藥、加藥或調整胰島素。
- 用通用血糖門檻取代使用者的醫療計畫。

