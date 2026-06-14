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
- `sas_template.py` 目前使用 `index(MERCH_NAME_CHT, "店家名") > 0` 做字串比對
- 變數命名：`TAG_{標籤}` 為總標籤，`TAG_{標籤}_{分類}` 為細分類
- **待補**：使用者提供實際慣用的 SAS 寫法後，需更新 `sas_template.py` 的 template

## PPTX 設計指南

使用 `/pptx` 技能（`.claude/commands/pptx/SKILL.md`）：
- 色彩：本專案主色 `#EF7131` 橘 / `#202020` 深灰，不更換
- 字型：全程 **微軟正黑體**，不替換
- 每張投影片 Bullet 不超過 3~5 行，每行 ≤ 20 字
- 動態新增投影片後必須跑 relationship QA 確認無 MISSING rId

## 待辦 / 後續優化
- [ ] 使用者提供 SAS 慣用寫法 → 更新 `sas_template.py`
- [ ] 加入多步驟確認流程（Phase 1 AI 腦力激盪 → 使用者確認 → Phase 2 網路搜尋）
- [ ] 可考慮部署至 Streamlit Community Cloud 供組員共用
- [ ] 若需保留歷史分析紀錄，可加入 SQLite 儲存
