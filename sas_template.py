from datetime import date


def build_sas_code(data: dict) -> str:
    label = data.get("label", "LABEL")
    summary = data.get("summary", "")
    categories = data.get("categories", [])
    today = date.today().strftime("%Y-%m-%d")

    # 收集所有店家名稱（去重）
    all_stores: list[str] = []
    for cat in categories:
        for store in cat.get("stores", []):
            name = store.get("name", "").strip()
            if name and name not in all_stores:
                all_stores.append(name)

    # 依分類建立各段條件
    category_blocks = []
    for cat in categories:
        stores = cat.get("stores", [])
        if not stores:
            continue
        names = [s.get("name", "").strip() for s in stores if s.get("name", "").strip()]
        conditions = "\n        or ".join(
            [f'index(MERCH_NAME_CHT, "{n}") > 0' for n in names]
        )
        block = f"""    /* {cat['category_name']} */
    if {conditions}
    then TAG_{_to_var(label)}_{_to_var(cat['category_name'])} = 1;
    else TAG_{_to_var(label)}_{_to_var(cat['category_name'])} = 0;"""
        category_blocks.append(block)

    # 總標籤（任一分類命中即為1）
    sub_vars = " or ".join(
        [f"TAG_{_to_var(label)}_{_to_var(cat['category_name'])} = 1"
         for cat in categories if cat.get("stores")]
    )

    code = f"""/* ============================================================
   標籤名稱：{label}
   說    明：{summary}
   產生日期：{today}
   備    注：店家名稱請依實際資料庫欄位比對後調整
   ============================================================ */

data want;
    set your_table; /* ← 請替換成實際資料表名稱 */

{chr(10).join(category_blocks)}

    /* 總標籤：任一分類命中即標記為 1 */
    if {sub_vars}
    then TAG_{_to_var(label)} = 1;
    else TAG_{_to_var(label)} = 0;

run;

/* 驗證：檢查各標籤人數 */
proc freq data=want;
    tables TAG_{_to_var(label)}
{chr(10).join([f"           TAG_{_to_var(label)}_{_to_var(cat['category_name'])}" for cat in categories if cat.get("stores")])}
    / nocum nopercent;
run;
"""
    return code


def _to_var(text: str) -> str:
    """將中文或含空格的字串轉為 SAS 變數名稱友善格式（保留英數與底線）"""
    import re
    # 保留英數字與底線，其餘替換為底線
    cleaned = re.sub(r"[^\w]", "_", text, flags=re.UNICODE)
    # SAS 變數名最長 32 字元
    return cleaned[:32].strip("_")
