import json
import streamlit as st
from docx import Document
from google import genai
from google.genai import types
from pypdf import PdfReader

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(
    page_title="ระบบตรวจสอบแผนการสอนตามเกณฑ์ ว.PA",
    page_icon="📋",
    layout="wide"
)

# --- ดึง API Key จาก Secrets หรือช่องกรอก ---
api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- ฟังก์ชันสกัดข้อความจากเอกสาร (.docx และ .pdf) ---
def extract_text_from_file(uploaded_file) -> str:
    text = ""
    filename = uploaded_file.name.lower()
    
    # กรณีเป็นไฟล์ DOCX (ดึงทั้งย่อหน้าและตาราง)
    if filename.endswith(".docx"):
        doc = Document(uploaded_file)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text += "\n" + " | ".join(row_text)
                    
    # กรณีเป็นไฟล์ PDF
    elif filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
                
    return text

# --- เมนูด้านข้าง (Sidebar) ---
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    
    # หากไม่ได้ตั้ง Secrets ไว้ จะให้กรอกผ่านหน้าเว็บ
    if not api_key:
        api_key = st.text_input("ระบุ Google Gemini API Key:", type="password")
        st.caption("สามารถนำ API Key ไปใส่ใน Secrets ของ Streamlit Cloud เพื่อความสะดวกได้")
    
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

# --- ส่วนแสดงผลหลัก ---
st.title("📋 โปรแกรม AI ตรวจสอบและประเมินแผนการจัดการเรียนรู้ (ว.PA)")
st.caption("วิเคราะห์ 11 องค์ประกอบ | 8 ตัวชี้วัดการจัดการเรียนรู้ | Constructive Alignment | การตอบโจทย์วิทยฐานะ")

uploaded_file = st.file_uploader("แนบไฟล์แผนการสอนที่ต้องการตรวจสอบ (.docx หรือ .pdf)", type=["docx", "pdf"])

if st.button("🚀 เริ่มวิเคราะห์แผนการสอน", type="primary"):
    if not api_key:
        st.error("กรุณาระบุ Google Gemini API Key ก่อนเริ่มวิเคราะห์")
    elif not uploaded_file:
        st.warning("กรุณาแนบไฟล์แผนการสอน (.docx หรือ .pdf)")
    else:
        with st.spinner("⚡ กำลังอ่านเนื้อหาเอกสารและวิเคราะห์ตามเกณฑ์ ว.PA..."):
            try:
                # 1. สกัดข้อความ
                plan_text = extract_text_from_file(uploaded_file)
                if not plan_text.strip():
                    st.error("ไม่สามารถอ่านข้อความจากไฟล์ได้ กรุณาตรวจสอบว่าเป็นไฟล์เอกสารที่มีตัวหนังสือพิมพ์")
                    st.stop()

                # 2. เตรียมคำสั่งการประเมิน
                client = genai.Client(api_key=api_key)
                
                system_instruction = f"""
คุณคือผู้เชี่ยวชาญด้านการประเมินวิทยฐานะข้าราชการครูตามเกณฑ์ ว.PA (ก.ค.ศ.) และผู้เชี่ยวชาญด้านหลักสูตรและการจัดการเรียนรู้
ตรวจสอบและวิเคราะห์แผนการจัดการเรียนรู้ที่ส่งมาอย่างละเอียด เข้มข้น และตรงไปตรงมา โดยอิงตามระดับวิทยฐานะ: '{target_rank}'

กรอบการประเมิน:
1. ตรวจสอบ 11 องค์ประกอบโครงสร้างแผน (ครบถ้วน/ไม่ครบ/ขาดหาย)
2. ประเมิน 8 ตัวชี้วัดการจัดการเรียนรู้ ว.PA (คะแนน 1-4 พร้อมยกหลักฐานในแผน)
3. ตรวจสอบ Constructive Alignment: จุดประสงค์ (K, P, A) สอดคล้องกับกิจกรรม วิธีวัด เครื่องมือวัด และเกณฑ์การประเมินหรือไม่
4. วิเคราะห์การตอบโจทย์วิทยฐานะเป้าหมาย (เช่น หากเป็น 'ครูชำนาญการ' ต้องแสดงให้เห็นการ 'แก้ปัญหา' ผู้เรียนชัดเจน มีการวัดผลก่อน-หลัง หรือเทคนิคแก้จุดอ่อนเฉพาะทาง)
5. สรุปจุดเด่น จุดด้อย/ข้อควรระวัง และข้อเสนอแนะในการปรับปรุงที่ชัดเจน นำไปแก้ไขได้ทันที

ส่งผลลัพธ์กลับมาเป็นโครงสร้าง JSON ตาม Schema นี้เท่านั้น:
{{
  "overall_score": 85,
  "rank_status": "ผ่านเกณฑ์ / ต้องปรับปรุง",
  "is_assessment_aligned": true,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "actionable_recommendations": ["...", "..."],
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
    {{"id": 1, "name": "การเข้าถึงสิ่งที่เรียนและเข้าใจบทเรียน", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 2, "name": "การเชื่อมโยงความรู้เดิมสู่ความรู้ใหม่", "score": 3, "evidence": "...", "suggestion": "..."}},
    {{"id": 3, "name": "การกระตุ้นและสร้างแรงจูงใจ", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 4, "name": "การพัฒนาทักษะและการแก้ปัญหา", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 5, "name": "การให้ข้อมูลสะท้อนกลับ (Feedback)", "score": 3, "evidence": "...", "suggestion": "..."}},
    {{"id": 6, "name": "บรรยากาศชั้นเรียนที่ส่งเสริมการเรียนรู้", "score": 4, "evidence": "...", "suggestion": "..."}},
    {{"id": 7, "name": "การกำกับการเรียนรู้และการทำงานตนเอง", "score": 3, "evidence": "...", "suggestion": "..."}},
    {{"id": 8, "name": "การเกิดผลลัพธ์ตามจุดประสงค์การเรียนรู้", "score": 4, "evidence": "...", "suggestion": "..."}}
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

                # ระบบสลับโมเดลอัตโนมัติ (Fallback) ป้องกัน Error 503 เซิร์ฟเวอร์หนาแน่น
                candidate_models = [
                    'gemini-3.8-flash',
                    'gemini-flash-latest',
                    'gemini-2.5-flash'
                ]
                
                result = None
                last_error = None

                for model_name in candidate_models:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                f"นี่คือข้อความในแผนการสอน:\n\n{plan_text[:30000]}"
                            ],
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                response_mime_type="application/json",
                                temperature=0.1
                            )
                        )
                        result = json.loads(response.text)
                        if result:
                            break
                    except Exception as err:
                        last_error = err
                        continue

                if not result:
                    raise Exception(f"เซิร์ฟเวอร์ AI มีผู้ใช้งานหนาแน่นชั่วคราว: {last_error}")

                # 3. นำผลลัพธ์แสดงบนหน้าเว็บ
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
