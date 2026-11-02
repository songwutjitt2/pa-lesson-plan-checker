import json
import streamlit as st
import requests
from docx import Document
from pypdf import PdfReader

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(
    page_title="ระบบตรวจสอบแผนการสอนตามเกณฑ์ ว.PA",
    page_icon="📋",
    layout="wide"
)

# --- ดึง API Key จาก Secrets หรือช่องกรอก ---
api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- ฟังก์ชันสกัดข้อความความเร็วสูง ---
def extract_text_from_file_fast(uploaded_file) -> str:
    text = ""
    filename = uploaded_file.name.lower()
    
    if filename.endswith(".docx"):
        doc = Document(uploaded_file)
        text_list = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_list.append(" | ".join(row_text))
        text = "\n".join(text_list)
                    
    elif filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        max_pages = min(len(reader.pages), 8)
        text_list = []
        for i in range(max_pages):
            extracted = reader.pages[i].extract_text()
            if extracted:
                text_list.append(extracted)
        text = "\n".join(text_list)
                
    # ตัดให้เหลือ 10,000 ตัวอักษรเพื่อความเร็วสูงสุด
    return text[:10000]

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    
    if not api_key:
        api_key = st.text_input("ระบุ Google Gemini API Key:", type="password")
    
    st.subheader("🎯 ระดับวิทยฐานะเป้าหมาย")
    target_rank = st.selectbox(
        "เลือกวิทยฐานะที่ต้องการประเมิน:",
        [
            "ครู (ปรับประยุกต์ - Applying and Adapting)",
            "ครูชำนาญการ (แก้ปัญหา - Solving the Problem)",
            "ครูชำนาญการพิเศษ (ริเริ่ม พัฒนา - Initiative and Developing)",
            "ครูเชี่ยวชาญ (คิดค้น ปรับเปลี่ยน - Inventing and Transforming)",
            "ครูเชี่ยวชาญพิเศษ (สร้างการเปลี่ยนแปลง - Creating an Impact)"
        ],
        index=1
    )
    
    st.markdown("---")
    st.markdown(
        "**ผู้พัฒนา:**\n\n"
        "**นายทรงวุฒิ จิตรประเสริฐ**  \n"
        "วิทยฐานะ ครูชำนาญการ  \n"
        "โรงเรียนวัดนางสาว (ถาวรราษฎร์บำรุง)"
    )

# --- หน้าจอหลัก ---
st.title("📋 โปรแกรม AI ตรวจสอบและประเมินแผนการจัดการเรียนรู้ (ว.PA)")
st.caption("⚡ วิเคราะห์ด่วน: 11 องค์ประกอบ | 8 ตัวชี้วัดการจัดการเรียนรู้ | Constructive Alignment | การตอบโจทย์วิทยฐานะ")

uploaded_file = st.file_uploader("แนบไฟล์แผนการสอนที่ต้องการตรวจสอบ (.docx หรือ .pdf)", type=["docx", "pdf"])

if st.button("⚡ เริ่มวิเคราะห์แผนการสอนแบบด่วน", type="primary"):
    if not api_key:
        st.error("กรุณาระบุ Google Gemini API Key ก่อนเริ่มวิเคราะห์")
    elif not uploaded_file:
        st.warning("กรุณาแนบไฟล์แผนการสอน (.docx หรือ .pdf)")
    else:
        status_box = st.empty()
        status_box.info("⚡ กำลังอ่านเนื้อหาเอกสาร...")

        try:
            plan_text = extract_text_from_file_fast(uploaded_file)
            if not plan_text.strip():
                st.error("ไม่สามารถอ่านข้อความจากไฟล์ได้ กรุณาตรวจสอบเอกสาร")
                st.stop()

            status_box.info("🤖 AI กำลังประเมินผลตามเกณฑ์ ว.PA (กำลังส่งข้อมูล)...")

            system_prompt = f"""
คุณคือผู้เชี่ยวชาญการประเมินวิทยฐานะ ว.PA วิเคราะห์แผนการสอนนี้แบบกระชับ ตรงประเด็น วิทยฐานะ: '{target_rank}'
ตอบกลับเป็น JSON ตามโครงสร้างนี้เท่านั้น (ห้ามใส่ Markdown อื่นนอกเหนือจาก JSON):
{{
  "overall_score": 85,
  "rank_status": "ผ่านเกณฑ์ / ต้องปรับปรุง",
  "is_assessment_aligned": true,
  "strengths": ["จุดเด่น 1", "จุดเด่น 2"],
  "weaknesses": ["จุดด้อย 1", "จุดด้อย 2"],
  "actionable_recommendations": ["ข้อเสนอแนะ 1", "ข้อเสนอแนะ 2"],
  "structural_elements_11": [
    {{"name": "1. หัวเรื่องและเวลา", "status": "Pass", "comment": "..."}},
    {{"name": "2. มาตรฐาน/ตัวชี้วัด", "status": "Pass", "comment": "..."}},
    {{"name": "3. สาระสำคัญ", "status": "Pass", "comment": "..."}},
    {{"name": "4. สาระการเรียนรู้", "status": "Pass", "comment": "..."}},
    {{"name": "5. จุดประสงค์ KPA", "status": "Pass", "comment": "..."}},
    {{"name": "6. สมรรถนะ/คุณลักษณะ", "status": "Pass", "comment": "..."}},
    {{"name": "7. ภาระงาน/ชิ้นงาน", "status": "Pass", "comment": "..."}},
    {{"name": "8. กิจกรรมการเรียนรู้", "status": "Pass", "comment": "..."}},
    {{"name": "9. สื่อ/แหล่งเรียนรู้", "status": "Pass", "comment": "..."}},
    {{"name": "10. การวัดและประเมินผล", "status": "Warning", "comment": "..."}},
    {{"name": "11. บันทึกหลังสอน", "status": "Pass", "comment": "..."}}
  ],
  "pa_indicators_8": [
    {{"id": 1, "name": "การเข้าถึงสิ่งที่เรียน", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 2, "name": "การเชื่อมโยงความรู้", "score": 3, "evidence": "...", "suggestion": "..."}},
    {{"id": 3, "name": "การกระตุ้นและจูงใจ", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 4, "name": "การพัฒนาทักษะ/แก้ปัญหา", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 5, "name": "ข้อมูลสะท้อนกลับ", "score": 3, "evidence": "...", "suggestion": "..."}},
    {{"id": 6, "name": "บรรยากาศชั้นเรียน", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 7, "name": "การกำกับการเรียนรู้ตนเอง", "score": 3, "evidence": "...", "suggestion": "..."}},
    {{"id": 8, "name": "ผลลัพธ์ตามจุดประสงค์", "score": 4, "evidence": "...", "suggestion": "..."}}
  ],
  "assessment_analysis": {{
    "overview": "...",
    "issues": [
      {{"objective": "...", "found": "...", "fix": "..."}}
    ]
  }},
  "rank_readiness_comment": "..."
}}
"""

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": system_prompt},
                            {"text": f"เนื้อหาแผนการสอน:\n\n{plan_text}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }

            # ยิงตรงผ่าน REST API พร้อมระบบ Timeout ไม่ให้หน้าค้าง
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
            
            resp = requests.post(
                url, 
                headers={"Content-Type": "application/json"}, 
                data=json.dumps(payload), 
                timeout=30
            )

            status_box.empty()

            if resp.status_code != 200:
                st.error(f"เกิดข้อผิดพลาดจาก Gemini API (รหัส {resp.status_code}): {resp.text}")
                st.stop()

            res_data = resp.json()
            raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            result = json.loads(raw_text.strip())

            # --- แสดงผล Dashboard ---
            st.success("✅ วิเคราะห์แผนการสอนเสร็จสิ้นเรียบร้อยแล้ว!")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("คะแนนภาพรวม", f"{result.get('overall_score', 0)} / 100")
            col2.metric("สถานะตามเกณฑ์วิทยฐานะ", result.get('rank_status', 'ผ่านเกณฑ์'))
            col3.metric("ความสอดคล้องการวัดผล", "สอดคล้อง" if result.get('is_assessment_aligned', False) else "ต้องปรับปรุง")
            
            st.markdown("---")

            tab1, tab2, tab3, tab4 = st.tabs([
                "📌 จุดเด่น - จุดด้อย & ข้อเสนอแนะ",
                "🎯 8 ตัวชี้วัด ว.PA",
                "📐 11 องค์ประกอบของแผน",
                "📊 การวัดและประเมินผล & วิทยฐานะ"
            ])

            with tab1:
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🌟 จุดเด่นของแผน")
                    for item in result.get("strengths", []):
                        st.write(f"- {item}")
                with c2:
                    st.subheader("⚠️ จุดด้อย / ข้อบกพร่องที่ต้องระวัง")
                    for item in result.get("weaknesses", []):
                        st.write(f"- {item}")
                
                st.subheader("💡 ข้อเสนอแนะเพื่อการปรับปรุงให้ตรงเกณฑ์")
                for item in result.get("actionable_recommendations", []):
                    st.info(f"👉 {item}")

            with tab2:
                st.subheader("การประเมิน 8 ตัวชี้วัดการจัดการเรียนรู้ (ว.PA)")
                for ind in result.get("pa_indicators_8", []):
                    with st.expander(f"ตัวชี้วัดที่ {ind.get('id')}: {ind.get('name')} — ได้ {ind.get('score')}/4 คะแนน"):
                        st.write(f"**การวิเคราะห์/หลักฐานที่พบ:** {ind.get('evidence')}")
                        if ind.get("suggestion"):
                            st.write(f"**ข้อแนะนำเพิ่มเติม:** {ind.get('suggestion')}")

            with tab3:
                st.subheader("ความครบถ้วนของ 11 องค์ประกอบพื้นฐาน")
                for elem in result.get("structural_elements_11", []):
                    status = elem.get("status", "Pass")
                    icon = "✅" if status == "Pass" else ("⚠️" if status == "Warning" else "❌")
                    st.write(f"{icon} **{elem.get('name')}**: {elem.get('comment')}")

            with tab4:
                st.subheader("🎯 การวิเคราะห์ความสอดคล้องของการวัดผล (Constructive Alignment)")
                st.write(f"**บทวิเคราะห์ภาพรวม:** {result.get('assessment_analysis', {}).get('overview', '')}")
                
                issues = result.get('assessment_analysis', {}).get('issues', [])
                if issues:
                    st.warning("ประเด็นความไม่สอดคล้องของการวัดผลที่ตรวจพบ:")
                    for issue in issues:
                        st.write(f"- **จุดประสงค์:** {issue.get('objective')}")
                        st.write(f"  **สิ่งที่พบในแผน:** {issue.get('found')}")
                        st.write(f"  **ข้อแก้ไข:** {issue.get('fix')}")
                else:
                    st.success("การวัดและประเมินผลมีความสอดคล้องกับจุดประสงค์ K-P-A ครบถ้วน")

                st.markdown("---")
                st.subheader(f"🎖️ ความสอดคล้องกับวิทยฐานะ: {target_rank}")
                st.write(result.get("rank_readiness_comment", ""))

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}")

# ส่วนท้าย
st.markdown("---")
st.markdown(
    "<center><small>โปรแกรมตรวจสอบแผนการจัดการเรียนรู้ ว.PA | พัฒนาโดย นายทรงวุฒิ จิตรประเสริฐ วิทยฐานะ ครูชำนาญการ โรงเรียนวัดนางสาว (ถาวรราษฎร์บำรุง)</small></center>",
    unsafe_allow_html=True
)
