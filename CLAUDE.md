# cust_tagging — 客戶樣貌標籤分析工具

## 專案目的
輸入「標籤名稱」，由 AI 自動歸納對應的台灣特店/品牌，產出：
- 店家清單（含來源連結）
- PowerPoint 簡報（可下載後手動調整）
- SAS code 草稿（供後續撈取資料庫特店中文）

## 檔案結構
```
cust_tagging/
├── app.py              # Streamlit 主程式（UI 進入點）
├── tagger.py           # 核心邏輯：呼叫 Gemini API + Google Search Grounding
├── pptx_builder.py     # PowerPoint 產生器（python-pptx）
├── sas_template.py     # SAS code 產生器（依 AI 輸出的店家清單套 template）
├── template.pptx       # 自訂簡報範本（微軟正黑體，11 張投影片）
├── requirements.txt    # Python 套件需求
├── .env                # API 金鑰（不要 commit）
├── .env.example        # 金鑰範本
├── 啟動.bat            # 一鍵啟動腳本
└── .claude/
    └── commands/pptx/  # 官方 PPTX Skill（設計指南 + 編輯流程）
```

## 技術棧
- **前端 UI**：Streamlit
- **AI + 搜尋**：Google Gemini 2.0 Flash（內建 Google Search Grounding，不需額外 Search API）
- **簡報產生**：python-pptx
- **環境變數**：python-dotenv

## 啟動方式
```
雙擊 啟動.bat
```
或手動：
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 環境變數
`.env` 需包含：
```
GEMINI_API_KEY=你的金鑰
```
金鑰來源：[Google AI Studio](https://aistudio.google.com/app/apikey)

## 資料流
```
使用者輸入標籤名稱
→ tagger.py 呼叫 Gemini（含 Google Search）
→ 回傳 JSON 結構（label / summary / categories / stores）
→ app.py 顯示店家清單
→ pptx_builder.py 產出 .pptx
→ sas_template.py 產出 SAS code
```

## SAS Code 說明

`sas_template.py` 對照 `sas_examples/客戶標籤_SAS_EXAMPLE.SAS` 慣例產出完整 9-Step 流程：

| Step | 說明 |
|------|------|
| 1 | `DATA _NULL_` 建立日期 Macro（P1Y / L1M / P1M ... / DT / P1D） |
| 2 | `PROC SQL` 撈取交易資料，中文店家 → `MERCHANT_CHI_NAME`，英文 → `MERCHANT_ENG_NAME` |
| 3 | `DATA _PRE1` 認列判斷（`IDENTIFIED = '已認列'/'未認列'`），UPCASE + KPROPCASE 處理 |
| 4 | `PROC SQL` 計算 `AMT_MACH` / `TXN_MACH`（CASE WHEN） |
| 5 | `PROC SUMMARY` 依 CST_ID × YYYYMM 彙總 |
| 6 | `PROC SUMMARY` 依 CST_ID 彙總，取得 `DIFF_MONTH_MACH` |
| 7 | 統計確認：TABULATE / TICKET_SIZE / MAX_MIN / TOP10 / 極端值 / 消費月數分布 |
| 8 | `PROC UNIVARIATE` 百分位（AMT / TXN / MONTH，25/50/75/90/95/99） |
| 9 | 貼標輸出 `DATA.INT_{標籤}`，強度 1-3（依百分位人工調整閾值） |

- 中文名稱自動偵測（含 Unicode CJK）→ 搭配 `MERCHANT_CHI_NAME` / `UMCHT_CNAME`
- 英文名稱自動轉大寫 → 搭配 `MERCHANT_ENG_NAME` / `UMCHT_ENAME`
- 表名前綴 `INT_{標籤}` 搭配 `OPTIONS VALIDVARNAME = ANY`

## PPTX 設計指南

使用 `/pptx` 技能（`.claude/commands/pptx/SKILL.md`）：
- 色彩：本專案主色 `#EF7131` 橘 / `#202020` 深灰，不更換
- 字型：全程 **微軟正黑體**，不替換
- 每張投影片 Bullet 不超過 3~5 行，每行 ≤ 20 字
- 動態新增投影片後必須跑 relationship QA 確認無 MISSING rId

## 待辦 / 後續優化
- [x] `sas_template.py` 對照 `客戶標籤_SAS_EXAMPLE.SAS` 完整重寫
- [ ] 加入多步驟確認流程（Phase 1 AI 腦力激盪 → 使用者確認 → Phase 2 網路搜尋）
- [ ] 可考慮部署至 Streamlit Community Cloud 供組員共用
- [ ] 若需保留歷史分析紀錄，可加入 SQLite 儲存
