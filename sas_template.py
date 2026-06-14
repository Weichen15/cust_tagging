import re
from datetime import date


def _to_var(text: str) -> str:
    """標籤/分類名 → SAS 變數名（保留英數字、底線、中文，最長 32 字元）"""
    cleaned = re.sub(r"[^\w]", "_", text, flags=re.UNICODE)
    return cleaned[:32].strip("_")


def _is_chinese(text: str) -> bool:
    return bool(re.search(r"[一-鿿＀-￯]", text))


def _sql_cond(name: str) -> str:
    """PROC SQL WHERE 用的 INDEX 條件"""
    if _is_chinese(name):
        return f'INDEX(UPCASE(MERCHANT_CHI_NAME), "{name}") > 0'
    return f'INDEX(UPCASE(MERCHANT_ENG_NAME), "{name.upper()}") > 0'


def _data_cond(name: str) -> str:
    """DATA step IF 用的 INDEX 條件（搭配 UMCHT_* 欄位）"""
    if _is_chinese(name):
        return f'INDEX(UMCHT_CNAME, "{name}") > 0'
    return f'INDEX(UMCHT_ENAME, "{name.upper()}") > 0'


def _cond_block(categories: list, cond_fn, indent: str) -> str:
    """
    組合 OR 條件區塊。第一個條件不加 OR（改為空格對齊），
    各分類前插入 /* 分類名 */ 說明。
    """
    lines = []
    first = True
    for cat in categories:
        names = [
            s.get("name", "").strip()
            for s in cat.get("stores", [])
            if s.get("name", "").strip()
        ]
        if not names:
            continue
        lines.append(f"{indent}/* {cat.get('category_name', '')} */")
        for n in names:
            prefix = "   " if first else "OR "
            lines.append(f"{indent}{prefix}{cond_fn(n)}")
            first = False
    return "\n".join(lines)


def build_sas_code(data: dict) -> str:
    label      = data.get("label", "LABEL")
    summary    = data.get("summary", "")
    categories = data.get("categories", [])
    today      = date.today().strftime("%Y%m%d")
    lv         = _to_var(label)

    sql_block  = _cond_block(categories, _sql_cond,  "\t\t")
    data_block = _cond_block(categories, _data_cond, "\t")

    return (
        f"/* {'='*60}\n"
        f"   標籤名稱：{label}\n"
        f"   說    明：{summary}\n"
        f"   產生日期：{today}\n"
        f"   備    注：\n"
        f"     - 請依實際環境調整 TRANSACTION_TABLE、MCC_CODE_TABLE、LIBNAME 路徑\n"
        f"     - 中文店家若含全形字元，請確認 MERCHANT_CHI_NAME 實際格式後調整\n"
        f"     - 強度閾值（INT_{lv}）請依 Step 8 百分位結果人工調整\n"
        f"   {'='*60} */\n"
        f"\n"
        f'%INCLUDE "PATH\\PW.sas";\n'
        f"\n"
        f"OPTIONS VALIDVARNAME = ANY;\n"
        f'LIBNAME ... META LIBRARY="...." REPNAME="FOUNDATION";\n'
        f"\n"
        f"/* ── Step 1: 建立日期 Macro 變數 ─────────────────────────────── */\n"
        f"DATA _NULL_;\n"
        f'\tCALL SYMPUT("P1Y",  PUT(INTNX("MONTH",TODAY(),-12,"B"), YYMMDDN8.));  /* 去年同月初 */\n'
        f'\tCALL SYMPUT("L1M",  PUT(INTNX("MONTH",TODAY(),-1, "E"), YYMMDDN8.));  /* 上個月底   */\n'
        f'\tCALL SYMPUT("P1M",  PUT(INTNX("MONTH",TODAY(),-1),      YYMMN6.));    /* 上個月     */\n'
        f'\tCALL SYMPUT("P2M",  PUT(INTNX("MONTH",TODAY(),-2),      YYMMN6.));\n'
        f'\tCALL SYMPUT("P3M",  PUT(INTNX("MONTH",TODAY(),-3),      YYMMN6.));\n'
        f'\tCALL SYMPUT("DT",   PUT(TODAY()-1,                       YYMMDDN8.));  /* 昨天       */\n'
        f'\tCALL SYMPUT("P1D",  PUT(INTNX("MONTH",TODAY()-1,0,"S"), YYMMDDN8.));  /* 當月初     */\n'
        f"RUN;\n"
        f"%PUT &P1Y &L1M &P1M &P2M &P3M &DT &P1D;\n"
        f"\n"
        f"/* ── Step 2: 撈取 {label} 相關交易資料 ──────────────────────── */\n"
        f"PROC SQL;\n"
        f"\tCREATE TABLE INT_{lv}_PRE (COMPRESS=YES) AS\n"
        f"\tSELECT CST_ID,\n"
        f'\t\tSUBSTR(DATE, 1, 6)    AS YYYYMM,\n'
        f"\t\tMERCHANT_CHI_NAME     AS MCHT_NAME,\n"
        f"\t\tMERCHANT_ENG_NAME     AS MCHT_ENAME,\n"
        f"\t\tMCC_CODE              AS MCC_ID,\n"
        f"\t\tAMT\n"
        f"\tFROM TRANSACTION_TABLE AS A\n"
        f'\t\tLEFT JOIN (SELECT * FROM MCC_CODE_TABLE WHERE YYYYMMDD="&P1D") AS F\n'
        f"\t\t\tON A.MCC_CODE = F.MCC_CODE\n"
        f'\tWHERE DATE >= "&P1Y."\n'
        f'\t\tAND DATE <= "&L1M."\n'
        f"\t\tAND AMT > 0\n"
        f"\t\tAND (\n"
        f"{sql_block}\n"
        f"\t\t)\n"
        f"\t;\n"
        f"QUIT;\n"
        f"\n"
        f"/* ── Step 3: 認列判斷（IDENTIFIED）─────────────────────────── */\n"
        f"DATA INT_{lv}_PRE1 (COMPRESS=YES);\n"
        f"\tSET INT_{lv}_PRE;\n"
        f"\tLENGTH IDENTIFIED $10.;\n"
        f"\n"
        f"\tUMCHT_ENAME = UPCASE(MCHT_ENAME);\n"
        f"\tUMCHT_CNAME = KPROPCASE(UPCASE(KPROPCASE(MCHT_NAME,\n"
        f"\t\t'FULL-ALPHABET,HALF-ALPHABET')), 'HALF-ALPHABET,FULL-ALPHABET');\n"
        f"\n"
        f"\tIF (\n"
        f"{data_block}\n"
        f"\t)\n"
        f"\tTHEN IDENTIFIED = '已認列';\n"
        f"\tELSE IDENTIFIED = '未認列';\n"
        f"RUN;\n"
        f"\n"
        f"/* ── Step 4: 計算認列金額（AMT_MACH）與筆數（TXN_MACH）──────── */\n"
        f"PROC SQL;\n"
        f"\tCREATE TABLE INT_{lv}_MACH (COMPRESS=YES) AS\n"
        f"\tSELECT *,\n"
        f'\t\tCASE WHEN (IDENTIFIED="已認列") THEN AMT ELSE 0 END AS AMT_MACH,\n'
        f'\t\tCASE WHEN (IDENTIFIED="已認列") THEN 1   ELSE 0 END AS TXN_MACH\n'
        f"\tFROM INT_{lv}_PRE1\n"
        f"\t;\n"
        f"QUIT;\n"
        f"\n"
        f"PROC FREQ DATA=INT_{lv}_MACH;\n"
        f"\tTABLE IDENTIFIED;\n"
        f"RUN;\n"
        f"/*\n"
        f"\t*{today}: Ori: N; N   <- 執行後請填入認列/未認列筆數\n"
        f"*/\n"
        f"\n"
        f"/* ── Step 5: 彙總（依客戶＋月份）──────────────────────────────── */\n"
        f"PROC SUMMARY DATA=INT_{lv}_MACH NWAY MISSING;\n"
        f'\tWHERE IDENTIFIED = "已認列";\n'
        f"\tCLASS CST_ID YYYYMM;\n"
        f"\tVAR AMT_MACH TXN_MACH;\n"
        f"\tOUTPUT OUT=INT_{lv}_MACH2 (DROP=_TYPE_ _FREQ_) SUM=;\n"
        f"RUN;\n"
        f"\n"
        f"/* ── Step 6: 彙總（依客戶，取得消費月數 DIFF_MONTH_MACH）──────── */\n"
        f"PROC SUMMARY DATA=INT_{lv}_MACH2 NWAY MISSING;\n"
        f"\tCLASS CST_ID;\n"
        f"\tVAR AMT_MACH TXN_MACH;\n"
        f"\tOUTPUT OUT=INT_{lv}_MACH3\n"
        f"\t\t(DROP=_TYPE_ RENAME=(_FREQ_=DIFF_MONTH_MACH)) SUM=;\n"
        f"RUN;\n"
        f"\n"
        f"/* ── Step 7: 統計確認 ────────────────────────────────────────── */\n"
        f"\n"
        f"/* STAT1: 特店名稱確認表 */\n"
        f"PROC TABULATE DATA=INT_{lv}_MACH MISSING;\n"
        f'\tTITLE "MERCHANT 確認表, 資料日期: &P1Y. ~ &L1M.";\n'
        f"\tCLASS MCHT_NAME MCHT_ENAME IDENTIFIED;\n"
        f"\tVAR AMT_MACH TXN_MACH;\n"
        f'\tTABLES MCHT_NAME="" * MCHT_ENAME="",\n'
        f'\t\tIDENTIFIED="" * (AMT_MACH="Amount" TXN_MACH="Transaction") * SUM="";\n'
        f"RUN;\n"
        f"\n"
        f"/* STAT2: 消費人數/消費金額/消費次數/客單價 */\n"
        f"PROC SUMMARY DATA=INT_{lv}_MACH3 NWAY MISSING;\n"
        f"\tWHERE AMT_MACH > 0;\n"
        f"\tVAR AMT_MACH TXN_MACH;\n"
        f"\tOUTPUT OUT=TICKET_SIZE (DROP=_TYPE_ RENAME=(_FREQ_=CIF)) SUM=;\n"
        f"RUN;\n"
        f"\n"
        f"DATA TICKET_SIZE;\n"
        f"\tSET TICKET_SIZE;\n"
        f"\tTICKET_SIZE = AMT_MACH / TXN_MACH;\n"
        f"RUN;\n"
        f"\n"
        f"PROC PRINT DATA=TICKET_SIZE NOOBS;\n"
        f"\tTITLE '消費人數/消費金額/消費次數/平均消費金額';\n"
        f"RUN;\n"
        f"\n"
        f"/* STAT3: 單筆金額最大最小值 */\n"
        f"PROC SQL;\n"
        f"\tCREATE TABLE MAX_MIN AS\n"
        f"\tSELECT MAX(AMT_MACH) AS MAX_AMT,\n"
        f"\t\tMIN(AMT_MACH) AS MIN_AMT\n"
        f"\tFROM INT_{lv}_MACH\n"
        f'\tWHERE IDENTIFIED = "已認列"\n'
        f"\t;\n"
        f"QUIT;\n"
        f"\n"
        f"PROC PRINT DATA=MAX_MIN NOOBS;\n"
        f"\tTITLE '單筆金額最大最小值';\n"
        f"RUN;\n"
        f"\n"
        f"/* STAT4: 單筆消費前 10 大 */\n"
        f"PROC SORT DATA=INT_{lv}_MACH;\n"
        f"\tBY DESCENDING AMT_MACH;\n"
        f"RUN;\n"
        f"\n"
        f"DATA TOP10;\n"
        f"\tSET INT_{lv}_MACH;\n"
        f"\tIF _N_ <= 10;\n"
        f"RUN;\n"
        f"\n"
        f"PROC PRINT DATA=TOP10;\n"
        f"\tTITLE '單筆消費前10大';\n"
        f"RUN;\n"
        f"\n"
        f"/* STAT5: 極端值統計 */\n"
        f"PROC SUMMARY DATA=INT_{lv}_MACH3 NWAY MISSING;\n"
        f"\tWHERE AMT_MACH > 0;\n"
        f"\tVAR AMT_MACH TXN_MACH DIFF_MONTH_MACH;\n"
        f"\tOUTPUT OUT=AVG (DROP=_TYPE_ _FREQ_);\n"
        f"RUN;\n"
        f"\n"
        f"PROC PRINT DATA=AVG NOOBS;\n"
        f"\tTITLE '極端值統計數字';\n"
        f"RUN;\n"
        f"\n"
        f"/* STAT6: 消費月數分布 */\n"
        f"PROC FREQ DATA=INT_{lv}_MACH3;\n"
        f"\tTITLE '消費月數分布';\n"
        f"\tWHERE AMT_MACH > 0;\n"
        f"\tTABLES DIFF_MONTH_MACH / LIST MISSING;\n"
        f"RUN;\n"
        f"\n"
        f"/* ── Step 8: 百分位分析 ─────────────────────────────────────── */\n"
        f"PROC UNIVARIATE DATA=INT_{lv}_MACH3 NOPRINT;\n"
        f"\tWHERE AMT_MACH > 0;\n"
        f"\tVAR AMT_MACH;\n"
        f"\tOUTPUT OUT=PERCENTILE_AMT PCTLPTS= 25 50 75 90 95 99 PCTLPRE= PCT_;\n"
        f"RUN;\n"
        f"PROC PRINT DATA=PERCENTILE_AMT NOOBS;\n"
        f"\tTITLE '消費金額百分位';\n"
        f"RUN;\n"
        f"\n"
        f"PROC UNIVARIATE DATA=INT_{lv}_MACH3 NOPRINT;\n"
        f"\tWHERE TXN_MACH > 0;\n"
        f"\tVAR TXN_MACH;\n"
        f"\tOUTPUT OUT=PERCENTILE_TXN PCTLPTS= 25 50 75 90 95 99 PCTLPRE= PCT_;\n"
        f"RUN;\n"
        f"PROC PRINT DATA=PERCENTILE_TXN NOOBS;\n"
        f"\tTITLE '消費次數百分位';\n"
        f"RUN;\n"
        f"\n"
        f"PROC UNIVARIATE DATA=INT_{lv}_MACH3 NOPRINT;\n"
        f"\tWHERE AMT_MACH > 0;\n"
        f"\tVAR DIFF_MONTH_MACH;\n"
        f"\tOUTPUT OUT=PERCENTILE_MONTH PCTLPTS= 25 50 75 90 95 99 PCTLPRE= PCT_;\n"
        f"RUN;\n"
        f"PROC PRINT DATA=PERCENTILE_MONTH NOOBS;\n"
        f"\tTITLE '消費月數百分位';\n"
        f"RUN;\n"
        f"\n"
        f"/* ── Step 9: 貼標輸出（INT_{lv}）────────────────────────────── */\n"
        f"DATA _NULL_;\n"
        f"\tCALL SYMPUT(\"P1M6\", PUT(INTNX(\"MONTH\",TODAY(),-1,'E'), YYMMN6.));\n"
        f"RUN;\n"
        f'LIBNAME DATA "PATH\\&P1M6";\n'
        f"\n"
        f"/* ⚠️ 強度閾值請依 Step 8 PERCENTILE_MONTH 結果人工調整 */\n"
        f"PROC SQL;\n"
        f"\tCREATE TABLE DATA.INT_{lv} (COMPRESS=YES) AS\n"
        f"\tSELECT DISTINCT CST_ID,\n"
        f"\t\tCASE\n"
        f"\t\t\tWHEN DIFF_MONTH_MACH >= 7 /* 消費月數 ~80% 位 <- 請調整 */ THEN 1\n"
        f"\t\t\tWHEN DIFF_MONTH_MACH >= 3 /* 消費月數 ~50% 位 <- 請調整 */ THEN 2\n"
        f"\t\t\tWHEN DIFF_MONTH_MACH >  0                                   THEN 3\n"
        f"\t\tEND AS INT_{lv}\n"
        f"\tFROM INT_{lv}_MACH3\n"
        f"\t;\n"
        f"QUIT;\n"
        f"\n"
        f"PROC FREQ DATA=DATA.INT_{lv};\n"
        f"\tTABLE INT_{lv};\n"
        f"RUN;\n"
    )
