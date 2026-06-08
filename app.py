import streamlit as st
from tagger import analyze_label
from pptx_builder import build_pptx
from sas_template import build_sas_code

st.set_page_config(
    page_title="客戶標籤分析工具",
    page_icon="🏷️",
    layout="wide",
)

st.title("🏷️ 客戶樣貌標籤分析工具")
st.caption("輸入標籤名稱，AI 自動歸納對應特店、搜尋網路資料，並產出簡報與 SAS code")

# --- 輸入區 ---
with st.form("label_form"):
    label_input = st.text_input(
        "標籤名稱",
        placeholder="例如：健身運動、寵物消費、親子娛樂",
        help="輸入你想分析的客戶消費標籤",
    )
    submitted = st.form_submit_button("🔍 開始分析", use_container_width=True)

# --- 分析流程 ---
if submitted:
    if not label_input.strip():
        st.warning("請輸入標籤名稱")
    else:
        with st.spinner(f"AI 正在分析「{label_input}」並搜尋網路資料，約需 15-30 秒..."):
            try:
                result = analyze_label(label_input.strip())
                st.session_state["result"] = result
                st.session_state["label"] = label_input.strip()
            except RuntimeError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"發生未預期的錯誤，請稍後再試。\n\n詳細訊息：{e}")

# --- 結果顯示 ---
if "result" in st.session_state:
    result = st.session_state["result"]
    label = st.session_state["label"]

    if "raw_response" in result:
        st.error("AI 回應格式異常，請重試")
        st.code(result["raw_response"])
    else:
        st.success(f"分析完成！共找到 {sum(len(c.get('stores', [])) for c in result.get('categories', []))} 家特店")

        # 說明
        st.info(f"**標籤說明：** {result.get('summary', '')}")

        tab1, tab2, tab3 = st.tabs(["📋 店家清單", "💻 SAS Code", "📥 下載簡報"])

        # --- Tab 1: 店家清單 ---
        with tab1:
            for cat in result.get("categories", []):
                with st.expander(
                    f"**{cat['category_name']}**（{len(cat.get('stores', []))} 家）",
                    expanded=True,
                ):
                    st.caption(f"挑選原因：{cat.get('reason', '')}")
                    stores = cat.get("stores", [])
                    if stores:
                        rows = []
                        for s in stores:
                            source = s.get("source", "")
                            # 如果是網址就加連結
                            if source.startswith("http"):
                                source_display = f"[連結]({source})"
                            else:
                                source_display = source
                            rows.append({
                                "店家 / 品牌": s.get("name", ""),
                                "說明": s.get("note", ""),
                                "來源": source_display,
                            })
                        st.dataframe(rows, use_container_width=True, hide_index=True)

        # --- Tab 2: SAS Code ---
        with tab2:
            sas_code = build_sas_code(result)
            st.code(sas_code, language="sas")
            st.download_button(
                label="📋 複製並下載 SAS Code",
                data=sas_code.encode("utf-8"),
                file_name=f"tag_{label}.sas",
                mime="text/plain",
            )
            st.caption("⚠️ 店家名稱與變數名稱請依實際 SAS 資料庫欄位格式調整")

        # --- Tab 3: 下載簡報 ---
        with tab3:
            st.write("點擊下方按鈕產生並下載 PowerPoint 簡報（.pptx）")
            st.write("下載後可用 PowerPoint 或 Google 簡報開啟編輯")

            pptx_buf = build_pptx(result)
            st.download_button(
                label="⬇️ 下載 PowerPoint 簡報",
                data=pptx_buf,
                file_name=f"標籤分析_{label}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
