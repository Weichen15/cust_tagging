@echo off
chcp 65001 > nul
echo 啟動客戶標籤分析工具...
cd /d "%~dp0"

pip install -r requirements.txt -q

streamlit run app.py
pause
