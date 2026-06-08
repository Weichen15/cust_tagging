import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """
你是一位台灣消費市場分析專家，熟悉台灣在地店家、品牌與消費習慣。

任務：針對以下「標籤名稱」，歸納出這個標籤所對應的台灣店家或品牌。

標籤名稱：{label_name}

請完成以下三件事：
1. 依你的知識，歸納這個標籤可能涵蓋的台灣店家或品牌（盡量完整，包含連鎖、獨立店、品牌名稱）
2. 透過 Google Search 搜尋：
   - 相關的銀行信用卡回饋優惠特約店家
   - 部落客整理的相關消費清單
   - 台灣消費市場的品牌分類資料
3. 整合後，依「分類」整理店家清單，並說明每個分類的挑選原因

請以下列 JSON 格式回覆，不要有多餘的文字或 markdown：
{{
  "label": "{label_name}",
  "summary": "這個標籤的簡短說明（1-2句話）",
  "categories": [
    {{
      "category_name": "分類名稱",
      "reason": "為何這個分類屬於此標籤的說明",
      "stores": [
        {{
          "name": "店家或品牌名稱",
          "note": "補充說明（可留空）",
          "source": "資料來源（網址或說明）"
        }}
      ]
    }}
  ]
}}
"""


MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]


def analyze_label(label_name: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(label_name=label_name)
    last_error = None

    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.3,
                ),
            )
            raw = response.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {
                    "label": label_name,
                    "summary": "解析失敗，請查看原始回應",
                    "categories": [],
                    "raw_response": raw,
                }

        except Exception as e:
            last_error = e
            err_str = str(e)
            if any(code in err_str for code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                continue  # 嘗試下一個模型
            raise  # 其他錯誤直接往上拋

    raise RuntimeError(
        f"所有 Gemini 模型目前無法使用。\n\n"
        "解決方式：\n"
        "  • 503：伺服器暫時忙碌，等 1-2 分鐘再試\n"
        "  • 429：配額超量，等幾分鐘或明天再試\n"
        f"\n原始錯誤：{last_error}"
    )
