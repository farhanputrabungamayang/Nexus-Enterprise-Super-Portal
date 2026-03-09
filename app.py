import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime, timedelta
import os
import uuid
from passlib.hash import pbkdf2_sha256
import requests 
from fpdf import FPDF 
import google.generativeai as genai
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from PIL import Image

try: import PyPDF2
except ImportError: PyPDF2 = None

# ==========================================
# 1. KONFIGURASI HALAMAN UTAMA (SUPER PORTAL)
# ==========================================
st.set_page_config(page_title="Nexus Super Portal", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

CHART_THEME = "plotly_white"
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
        .lobby-title { background: linear-gradient(to right, #ffffff, #8892b0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 4rem; text-align: center; margin-bottom: 5px; letter-spacing: -1.5px; }
        .lobby-subtitle { color: #8892b0; font-size: 1.2rem; text-align: center; margin-bottom: 40px; font-weight: 400; letter-spacing: 0.5px; }
        div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 20px !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; background: linear-gradient(145deg, rgba(20, 25, 35, 0.6) 0%, rgba(10, 15, 25, 0.8) 100%) !important; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5) !important; backdrop-filter: blur(10px) !important; transition: transform 0.3s ease, box-shadow 0.3s ease, border 0.3s ease !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover { transform: translateY(-8px) !important; box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; }
        [data-testid="baseButton-primary"] { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important; color: #FFFFFF !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 12px !important; font-weight: 700 !important; font-size: 1.05rem !important; padding: 25px 0 !important; transition: all 0.3s ease !important; text-transform: uppercase !important; letter-spacing: 1.5px !important; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important; }
        [data-testid="baseButton-primary"]:hover { background: linear-gradient(135deg, #334155 0%, #1E293B 100%) !important; border: 1px solid rgba(255, 255, 255, 0.3) !important; box-shadow: 0 8px 25px rgba(255, 255, 255, 0.15) !important; transform: translateY(-2px) !important; color: #38BDF8 !important; }
        [data-testid="baseButton-secondary"] { border-radius: 10px !important; border: 1px solid #334155 !important; transition: all 0.3s ease !important; font-weight: 500 !important; }
        [data-testid="baseButton-secondary"]:hover { border-color: #94A3B8 !important; color: #FFFFFF !important; background-color: rgba(255, 255, 255, 0.05) !important; }
        div[data-testid="metric-container"] { border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; background-color: #f8f9fa; }
        marquee { font-size: 1.1rem; padding: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. KONFIGURASI AI
# ==========================================
WA_LINK = "https://chat.whatsapp.com/Dg09QTJ9f9gFemTnQoYM0o" 
if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model_hidup = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_hidup = m.name
                break 
        ai_model = genai.GenerativeModel(model_hidup) if model_hidup else None
    except: ai_model = None
else: ai_model = None

# ==========================================
# 3. DATABASE SETUP
# ==========================================
Base = declarative_base()
engine = create_engine('sqlite:///nexus_super_portal.db', connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
session = Session()

# --- MODEL BARU: AUDIT TRAIL (LOG AKTIVITAS) ---
class AdminLog(Base):
    __tablename__ = 'admin_logs'
    id = Column(Integer, primary_key=True)
    admin_username = Column(String(50), nullable=False)
    department = Column(String(50), nullable=False) # IT atau HR
    action = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)

class BroadcastMessage(Base):
    __tablename__ = 'broadcasts'
    id = Column(Integer, primary_key=True)
    message = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    department = Column(String(50), default='General')

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    full_name = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    email = Column(String(100), nullable=True)

class ITDocument(Base):
    __tablename__ = 'it_documents'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    file_path = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class HRDocument(Base):
    __tablename__ = 'hr_documents'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    file_path = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class ITUser(Base):
    __tablename__ = 'it_users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default='admin') 

class ITInventory(Base):
    __tablename__ = 'it_inventory'
    id = Column(Integer, primary_key=True)
    asset_name = Column(String(100), nullable=False)
    asset_type = Column(String(50), nullable=False)
    serial_number = Column(String(100), nullable=True)
    status = Column(String(50), default='Active')
    department = Column(String(50), nullable=True)

class ITFAQ(Base):
    __tablename__ = 'it_faqs'
    id = Column(Integer, primary_key=True)
    question = Column(String(200), nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class ITTicket(Base):
    __tablename__ = 'it_tickets'
    id = Column(Integer, primary_key=True)
    emp_username = Column(String(50), nullable=True) 
    requester_name = Column(String(100), nullable=False)
    requester_email = Column(String(100), nullable=True) 
    department = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    sentiment = Column(String(50), default='Netral') # FITUR BARU: SENTIMEN
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default='Open')
    assigned_to = Column(String(50), nullable=True) 
    created_at = Column(DateTime, default=datetime.now)
    image_path = Column(String(200), nullable=True)
    rating = Column(Integer, nullable=True) 
    feedback = Column(Text, nullable=True)
    device_id = Column(Integer, ForeignKey('it_inventory.id'), nullable=True)
    device = relationship('ITInventory')
    comments = relationship('ITComment', backref='ticket', cascade="all, delete-orphan")

class ITComment(Base):
    __tablename__ = 'it_comments'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('it_tickets.id'), nullable=False)
    sender = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    image_path = Column(String(200), nullable=True) 
    created_at = Column(DateTime, default=datetime.now)

def generate_ticket_token(): return f"HR-{uuid.uuid4().hex[:8].upper()}"

class HRUser(Base):
    __tablename__ = 'hr_users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default='admin') 

class HRFAQ(Base):
    __tablename__ = 'hr_faqs'
    id = Column(Integer, primary_key=True)
    question = Column(String(200), nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class HRTicket(Base):
    __tablename__ = 'hr_tickets'
    id = Column(String(20), primary_key=True, default=generate_ticket_token)
    emp_username = Column(String(50), nullable=True) 
    requester_name = Column(String(100), nullable=False)
    requester_email = Column(String(100), nullable=True) 
    department = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False) 
    priority = Column(String(20), nullable=False)
    sentiment = Column(String(50), default='Netral') # FITUR BARU: SENTIMEN
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default='Open')
    assigned_to = Column(String(50), nullable=True) 
    created_at = Column(DateTime, default=datetime.now)
    image_path = Column(String(200), nullable=True)
    rating = Column(Integer, nullable=True) 
    feedback = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, default=False) 
    comments = relationship('HRComment', backref='ticket', cascade="all, delete-orphan")

class HRComment(Base):
    __tablename__ = 'hr_comments'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(String(20), ForeignKey('hr_tickets.id'), nullable=False)
    sender = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    image_path = Column(String(200), nullable=True) 
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

# ==========================================
# 4. FUNGSI HELPER GLOBAL & AI CORE
# ==========================================
def clean_text(text):
    if text is None: return "-"
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def save_uploaded_file(uploadedfile):
    if not os.path.exists("uploads"): os.makedirs("uploads")
    file_path = os.path.join("uploads", f"{datetime.now().timestamp()}_{uploadedfile.name}")
    with open(file_path, "wb") as f: f.write(uploadedfile.getbuffer())
    return file_path

def log_admin_action(username, dept, action):
    session.add(AdminLog(admin_username=username, department=dept, action=action))
    session.commit()

# --- FITUR MATA DEWA, SENTIMENT, AUTO TRIAGE ---
def get_ai_triage(subject, description):
    if not ai_model: return "Medium"
    prompt = f"Sebagai Juri Triage Enterprise, tentukan prioritas masalah ini HANYA dengan 1 KATA: Low, Medium, High, atau Critical.\nJudul: {subject}\nDetail: {description}"
    try:
        res = ai_model.generate_content(prompt).text.strip().replace('*', '')
        for v in ["Critical", "High", "Medium", "Low"]:
            if v.lower() in res.lower(): return v
        return "Medium"
    except: return "Medium"

def get_ai_sentiment(text):
    if not ai_model: return "Netral"
    try:
        res = ai_model.generate_content(f"Analisis sentimen dari laporan ini. Jawab HANYA dengan 1 KATA: Marah, Panik, Kecewa, Netral, atau Senang.\nTeks: {text}").text.strip().replace('*', '')
        for v in ["Marah", "Panik", "Kecewa", "Netral", "Senang"]:
            if v.lower() in res.lower(): return v
        return "Netral"
    except: return "Netral"

def get_ai_response_with_vision(prompt, image_path=None):
    if not ai_model: return "⚠️ AI Offline."
    try:
        contents = [prompt]
        if image_path and os.path.exists(image_path): contents.append(Image.open(image_path))
        return ai_model.generate_content(contents).text
    except Exception: return "⚠️ AI Gagal Membaca Detail/Gambar."

def it_get_ai_first_aid(subject, description, category, img_path=None):
    prompt = f"Sambut keluhan IT. Kategori: {category}, Masalah: {subject}, Detail: {description}. JIKA ADA GAMBAR TERLAMPIR, BACA DAN ANALISIS GAMBAR ITU (Misal: baca kode errornya). Berikan 2 langkah awal."
    return get_ai_response_with_vision(prompt, img_path)

def hr_get_ai_first_aid(subject, description, category, img_path=None):
    prompt = f"Sambut laporan HR secara empatik. Kategori: {category}, Masalah: {subject}. JIKA ADA GAMBAR (Misal kwitansi/surat dokter), sebutkan bahwa sistem telah merekam datanya. Berikan kalimat menenangkan."
    return get_ai_response_with_vision(prompt, img_path)

def show_broadcast(dept='General'):
    msgs = session.query(BroadcastMessage).filter_by(is_active=True).all()
    active_msgs = [m.message for m in msgs if m.department in ['General', dept]]
    if active_msgs:
        combined = " 📢 | ".join(active_msgs)
        st.markdown(f"<div style='background: linear-gradient(90deg, #b91d73 0%, #f953c6 100%); color: white; font-weight: bold; border-radius: 8px; margin-bottom: 25px;'><marquee scrollamount='6'>🚨 PENGUMUMAN: {combined}</marquee></div>", unsafe_allow_html=True)

def extract_text_from_pdfs(file_paths):
    if not PyPDF2: return ""
    text = ""
    for path in file_paths:
        if os.path.exists(path):
            try:
                reader = PyPDF2.PdfReader(path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted: text += extracted + "\n"
            except: pass
    return text[:200000] 

def get_rag_answer(question, context_text, role="IT"):
    if not ai_model: return "⚠️ AI Offline."
    prompt = f"Kamu adalah AI {role}. Jawab HANYA dari referensi.\n--- REFERENSI ---\n{context_text}\n---\nPertanyaan: {question}\nJIKA TIDAK ADA DI REFERENSI, katakan tidak tahu."
    try: return ai_model.generate_content(prompt).text
    except Exception: return "⚠️ Terjadi kesalahan AI."

def verify_employee(username, password):
    user = session.query(Employee).filter_by(username=username).first()
    if user and pbkdf2_sha256.verify(password, user.password_hash): return user
    return None

def register_employee(username, password, name, dept, email):
    if session.query(Employee).filter_by(username=username).first(): return False
    session.add(Employee(username=username, password_hash=pbkdf2_sha256.hash(password), full_name=name, department=dept, email=email))
    session.commit()
    return True

def send_reset_email(email_to, name, temp_password):
    if "SMTP_EMAIL" in st.secrets and "SMTP_PASSWORD" in st.secrets:
        try:
            msg = MIMEMultipart()
            msg['Subject'] = "Reset Password - Nexus Hub"
            msg['From'] = st.secrets["SMTP_EMAIL"]; msg['To'] = email_to
            msg.attach(MIMEText(f"Halo {name},\n\nPassword Sementara: {temp_password}\n\nSegera login dan ganti password Anda.", 'plain'))
            server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(st.secrets["SMTP_EMAIL"], st.secrets["SMTP_PASSWORD"]); server.send_message(msg); server.quit()
            return True
        except: return False
    return False

def it_create_default_admin():
    if not session.query(ITUser).filter_by(username='admin_it').first():
        session.add(ITUser(username='admin_it', password_hash=pbkdf2_sha256.hash("admin123"), role='admin')); session.commit()

def it_verify_user(username, password):
    user = session.query(ITUser).filter_by(username=username).first()
    if user and pbkdf2_sha256.verify(password, user.password_hash): return user
    return None

def hr_create_default_admin():
    if not session.query(HRUser).filter_by(username='admin_hr').first():
        session.add(HRUser(username='admin_hr', password_hash=pbkdf2_sha256.hash("admin123"), role='admin')); session.commit()

def hr_verify_user(username, password):
    user = session.query(HRUser).filter_by(username=username).first()
    if user and pbkdf2_sha256.verify(password, user.password_hash): return user
    return None

def it_get_sla_status(created_at, priority, status):
    if status == 'Resolved': return "✅ Tuntas"
    target_hours = {"Critical": 2, "High": 8, "Medium": 24, "Low": 48}.get(priority, 24)
    deadline = created_at + timedelta(hours=target_hours)
    now = datetime.now()
    if now > deadline: return f"🔥 Telat {int((now - deadline).total_seconds() / 3600)} Jam!"
    remaining = (deadline - now).total_seconds() / 3600
    return f"⚠️ Sisa {int(remaining)} Jam" if remaining < (target_hours * 0.2) else f"⏳ Sisa {int(remaining)} Jam"

def send_telegram_alert(ticket_id, name, dept, subject, priority):
    if "TELEGRAM_BOT_TOKEN" in st.secrets and "TELEGRAM_CHAT_ID" in st.secrets:
        try:
            token = st.secrets["TELEGRAM_BOT_TOKEN"]; chat_id = st.secrets["TELEGRAM_CHAT_ID"]
            prio_icon = "🔴" if priority in ["High", "Critical"] else "🔵"
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": f"🚨 *TIKET BARU!* \n🆔 #{ticket_id}\n👤 {name} ({dept})\n🔥 Prio: {prio_icon} {priority}\n📝 {subject}", "parse_mode": "Markdown"}, timeout=5)
        except: pass

def send_email_receipt(email_to, ticket_id, name, pdf_bytes):
    if "SMTP_EMAIL" in st.secrets and "SMTP_PASSWORD" in st.secrets:
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"Tiket #{ticket_id} Berhasil Diterima"
            msg['From'] = st.secrets["SMTP_EMAIL"]; msg['To'] = email_to
            msg.attach(MIMEText(f"Halo {name},\n\nLaporan dengan ID #{ticket_id} telah kami terima.\n\nTerima kasih.", 'plain'))
            if pdf_bytes:
                part = MIMEApplication(pdf_bytes, Name=f"Bukti_Tiket_{ticket_id}.pdf")
                part['Content-Disposition'] = f'attachment; filename="Bukti_Tiket_{ticket_id}.pdf"'; msg.attach(part)
            server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(st.secrets["SMTP_EMAIL"], st.secrets["SMTP_PASSWORD"]); server.send_message(msg); server.quit()
        except: pass

def it_generate_ticket_pdf(ticket):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", style="B", size=16); pdf.cell(200, 10, txt="BUKTI LAPORAN IT SUPPORT", ln=True, align='C')
    pdf.set_font("Arial", size=10); pdf.cell(200, 5, txt="IT Service Desk Pro", ln=True, align='C'); pdf.cell(200, 10, txt="="*50, ln=True, align='C')
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="ID Tiket", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": #{clean_text(ticket.id)}", ln=True)
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Tanggal", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": {clean_text(ticket.created_at.strftime('%d %B %Y %H:%M'))}", ln=True)
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Pelapor", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": {clean_text(ticket.requester_name)} ({clean_text(ticket.department)})", ln=True)
    if ticket.device:
        pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Perangkat", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": {clean_text(ticket.device.asset_name)} (SN: {clean_text(ticket.device.serial_number)})", ln=True)
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Prioritas", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": {clean_text(ticket.priority).upper()}", ln=True)
    pdf.cell(200, 5, txt="-"*50, ln=True, align='C'); pdf.set_font("Arial", style="B", size=12); pdf.cell(200, 8, txt="JUDUL MASALAH:", ln=True); pdf.set_font("Arial", size=12); pdf.multi_cell(0, 8, txt=f"{clean_text(ticket.subject)}")
    pdf.set_font("Arial", style="B", size=12); pdf.cell(200, 8, txt="DESKRIPSI:", ln=True); pdf.set_font("Arial", size=12); pdf.multi_cell(0, 8, txt=f"{clean_text(ticket.description)}")
    return pdf.output(dest='S').encode('latin1')

def hr_generate_ticket_pdf(ticket):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", style="B", size=16); pdf.cell(200, 10, txt="BUKTI LAPORAN HR HOTLINE", ln=True, align='C')
    pdf.set_font("Arial", size=10); pdf.cell(200, 5, txt="Strictly Confidential (Rahasia)", ln=True, align='C'); pdf.cell(200, 10, txt="="*50, ln=True, align='C')
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Token ID", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": {clean_text(ticket.id)}", ln=True)
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Tanggal", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": {clean_text(ticket.created_at.strftime('%d %B %Y %H:%M'))}", ln=True)
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Pelapor", ln=False); pdf.set_font("Arial", size=12)
    pelapor_teks = "(Anonim) Rahasia" if ticket.is_anonymous else ticket.requester_name
    pdf.cell(150, 8, txt=f": {clean_text(pelapor_teks)} ({clean_text(ticket.department)})", ln=True)
    pdf.set_font("Arial", style="B", size=12); pdf.cell(40, 8, txt="Kategori", ln=False); pdf.set_font("Arial", size=12); pdf.cell(150, 8, txt=f": {clean_text(ticket.category)}", ln=True)
    pdf.cell(200, 5, txt="-"*50, ln=True, align='C'); pdf.set_font("Arial", style="B", size=12); pdf.cell(200, 8, txt="JUDUL LAPORAN:", ln=True); pdf.set_font("Arial", size=12); pdf.multi_cell(0, 8, txt=f"{clean_text(ticket.subject)}")
    pdf.set_font("Arial", style="B", size=12); pdf.cell(200, 8, txt="DESKRIPSI:", ln=True); pdf.set_font("Arial", size=12); pdf.multi_cell(0, 8, txt=f"{clean_text(ticket.description)}")
    return pdf.output(dest='S').encode('latin1')

# ==========================================
# 6. INIT STATE (SUPER PORTAL SSO)
# ==========================================
it_create_default_admin(); hr_create_default_admin()
if "current_building" not in st.session_state: st.session_state.current_building = "Lobby"
if 'emp_logged_in' not in st.session_state: st.session_state.emp_logged_in = False
if 'emp_username' not in st.session_state: st.session_state.emp_username = None
if 'emp_name' not in st.session_state: st.session_state.emp_name = None
if 'emp_dept' not in st.session_state: st.session_state.emp_dept = None
if 'emp_email' not in st.session_state: st.session_state.emp_email = None
if 'it_logged_in' not in st.session_state: st.session_state.it_logged_in = False
if 'it_username' not in st.session_state: st.session_state.it_username = None
if 'it_active_ticket_id' not in st.session_state: st.session_state.it_active_ticket_id = None
if 'hr_logged_in' not in st.session_state: st.session_state.hr_logged_in = False
if 'hr_username' not in st.session_state: st.session_state.hr_username = None
if 'hr_active_ticket_id' not in st.session_state: st.session_state.hr_active_ticket_id = None

if st.session_state.current_building == "Lobby" or (st.session_state.current_building == "IT" and not st.session_state.it_logged_in and not st.session_state.emp_logged_in) or (st.session_state.current_building == "HR" and not st.session_state.hr_logged_in and not st.session_state.emp_logged_in):
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none; } [data-testid="stSidebar"] { display: none; }</style>""", unsafe_allow_html=True)

def go_to_it(): st.session_state.current_building = "IT"
def go_to_hr(): st.session_state.current_building = "HR"
def go_to_lobby(): st.session_state.current_building = "Lobby"

# ==========================================
# 7. LIVE CHAT FRAGMENTS
# ==========================================
@st.fragment(run_every=3)
def it_live_chat_display(ticket_id, requester_name):
    latest_comments = session.query(ITComment).filter_by(ticket_id=ticket_id).order_by(ITComment.created_at.asc()).all()
    with st.container(height=350):
        if latest_comments:
            for chat in latest_comments:
                if chat.sender == "🤖 AI Assistant": st.markdown(f"<div style='text-align: left; background-color: #f3e5f5; color: #000; padding: 10px; border-radius: 10px; margin-bottom: 5px; margin-right: 20%; border-left: 5px solid #9c27b0;'><b>🤖 AI Auto-Responder</b><br>{chat.content}<br><small style='color:gray;'>{chat.created_at.strftime('%H:%M')}</small></div>", unsafe_allow_html=True)
                elif chat.sender == requester_name: 
                    st.markdown(f"<div style='text-align: left; background-color: #f5f5f5; color: #000; padding: 10px; border-radius: 10px; margin-bottom: 5px; margin-right: 20%; border-left: 3px solid #ccc;'><b>👤 {chat.sender}</b><br>{chat.content}<br><small style='color:gray;'>{chat.created_at.strftime('%H:%M')}</small></div>", unsafe_allow_html=True)
                    if chat.image_path and os.path.exists(chat.image_path): st.image(chat.image_path, width=250)
                else: 
                    st.markdown(f"<div style='text-align: right; background-color: #e6f3ff; color: #000; padding: 10px; border-radius: 10px; margin-bottom: 5px; margin-left: 20%; border-right: 3px solid #2196f3;'><b>👨‍💻 IT Support ({chat.sender})</b><br>{chat.content}<br><small style='color:gray;'>{chat.created_at.strftime('%H:%M')}</small></div>", unsafe_allow_html=True)
                    if chat.image_path and os.path.exists(chat.image_path): st.image(chat.image_path, width=250)
        else: st.caption("Belum ada riwayat diskusi.")

@st.fragment(run_every=3)
def hr_live_chat_display(ticket_id, requester_name):
    latest_comments = session.query(HRComment).filter_by(ticket_id=ticket_id).order_by(HRComment.created_at.asc()).all()
    with st.container(height=350):
        if latest_comments:
            for chat in latest_comments:
                if chat.sender == "🤖 HR AI Assistant": st.markdown(f"<div style='text-align: left; background-color: #fce4ec; color: #000; padding: 10px; border-radius: 10px; margin-bottom: 5px; margin-right: 20%; border-left: 5px solid #e91e63;'><b>🤖 HR AI Assistant</b><br>{chat.content}<br><small style='color:gray;'>{chat.created_at.strftime('%H:%M')}</small></div>", unsafe_allow_html=True)
                elif chat.sender == requester_name: 
                    st.markdown(f"<div style='text-align: left; background-color: #f5f5f5; color: #000; padding: 10px; border-radius: 10px; margin-bottom: 5px; margin-right: 20%; border-left: 3px solid #ccc;'><b>👤 {chat.sender}</b><br>{chat.content}<br><small style='color:gray;'>{chat.created_at.strftime('%H:%M')}</small></div>", unsafe_allow_html=True)
                    if chat.image_path and os.path.exists(chat.image_path): st.image(chat.image_path, width=250)
                else: 
                    st.markdown(f"<div style='text-align: right; background-color: #e6f3ff; color: #000; padding: 10px; border-radius: 10px; margin-bottom: 5px; margin-left: 20%; border-right: 3px solid #2196f3;'><b>👔 HRD Support ({chat.sender})</b><br>{chat.content}<br><small style='color:gray;'>{chat.created_at.strftime('%H:%M')}</small></div>", unsafe_allow_html=True)
                    if chat.image_path and os.path.exists(chat.image_path): st.image(chat.image_path, width=250)
        else: st.caption("Belum ada riwayat diskusi rahasia.")

def it_show_ticket_detail(ticket, is_admin=False):
    st.markdown("<br>", unsafe_allow_html=True)
    prio_color = "red" if ticket.priority in ['High', 'Critical'] else "blue"
    st.subheader(f"#{ticket.id} - {ticket.subject}")
    assign_str = f"| **Assigned To:** {ticket.assigned_to}" if ticket.assigned_to else "| **Belum di-assign**"
    st.caption(f"**Oleh:** {ticket.requester_name} ({ticket.department}) | **Masuk:** {ticket.created_at.strftime('%d %b %Y, %H:%M')} | **Status:** {ticket.status} {assign_str}")
    tab_info, tab_chat, tab_action = st.tabs(["📄 Detail Laporan", "💬 Diskusi (Live)", "⚙️ Action"])
    
    with tab_info:
        c1, c2 = st.columns(2)
        c1.markdown(f"**Kategori:** {ticket.category}"); c2.markdown(f"**Prioritas:** :{prio_color}[{ticket.priority}]")
        st.info(f"🎭 **Analisis Sentimen Pelapor:** {ticket.sentiment}")
        if ticket.device: st.info(f"💻 **Perangkat Terkait:** {ticket.device.asset_name} | **SN:** {ticket.device.serial_number}")
        if is_admin:
            user_hist = session.query(ITTicket).filter(ITTicket.requester_name == ticket.requester_name).count()
            st.warning(f"🕵️‍♂️ **Intelijen:** Pelapor ini telah membuat total **{user_hist} tiket** sejauh ini.")
        st.markdown("**Deskripsi:**"); st.info(ticket.description)
        if ticket.image_path and os.path.exists(ticket.image_path): st.image(ticket.image_path, width=400)
        if ticket.status == 'Resolved':
            st.markdown("---")
            if ticket.rating is not None: st.success(f"**Rating:** {'⭐' * ticket.rating}\n\n**Ulasan:** {ticket.feedback or '-'}")
            elif not is_admin: 
                with st.form(key=f"it_rating_{ticket.id}"):
                    st.write("Beri rating penanganan tiket ini:")
                    rating_val = st.radio("Bintang:", [5, 4, 3, 2, 1], format_func=lambda x: "⭐" * x, horizontal=True)
                    feedback_val = st.text_area("Komentar (Opsional)")
                    if st.form_submit_button("Kirim Penilaian 🚀", type="primary"):
                        ticket.rating = rating_val; ticket.feedback = feedback_val; session.commit(); st.rerun()

    with tab_chat:
        it_live_chat_display(ticket.id, ticket.requester_name)
        with st.form(key=f"it_chat_{ticket.id}", clear_on_submit=True):
            user_msg = st.text_input("Balas pesan...")
            chat_img = st.file_uploader("Kirim Gambar (Opsional)", type=['png', 'jpg', 'jpeg'])
            if st.form_submit_button("Kirim 📤"):
                if user_msg or chat_img:
                    sender_name = st.session_state.it_username if is_admin else ticket.requester_name 
                    c_img_path = save_uploaded_file(chat_img) if chat_img else None
                    session.add(ITComment(ticket_id=ticket.id, sender=sender_name, content=user_msg if user_msg else "*(Kirim Gambar)*", image_path=c_img_path))
                    session.commit(); st.rerun()

    with tab_action:
        if is_admin:
            st.markdown("### 👨‍💻 Assign & Status")
            admins = session.query(ITUser).filter_by(role='admin').all()
            admin_names = ["Belum Di-assign"] + [a.username for a in admins]
            curr_idx = admin_names.index(ticket.assigned_to) if ticket.assigned_to in admin_names else 0
            new_assign = st.selectbox("Assign Tiket ke Staf:", admin_names, index=curr_idx)
            if st.button("Set PIC", key=f"it_pic_{ticket.id}"):
                ticket.assigned_to = None if new_assign == "Belum Di-assign" else new_assign
                log_admin_action(st.session_state.it_username, 'IT', f"Assign Tiket #{ticket.id} ke {new_assign}")
                session.commit(); st.rerun()
            new_status = st.selectbox("Pilih Status Baru", ["Open", "In Progress", "Resolved"], index=["Open", "In Progress", "Resolved"].index(ticket.status))
            if st.button("Simpan Status", type="primary", key=f"it_stat_{ticket.id}"):
                ticket.status = new_status
                if new_status == 'Resolved' and ticket.device: ticket.device.status = 'Active'
                log_admin_action(st.session_state.it_username, 'IT', f"Ubah status Tiket #{ticket.id} menjadi {new_status}")
                session.commit(); st.rerun()
        st.markdown("### 📄 Bukti Laporan")
        st.download_button(label="⬇️ Download PDF", data=it_generate_ticket_pdf(ticket), file_name=f"IT_Tiket_#{ticket.id}.pdf", mime="application/pdf", key=f"it_pdf_{ticket.id}")

def hr_show_ticket_detail(ticket, is_admin=False):
    st.markdown("<br>", unsafe_allow_html=True)
    prio_color = "red" if ticket.priority in ['High', 'Critical/Urgent'] else "blue"
    st.subheader(f"Laporan {ticket.id} - {ticket.subject}")
    assign_str = f"| **Assigned To:** {ticket.assigned_to}" if ticket.assigned_to else "| **Belum di-assign**"
    anon_tag = "🕵️ (Anonim) " if ticket.is_anonymous else ""
    st.caption(f"**Oleh:** {anon_tag}{ticket.requester_name} ({ticket.department}) | **Masuk:** {ticket.created_at.strftime('%d %b %Y, %H:%M')} | **Status:** {ticket.status} {assign_str}")
    tab_info, tab_chat, tab_action = st.tabs(["📄 Detail Laporan", "💬 Diskusi Rahasia (Live)", "⚙️ Action & Dokumen"])
    
    with tab_info:
        c1, c2 = st.columns(2)
        c1.markdown(f"**Kategori:** {ticket.category}"); c2.markdown(f"**Urgensi:** :{prio_color}[{ticket.priority}]")
        st.info(f"🎭 **Analisis Sentimen Pelapor:** {ticket.sentiment}")
        st.markdown("**Deskripsi:**"); st.info(ticket.description)
        if ticket.image_path and os.path.exists(ticket.image_path): st.image(ticket.image_path, width=400)
        if ticket.status == 'Resolved':
            st.markdown("---")
            if ticket.rating is not None: st.success(f"**Rating:** {'⭐' * ticket.rating}\n\n**Ulasan:** {ticket.feedback or '-'}")
            elif not is_admin: 
                with st.form(key=f"hr_rating_{ticket.id}"):
                    st.write("Beri rating penanganan kasus ini:")
                    rating_val = st.radio("Bintang:", [5, 4, 3, 2, 1], format_func=lambda x: "⭐" * x, horizontal=True)
                    feedback_val = st.text_area("Komentar Tambahan (Opsional)")
                    if st.form_submit_button("Kirim Penilaian 🚀", type="primary"):
                        ticket.rating = rating_val; ticket.feedback = feedback_val; session.commit(); st.rerun()

    with tab_chat:
        hr_live_chat_display(ticket.id, ticket.requester_name)
        with st.form(key=f"hr_chat_{ticket.id}", clear_on_submit=True):
            user_msg = st.text_input("Balas pesan...")
            chat_img = st.file_uploader("Kirim Gambar Pendukung", type=['png', 'jpg', 'jpeg', 'pdf'])
            if st.form_submit_button("Kirim 📤"):
                if user_msg or chat_img:
                    sender_name = st.session_state.hr_username if is_admin else ticket.requester_name 
                    c_img_path = save_uploaded_file(chat_img) if chat_img else None
                    session.add(HRComment(ticket_id=ticket.id, sender=sender_name, content=user_msg if user_msg else "*(Kirim Dokumen)*", image_path=c_img_path))
                    session.commit(); st.rerun()

    with tab_action:
        if is_admin:
            st.markdown("### 👔 Assign & Status HR")
            admins = session.query(HRUser).filter_by(role='admin').all()
            admin_names = ["Belum Di-assign"] + [a.username for a in admins]
            curr_idx = admin_names.index(ticket.assigned_to) if ticket.assigned_to in admin_names else 0
            new_assign = st.selectbox("Assign ke HR:", admin_names, index=curr_idx)
            if st.button("Set PIC HR", key=f"hr_pic_{ticket.id}"):
                ticket.assigned_to = None if new_assign == "Belum Di-assign" else new_assign
                log_admin_action(st.session_state.hr_username, 'HR', f"Assign Laporan {ticket.id} ke {new_assign}")
                session.commit(); st.rerun()
            new_status = st.selectbox("Pilih Status Baru", ["Open", "In Progress", "Resolved"], index=["Open", "In Progress", "Resolved"].index(ticket.status))
            if st.button("Simpan Status", type="primary", key=f"hr_stat_{ticket.id}"):
                ticket.status = new_status
                log_admin_action(st.session_state.hr_username, 'HR', f"Ubah status Laporan {ticket.id} menjadi {new_status}")
                session.commit(); st.rerun()
        st.markdown("### 📄 Unduh Rekap Kasus (PDF)")
        st.download_button(label="⬇️ Download PDF Dokumen Laporan", data=hr_generate_ticket_pdf(ticket), file_name=f"HR_Laporan_{ticket.id}.pdf", mime="application/pdf", key=f"hr_pdf_{ticket.id}")

# ==========================================
# 9. LOBBY UTAMA
# ==========================================
def show_lobby():
    show_broadcast('General') 
    st.markdown("<h1 class='lobby-title'>🏢 Nexus Super Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p class='lobby-subtitle'>Enterprise Command Center & Employee Services</p><br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.markdown("""<div style='text-align: center; padding: 15px;'><img src="https://cdn-icons-png.flaticon.com/512/3256/3256114.png" width="90" style="margin-bottom: 20px; filter: drop-shadow(0 0 15px rgba(0,210,255,0.4));"><h2 style='color: #00D2FF; font-weight: 700; font-size: 2.2rem; margin-bottom: 5px;'>IT Helpdesk</h2><p style='color: #8892B0; font-size: 1rem; line-height: 1.6; margin-bottom: 30px;'>Technical Support • Infrastructure<br>Device Management • Account Recovery</p></div>""", unsafe_allow_html=True)
            st.button("MASUK PORTAL IT 🚀", use_container_width=True, type="primary", on_click=go_to_it)
    with col2:
        with st.container(border=True):
            st.markdown("""<div style='text-align: center; padding: 15px;'><img src="https://cdn-icons-png.flaticon.com/512/1256/1256650.png" width="90" style="margin-bottom: 20px; filter: drop-shadow(0 0 15px rgba(255,65,108,0.4));"><h2 style='color: #FF416C; font-weight: 700; font-size: 2.2rem; margin-bottom: 5px;'>HR Hotline</h2><p style='color: #8892B0; font-size: 1rem; line-height: 1.6; margin-bottom: 30px;'>Confidential Reports • Payroll<br>Leave Requests • Grievance Protocol</p></div>""", unsafe_allow_html=True)
            st.button("MASUK PORTAL HR 🔒", use_container_width=True, type="primary", on_click=go_to_hr)

# ==========================================
# 10. EMPLOYEE DASHBOARDS 
# ==========================================
def it_user_dashboard():
    show_broadcast('IT')
    st.sidebar.markdown(f"### 👋 Welcome,\n**{st.session_state.emp_name}**")
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("📋 Menu IT", ["📝 Submit Tiket", "📋 Tiket IT Saya", "🤖 AI Knowledge Base", "⚙️ Pengaturan Akun"])
    st.sidebar.markdown("---")
    with st.sidebar.container(border=True):
        st.markdown("### 🆘 Darurat IT?")
        st.caption("Khusus Server Down / Mati Total")
        st.link_button("📲 Hubungi WA Team Kami", WA_LINK, use_container_width=True)
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.emp_logged_in = False; st.rerun()
    if st.sidebar.button("⬅️ Kembali ke Lobby", use_container_width=True):
        go_to_lobby(); st.rerun()

    if menu == "⚙️ Pengaturan Akun":
        st.title("⚙️ Pengaturan Profil & Password")
        with st.container(border=True):
            with st.form("it_ganti_pass_form"):
                p_old = st.text_input("Password Saat Ini", type="password")
                p_new = st.text_input("Password Baru", type="password")
                p_new2 = st.text_input("Ketik Ulang Password Baru", type="password")
                if st.form_submit_button("Simpan Password Baru", type="primary"):
                    user = session.query(Employee).filter_by(username=st.session_state.emp_username).first()
                    if user and pbkdf2_sha256.verify(p_old, user.password_hash):
                        if p_new == p_new2 and len(p_new) >= 4:
                            user.password_hash = pbkdf2_sha256.hash(p_new); session.commit(); st.success("✅ Password berhasil diubah!")
                        else: st.error("⚠️ Password baru tidak cocok atau terlalu pendek (min 4 karakter).")
                    else: st.error("❌ Password saat ini salah!")

    elif menu == "🤖 AI Knowledge Base":
        st.title("🤖 IT AI Knowledge Base")
        st.info("Tanyakan panduan IT! AI kami telah membaca seluruh dokumen panduan resmi.")
        with st.container(border=True):
            user_q = st.text_input("Tanya AI (Misal: Gimana cara reset password VPN?)")
            if st.button("Tanyakan ke AI 🔍", type="primary"):
                docs = session.query(ITDocument).all()
                if not docs: st.warning("⚠️ Belum ada dokumen panduan yang diunggah Admin.")
                else:
                    with st.spinner("🤖 Membaca tumpukan dokumen..."):
                        st.success(get_rag_answer(user_q, extract_text_from_pdfs([d.file_path for d in docs]), "IT Helpdesk"))
        st.markdown("---"); st.markdown("### 📌 FAQ Singkat")
        for faq in session.query(ITFAQ).all():
            with st.expander(f"📌 {faq.question}"): st.write(faq.answer)

    elif menu == "📝 Submit Tiket":
        st.title("🚀 Submit IT Request")
        assets = session.query(ITInventory).all()
        asset_options = {"Tidak Ada / Bukan Perangkat": None}
        for a in assets: asset_options[f"{a.asset_name} (SN: {a.serial_number}) - Dept: {a.department}"] = a.id
        with st.container(border=True):
            with st.form("it_ticket_form", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text_input("Nama Lengkap", value=st.session_state.emp_name, disabled=True)
                    st.text_input("Departemen", value=st.session_state.emp_dept, disabled=True)
                with col_b:
                    cat = st.selectbox("Kategori Masalah*", ["Hardware", "Software", "Network", "Access/Account", "Lainnya"])
                    selected_asset_name = st.selectbox("Perangkat Terkait (Opsional)", list(asset_options.keys()))
                st.markdown("---")
                st.info("🤖 **Sistem AI:** AI akan otomatis mendeteksi prioritas, sentimen, dan membaca gambar Anda (OCR).")
                subject = st.text_input("Judul Singkat*")
                desc = st.text_area("Deskripsi Lengkap*", height=150)
                uploaded_file = st.file_uploader("Upload Bukti (Opsional - Akan dianalisa oleh Vision AI)", type=['png', 'jpg', 'jpeg'])
                
                if st.form_submit_button("🚀 Kirim Request Tiket", type="primary", use_container_width=True):
                    if subject and desc:
                        img_path = save_uploaded_file(uploaded_file) if uploaded_file else None
                        asset_id = asset_options[selected_asset_name]
                        
                        with st.spinner("🤖 AI sedang memproses Triage & Sentimen..."):
                            ai_prio = get_ai_triage(subject, desc)
                            ai_senti = get_ai_sentiment(subject + " " + desc)
                            new_ticket = ITTicket(emp_username=st.session_state.emp_username, requester_name=st.session_state.emp_name, requester_email=st.session_state.emp_email, department=st.session_state.emp_dept, category=cat, priority=ai_prio, sentiment=ai_senti, subject=subject, description=desc, image_path=img_path, device_id=asset_id)
                            session.add(new_ticket); session.commit()
                            
                            ai_reply = it_get_ai_first_aid(subject, desc, cat, img_path)
                            if ai_reply:
                                session.add(ITComment(ticket_id=new_ticket.id, sender="🤖 AI Assistant", content=ai_reply)); session.commit()
                                
                            send_telegram_alert(new_ticket.id, st.session_state.emp_name, st.session_state.emp_dept, subject, ai_prio)
                            if st.session_state.emp_email: send_email_receipt(st.session_state.emp_email, new_ticket.id, st.session_state.emp_name, it_generate_ticket_pdf(new_ticket))
                            
                        if asset_id: perangkat = session.query(ITInventory).get(asset_id); perangkat.status = 'Broken'; session.commit()
                        st.success(f"✅ Tiket masuk antrean (ID: #{new_ticket.id}) | Prioritas: **{ai_prio.upper()}** | Sentimen: **{ai_senti}**")
                    else: st.error("⚠️ Mohon lengkapi judul dan deskripsi!")

    elif menu == "📋 Tiket IT Saya":
        st.title("📋 Riwayat Tiket IT Saya")
        my_tickets = session.query(ITTicket).filter_by(emp_username=st.session_state.emp_username).order_by(ITTicket.created_at.desc()).all()
        if my_tickets:
            data = []
            for t in my_tickets: data.append({"ID": t.id, "Waktu": t.created_at.strftime('%d/%m %H:%M'), "Subjek": t.subject, "Prio": t.priority, "Status": t.status, "PIC": t.assigned_to or "-"})
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            sel_id = st.selectbox("Pilih tiket untuk dilihat detailnya:", [t.id for t in my_tickets], format_func=lambda x: f"Tiket #{x}")
            if sel_id: st.markdown("---"); it_show_ticket_detail(session.query(ITTicket).get(sel_id), is_admin=False)
        else: st.info("Anda belum pernah membuat tiket IT.")

def hr_user_dashboard():
    show_broadcast('HR')
    st.sidebar.markdown(f"### 👋 Welcome,\n**{st.session_state.emp_name}**")
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("📋 Menu HR", ["📝 Buat Laporan HR", "📋 Laporan HR Saya", "🤖 AI SOP Explorer", "⚙️ Pengaturan Akun"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True): st.session_state.emp_logged_in = False; st.rerun()
    if st.sidebar.button("⬅️ Kembali ke Lobby", use_container_width=True): go_to_lobby(); st.rerun()

    if menu == "⚙️ Pengaturan Akun":
        st.title("⚙️ Pengaturan Profil & Password")
        with st.container(border=True):
            with st.form("hr_ganti_pass_form"):
                p_old = st.text_input("Password Saat Ini", type="password")
                p_new = st.text_input("Password Baru", type="password")
                p_new2 = st.text_input("Ketik Ulang Password Baru", type="password")
                if st.form_submit_button("Simpan Password Baru", type="primary"):
                    user = session.query(Employee).filter_by(username=st.session_state.emp_username).first()
                    if user and pbkdf2_sha256.verify(p_old, user.password_hash):
                        if p_new == p_new2 and len(p_new) >= 4:
                            user.password_hash = pbkdf2_sha256.hash(p_new); session.commit(); st.success("✅ Password berhasil diubah!")
                        else: st.error("⚠️ Password baru tidak cocok atau terlalu pendek.")
                    else: st.error("❌ Password saat ini salah!")

    elif menu == "🤖 AI SOP Explorer":
        st.title("🤖 HR AI SOP Explorer")
        with st.container(border=True):
            user_q = st.text_input("Tanya AI (Misal: Berapa hari jatah cuti tahunan?)")
            if st.button("Tanyakan ke AI 🔍", type="primary"):
                docs = session.query(HRDocument).all()
                if not docs: st.warning("⚠️ HRD belum mengunggah dokumen SOP.")
                else:
                    with st.spinner("🤖 Membaca dokumen peraturan..."):
                        st.success(get_rag_answer(user_q, extract_text_from_pdfs([d.file_path for d in docs]), "HRD"))
        st.markdown("---"); st.markdown("### 📌 Info Singkat")
        for faq in session.query(HRFAQ).all():
            with st.expander(f"📌 {faq.question}"): st.write(faq.answer)

    elif menu == "📝 Buat Laporan HR":
        st.title("🛡️ Buat Laporan HR / Grievance")
        st.caption("Laporan dijamin kerahasiaannya. Jika memilih Anonim, nama Anda disembunyikan.")
        with st.container(border=True):
            with st.form("hr_ticket_form", clear_on_submit=True):
                is_anon = st.checkbox("🕵️ Laporkan Secara Anonim")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text_input("Nama Lengkap", value=st.session_state.emp_name, disabled=True)
                    st.text_input("Departemen", value=st.session_state.emp_dept, disabled=True)
                with col_b:
                    cat = st.selectbox("Kategori Laporan*", ["Payroll & Finance", "Cuti & Kehadiran", "Klaim & Benefit", "Pelecehan / Toxic Workplace", "Pelanggaran Etika", "Lainnya"])
                st.markdown("---")
                st.info("🤖 **Sistem AI:** Prioritas, sentimen, dan analisis bukti dokumen dilakukan otomatis.")
                subject = st.text_input("Judul Singkat*")
                desc = st.text_area("Deskripsi Lengkap (Ceritakan kronologinya)*", height=150)
                uploaded_file = st.file_uploader("Upload Bukti Pendukung (Foto/Screenshot/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
                
                if st.form_submit_button("🚀 Kirim Laporan Rahasia", type="primary", use_container_width=True):
                    if subject and desc:
                        img_path = save_uploaded_file(uploaded_file) if uploaded_file else None
                        req_name = "Rahasia (Anonim)" if is_anon else st.session_state.emp_name
                        
                        with st.spinner("🤖 AI sedang memproses laporan..."):
                            ai_prio = get_ai_triage(subject, desc)
                            ai_senti = get_ai_sentiment(subject + " " + desc)
                            new_ticket = HRTicket(emp_username=st.session_state.emp_username, requester_name=req_name, requester_email=st.session_state.emp_email, department=st.session_state.emp_dept, category=cat, priority=ai_prio, sentiment=ai_senti, subject=subject, description=desc, image_path=img_path, is_anonymous=is_anon)
                            session.add(new_ticket); session.commit()
                            
                            ai_reply = hr_get_ai_first_aid(subject, desc, cat, img_path)
                            if ai_reply:
                                session.add(HRComment(ticket_id=new_ticket.id, sender="🤖 HR AI Assistant", content=ai_reply)); session.commit()
                                
                        st.success(f"✅ Laporan dikirim dengan ID: **{new_ticket.id}** | Prioritas: {ai_prio} | Mood: {ai_senti}")
                    else: st.error("⚠️ Mohon lengkapi judul dan deskripsi!")

    elif menu == "📋 Laporan HR Saya":
        st.title("📋 Riwayat Laporan HR Saya")
        my_tickets = session.query(HRTicket).filter_by(emp_username=st.session_state.emp_username).order_by(HRTicket.created_at.desc()).all()
        if my_tickets:
            data = []
            for t in my_tickets:
                anon_icon = "🕵️ (Anonim) " if t.is_anonymous else ""
                data.append({"Token ID": t.id, "Waktu": t.created_at.strftime('%d/%m %H:%M'), "Subjek": anon_icon + t.subject, "Prio": t.priority, "Status": t.status})
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            sel_id = st.selectbox("Pilih laporan untuk dilihat detailnya:", [t.id for t in my_tickets], format_func=lambda x: f"Laporan {x}")
            if sel_id: st.markdown("---"); hr_show_ticket_detail(session.query(HRTicket).get(sel_id), is_admin=False)
        else: st.info("Anda belum pernah membuat laporan HR.")

# ==========================================
# 11. ADMIN DASHBOARDS (V6 FINAL)
# ==========================================
def it_admin_dashboard():
    st.sidebar.markdown(f"### 🛡️ Halo IT Admin,\n**{st.session_state.it_username}**")
    menu = st.sidebar.radio("Navigasi IT", ["📊 Dashboard Analytics", "📋 Manajemen Tiket", "💻 Manajemen Aset", "📚 Kelola SOP & FAQ", "📢 Kelola Broadcast", "👥 Manajemen Staf", "🔒 Audit Trail"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout IT", use_container_width=True): 
        log_admin_action(st.session_state.it_username, 'IT', 'Logout sistem')
        st.session_state.it_logged_in = False; st.rerun()
    if st.sidebar.button("⬅️ Kembali ke Lobby", use_container_width=True): go_to_lobby(); st.rerun()

    if menu == "🔒 Audit Trail":
        st.title("🔒 Security Audit Trail (IT)")
        st.caption("Log aktivitas seluruh Admin IT tercatat di sini dan tidak dapat dihapus.")
        logs = session.query(AdminLog).filter_by(department='IT').order_by(AdminLog.timestamp.desc()).all()
        if logs:
            df_logs = pd.DataFrame([{"Waktu": l.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "Admin": l.admin_username, "Aksi": l.action} for l in logs])
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else: st.info("Belum ada log aktivitas.")

    elif menu == "📢 Kelola Broadcast":
        st.title("📢 Sistem Broadcast Enterprise")
        with st.form("add_bc_it", clear_on_submit=True):
            msg = st.text_input("Pesan Pengumuman darurat")
            tipe = st.selectbox("Target Karyawan", ["General (Semua Layar)", "IT (Hanya di Portal IT)"])
            tipe = "General" if "General" in tipe else "IT"
            if st.form_submit_button("Sebarkan Teks Berjalan 🚀", type="primary"):
                if msg:
                    session.add(BroadcastMessage(message=msg, department=tipe, is_active=True)); session.commit()
                    log_admin_action(st.session_state.it_username, 'IT', f"Membuat broadcast: {msg}")
                    st.success("Broadcast aktif!"); st.rerun()
        st.markdown("#### 🚨 Broadcast Aktif Saat Ini:")
        bc_list = session.query(BroadcastMessage).filter(BroadcastMessage.department.in_(['General', 'IT'])).all()
        for b in bc_list:
            c1, c2 = st.columns([4,1])
            c1.write(f"[{'🟢 AKTIF' if b.is_active else '🔴 MATI'}] ({b.department}) - **{b.message}**")
            if b.is_active and c2.button("Matikan", key=f"bc_off_{b.id}"):
                b.is_active = False; log_admin_action(st.session_state.it_username, 'IT', f"Mematikan broadcast ID {b.id}"); session.commit(); st.rerun()
            elif not b.is_active and c2.button("Hapus", key=f"bc_del_{b.id}"):
                session.delete(b); session.commit(); st.rerun()

    elif menu == "📊 Dashboard Analytics":
        st.title("📊 IT Command Center")
        tickets = session.query(ITTicket).all()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📌 Total Laporan", len(tickets))
        c2.metric("⏳ In Progress", len([t for t in tickets if t.status == 'In Progress']))
        c3.metric("✅ Resolved", len([t for t in tickets if t.status == 'Resolved']))
        res_t = [t for t in tickets if t.status == 'Resolved' and t.rating is not None]
        c4.metric("🌟 Kepuasan (CSAT)", f"{sum(t.rating for t in res_t) / len(res_t):.1f} ⭐" if res_t else "Belum Ada")
        st.markdown("---")
        
        if tickets:
            df = pd.DataFrame([{'Kategori': t.category, 'Status': t.status, 'Departemen': t.department, 'Prioritas': t.priority, 'Tanggal': t.created_at.strftime('%Y-%m-%d'), 'PIC': t.assigned_to if t.assigned_to else "Belum Di-assign", 'Rating': t.rating, 'Sentiment': t.sentiment} for t in tickets])
            
            # 1. CHART TREND & KATEGORI
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                with st.container(border=True):
                    trend_df = df['Tanggal'].value_counts().sort_index().reset_index(); trend_df.columns = ['Tanggal', 'Jumlah']
                    fig_it = px.line(trend_df, x='Tanggal', y='Jumlah', title="📈 Tren Masalah IT Harian", markers=True)
                    fig_it.update_layout(xaxis=dict(type='category'), yaxis=dict(dtick=1), margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig_it, use_container_width=True)
            with col_chart2:
                with st.container(border=True):
                    st.plotly_chart(px.pie(df, names='Kategori', title="🗂️ Distribusi Kategori", hole=0.4).update_layout(margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
            
            # 2. CHART DEPT & SENTIMENT
            col_chart3, col_chart4 = st.columns(2)
            with col_chart3:
                with st.container(border=True):
                    dc = df['Departemen'].value_counts().reset_index(); dc.columns = ['Departemen', 'Jumlah']
                    st.plotly_chart(px.bar(dc, x='Departemen', y='Jumlah', title="🏢 Sumber Laporan", color='Departemen', text_auto=True).update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
            with col_chart4:
                with st.container(border=True):
                    senti_df = df['Sentiment'].value_counts().reset_index(); senti_df.columns = ['Sentimen', 'Jumlah']
                    fig_senti = px.pie(senti_df, names='Sentimen', values='Jumlah', title="🎭 Analisis Mood Karyawan (AI)", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_senti.update_layout(margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig_senti, use_container_width=True)
            
            # 3. GAMIFICATION LEADERBOARD
            st.markdown("#### 🏆 IT Hero Leaderboard (Gamification)")
            resolved_df = df[(df['Status'] == 'Resolved') & (df['PIC'] != "Belum Di-assign")]
            if not resolved_df.empty:
                leaderboard = resolved_df.groupby('PIC').agg(Tiket_Selesai=('Status', 'count'), Rata_Rating=('Rating', 'mean'), Bintang_5=('Rating', lambda x: (x == 5).sum())).reset_index()
                leaderboard['XP Total'] = (leaderboard['Tiket_Selesai'] * 10) + (leaderboard['Bintang_5'] * 50)
                def get_title(xp):
                    if xp >= 200: return "🥇 Enterprise Wizard"
                    elif xp >= 50: return "🥈 Tech Knight"
                    else: return "🥉 Novice Support"
                leaderboard['Gelar Pangkat'] = leaderboard['XP Total'].apply(get_title)
                leaderboard['Rata_Rating'] = leaderboard['Rata_Rating'].fillna(0).round(1).astype(str) + " ⭐"
                leaderboard = leaderboard[['PIC', 'Gelar Pangkat', 'XP Total', 'Tiket_Selesai', 'Rata_Rating']].sort_values(by='XP Total', ascending=False)
                st.dataframe(leaderboard, use_container_width=True, hide_index=True)
            else: st.info("Belum ada tiket yang diselesaikan staf.")

    elif menu == "📚 Kelola SOP & FAQ":
        st.title("📚 Manajemen Knowledge Base")
        with st.expander("📄 Upload Dokumen Panduan Baru (PDF) untuk AI", expanded=False):
            with st.form("it_upload_sop", clear_on_submit=True):
                doc_title = st.text_input("Judul Dokumen")
                doc_file = st.file_uploader("Upload File PDF", type=['pdf'])
                if st.form_submit_button("Upload Dokumen", type="primary"):
                    if doc_title and doc_file:
                        session.add(ITDocument(title=doc_title, file_path=save_uploaded_file(doc_file))); session.commit()
                        log_admin_action(st.session_state.it_username, 'IT', f"Upload Dokumen PDF: {doc_title}")
                        st.success("✅ Dokumen diupload!"); st.rerun()
        docs = session.query(ITDocument).all()
        if docs:
            for d in docs:
                c1, c2 = st.columns([4,1]); c1.write(f"📄 **{d.title}**")
                if c2.button("Hapus", key=f"del_it_doc_{d.id}"):
                    if os.path.exists(d.file_path): os.remove(d.file_path)
                    log_admin_action(st.session_state.it_username, 'IT', f"Hapus Dokumen PDF: {d.title}"); session.delete(d); session.commit(); st.rerun()
        st.markdown("---")
        with st.form("it_form_faq", clear_on_submit=True):
            faq_q = st.text_input("Pertanyaan Singkat"); faq_a = st.text_area("Jawaban Singkat")
            if st.form_submit_button("Simpan Artikel FAQ", type="primary"):
                if faq_q and faq_a: session.add(ITFAQ(question=faq_q, answer=faq_a)); session.commit(); st.success("FAQ ditambahkan!"); st.rerun()
        for f in session.query(ITFAQ).all():
            with st.expander(f.question):
                st.write(f.answer); 
                if st.button("Hapus FAQ", key=f"it_del_faq_{f.id}"): session.delete(f); session.commit(); st.rerun()

    elif menu == "💻 Manajemen Aset":
        st.title("💻 IT Asset Inventory")
        with st.expander("➕ Tambah Aset Baru", expanded=False):
            with st.form("form_tambah_aset", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1: nama_aset = st.text_input("Nama Perangkat"); tipe_aset = st.selectbox("Tipe Perangkat", ["Laptop", "PC Desktop", "Printer", "Router/Switch", "Server", "Lainnya"])
                with col2: sn_aset = st.text_input("Serial Number"); dept_aset = st.selectbox("Lokasi Departemen", ["HRD", "Finance", "Marketing", "Operations", "IT"])
                if st.form_submit_button("💾 Simpan Aset Baru", type="primary"):
                    if nama_aset: session.add(ITInventory(asset_name=nama_aset, asset_type=tipe_aset, serial_number=sn_aset, department=dept_aset)); session.commit(); st.success("Aset ditambahkan!"); st.rerun()
        aset_list = session.query(ITInventory).all()
        if aset_list: st.dataframe(pd.DataFrame([{"ID": a.id, "Nama": a.asset_name, "Tipe": a.asset_type, "S/N": a.serial_number, "Dept": a.department, "Status": a.status} for a in aset_list]), use_container_width=True, hide_index=True)

    elif menu == "👥 Manajemen Staf":
        st.title("👥 Manajemen Akun IT")
        with st.expander("➕ Tambah Akun Staf IT Baru", expanded=False):
            with st.form("it_form_tambah_admin", clear_on_submit=True):
                new_username = st.text_input("Username Baru")
                new_password = st.text_input("Password Sementara", type="password")
                if st.form_submit_button("💾 Buat Akun", type="primary"):
                    if new_username and new_password:
                        if session.query(ITUser).filter_by(username=new_username).first(): st.error("⚠️ Username sudah ada!")
                        else: session.add(ITUser(username=new_username, password_hash=pbkdf2_sha256.hash(new_password), role='admin')); session.commit(); st.success(f"Akun dibuat!"); st.rerun()
        admins = session.query(ITUser).filter_by(role='admin').all()
        st.dataframe(pd.DataFrame([{"ID": a.id, "Username": a.username} for a in admins]), use_container_width=True, hide_index=True)

    elif menu == "📋 Manajemen Tiket":
        st.title("📋 Helpdesk Queue")
        with st.container(border=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1: filter_status = st.multiselect("Filter Status", ["Open", "In Progress", "Resolved"], default=["Open", "In Progress"])
            with col_f2: search_query = st.text_input("Pencarian", placeholder="Ketik kata kunci...")
        query = session.query(ITTicket)
        if filter_status: query = query.filter(ITTicket.status.in_(filter_status))
        if search_query: query = query.filter(ITTicket.subject.contains(search_query) | ITTicket.requester_name.contains(search_query))
        tickets = query.order_by(ITTicket.created_at.desc()).all()
        if tickets:
            data = []
            for t in tickets: data.append({"ID": f"#{t.id}", "Waktu": t.created_at.strftime('%d/%m %H:%M'), "Pelapor": t.requester_name, "Subjek": t.subject, "Prio": t.priority, "Status": t.status, "PIC/Staf": t.assigned_to if t.assigned_to else "-", "Target / SLA": it_get_sla_status(t.created_at, t.priority, t.status)})
            def it_apply_row_styles(s):
                if s.name == 'Target / SLA': return ['background-color: #ffebee; color: #c62828; font-weight: bold;' if '🔥' in str(v) else ('background-color: #fff8e1; color: #ef6c00; font-weight: bold;' if '⚠️' in str(v) else '') for v in s]
                if s.name == 'Prio': return ['background-color: #ffebee; color: #c62828; font-weight: bold;' if v == 'Critical' else ('background-color: #fff8e1; color: #ef6c00; font-weight: bold;' if v == 'High' else '') for v in s]
                return [''] * len(s)
            st.dataframe(pd.DataFrame(data).style.apply(it_apply_row_styles, axis=0), use_container_width=True, hide_index=True)
            selected_id_raw = st.selectbox("Pilih Tiket untuk Diproses:", [t.id for t in tickets], format_func=lambda x: f"Tiket #{x}")
            if selected_id_raw: it_show_ticket_detail(session.query(ITTicket).get(selected_id_raw), is_admin=True)

def hr_admin_dashboard():
    st.sidebar.markdown(f"### 🛡️ Halo HR Admin,\n**{st.session_state.hr_username}**")
    menu = st.sidebar.radio("Navigasi HR", ["📊 Dashboard HR", "📋 Antrean Laporan", "📚 Kelola Dokumen SOP", "📢 Kelola Broadcast", "👥 Manajemen Staf HR", "🔒 Audit Trail"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout HR", use_container_width=True): 
        log_admin_action(st.session_state.hr_username, 'HR', 'Logout sistem')
        st.session_state.hr_logged_in = False; st.rerun()
    if st.sidebar.button("⬅️ Kembali ke Lobby", use_container_width=True): go_to_lobby(); st.rerun()

    if menu == "🔒 Audit Trail":
        st.title("🔒 Security Audit Trail (HR)")
        st.caption("Log aktivitas seluruh Admin HR tercatat di sini dan tidak dapat dihapus.")
        logs = session.query(AdminLog).filter_by(department='HR').order_by(AdminLog.timestamp.desc()).all()
        if logs:
            st.dataframe(pd.DataFrame([{"Waktu": l.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "Admin": l.admin_username, "Aksi": l.action} for l in logs]), use_container_width=True, hide_index=True)
        else: st.info("Belum ada log aktivitas.")

    elif menu == "📢 Kelola Broadcast":
        st.title("📢 Sistem Broadcast HR")
        with st.form("add_bc_hr", clear_on_submit=True):
            msg = st.text_input("Pengumuman darurat HR")
            tipe = st.selectbox("Target Karyawan", ["General (Semua Layar)", "HR (Hanya di Portal HR)"])
            tipe = "General" if "General" in tipe else "HR"
            if st.form_submit_button("Sebarkan Teks Berjalan 🚀", type="primary"):
                if msg:
                    session.add(BroadcastMessage(message=msg, department=tipe, is_active=True)); session.commit()
                    log_admin_action(st.session_state.hr_username, 'HR', f"Membuat broadcast: {msg}")
                    st.success("Broadcast aktif!"); st.rerun()
        st.markdown("#### 🚨 Broadcast Aktif Saat Ini:")
        bc_list = session.query(BroadcastMessage).filter(BroadcastMessage.department.in_(['General', 'HR'])).all()
        for b in bc_list:
            c1, c2 = st.columns([4,1])
            c1.write(f"[{'🟢 AKTIF' if b.is_active else '🔴 MATI'}] ({b.department}) - **{b.message}**")
            if b.is_active and c2.button("Matikan", key=f"bc_hr_off_{b.id}"):
                b.is_active = False; log_admin_action(st.session_state.hr_username, 'HR', f"Mematikan broadcast ID {b.id}"); session.commit(); st.rerun()
            elif not b.is_active and c2.button("Hapus", key=f"bc_hr_del_{b.id}"):
                session.delete(b); session.commit(); st.rerun()

    elif menu == "📊 Dashboard HR":
        st.title("📊 HR Command Center")
        tickets = session.query(HRTicket).all()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📌 Total Laporan", len(tickets))
        c2.metric("⏳ Dalam Proses", len([t for t in tickets if t.status == 'In Progress']))
        c3.metric("✅ Selesai Ditangani", len([t for t in tickets if t.status == 'Resolved']))
        res_t = [t for t in tickets if t.status == 'Resolved' and t.rating is not None]
        c4.metric("🌟 Kepuasan (CSAT)", f"{sum(t.rating for t in res_t) / len(res_t):.1f} ⭐" if res_t else "Belum Ada")
        st.markdown("---")
        
        if tickets:
            df = pd.DataFrame([{'Kategori': t.category, 'Status': t.status, 'Departemen': t.department, 'Prioritas': t.priority, 'Tanggal': t.created_at.strftime('%Y-%m-%d'), 'PIC': t.assigned_to if t.assigned_to else "Belum Di-assign", 'Rating': t.rating, 'Sentiment': t.sentiment} for t in tickets])
            
            # 1. CHART TREND & KATEGORI
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                with st.container(border=True):
                    trend_df = df['Tanggal'].value_counts().sort_index().reset_index(); trend_df.columns = ['Tanggal', 'Jumlah']
                    fig_hr = px.line(trend_df, x='Tanggal', y='Jumlah', title="📈 Tren Laporan HR Harian", markers=True, color_discrete_sequence=['#FF416C'])
                    fig_hr.update_layout(xaxis=dict(type='category'), yaxis=dict(dtick=1), margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig_hr, use_container_width=True)
            with col_chart2:
                with st.container(border=True):
                    st.plotly_chart(px.pie(df, names='Kategori', title="🗂️ Distribusi Kategori HR", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel).update_layout(margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
            
            # 2. CHART DEPT & SENTIMENT
            col_chart3, col_chart4 = st.columns(2)
            with col_chart3:
                with st.container(border=True):
                    dc = df['Departemen'].value_counts().reset_index(); dc.columns = ['Departemen', 'Jumlah']
                    st.plotly_chart(px.bar(dc, x='Departemen', y='Jumlah', title="🏢 Sumber Departemen Laporan", color='Departemen', text_auto=True, color_discrete_sequence=px.colors.qualitative.Set3).update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
            with col_chart4:
                with st.container(border=True):
                    senti_df = df['Sentiment'].value_counts().reset_index(); senti_df.columns = ['Sentimen', 'Jumlah']
                    fig_senti = px.pie(senti_df, names='Sentimen', values='Jumlah', title="🎭 Analisis Mood Karyawan (AI)", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_senti.update_layout(margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig_senti, use_container_width=True)
            
            # 3. GAMIFICATION LEADERBOARD
            st.markdown("#### 🏆 HR Hero Leaderboard (Gamification)")
            resolved_df = df[(df['Status'] == 'Resolved') & (df['PIC'] != "Belum Di-assign")]
            if not resolved_df.empty:
                leaderboard = resolved_df.groupby('PIC').agg(Kasus_Selesai=('Status', 'count'), Rata_Rating=('Rating', 'mean'), Bintang_5=('Rating', lambda x: (x == 5).sum())).reset_index()
                leaderboard['XP Total'] = (leaderboard['Kasus_Selesai'] * 10) + (leaderboard['Bintang_5'] * 50)
                def get_title(xp):
                    if xp >= 200: return "🥇 Enterprise Wizard"
                    elif xp >= 50: return "🥈 HR Specialist"
                    else: return "🥉 Novice Support"
                leaderboard['Gelar Pangkat'] = leaderboard['XP Total'].apply(get_title)
                leaderboard['Rata_Rating'] = leaderboard['Rata_Rating'].fillna(0).round(1).astype(str) + " ⭐"
                leaderboard = leaderboard[['PIC', 'Gelar Pangkat', 'XP Total', 'Kasus_Selesai', 'Rata_Rating']].sort_values(by='XP Total', ascending=False)
                st.dataframe(leaderboard, use_container_width=True, hide_index=True)
            else: st.info("Belum ada kasus yang diselesaikan tim HR.")

    elif menu == "📚 Kelola Dokumen SOP":
        st.title("📚 Manajemen Info & SOP HRD")
        with st.expander("📄 Upload Dokumen SOP Baru (PDF)", expanded=False):
            with st.form("hr_upload_sop", clear_on_submit=True):
                doc_title = st.text_input("Judul Dokumen")
                doc_file = st.file_uploader("Upload File PDF", type=['pdf'])
                if st.form_submit_button("Upload Dokumen", type="primary"):
                    if doc_title and doc_file:
                        session.add(HRDocument(title=doc_title, file_path=save_uploaded_file(doc_file))); session.commit()
                        log_admin_action(st.session_state.hr_username, 'HR', f"Upload SOP PDF: {doc_title}")
                        st.success("✅ Dokumen diupload!"); st.rerun()
        docs = session.query(HRDocument).all()
        if docs:
            for d in docs:
                c1, c2 = st.columns([4,1]); c1.write(f"📄 **{d.title}**")
                if c2.button("Hapus", key=f"del_hr_doc_{d.id}"):
                    if os.path.exists(d.file_path): os.remove(d.file_path)
                    log_admin_action(st.session_state.hr_username, 'HR', f"Hapus SOP PDF: {d.title}"); session.delete(d); session.commit(); st.rerun()
        st.markdown("---")
        with st.form("hr_form_faq", clear_on_submit=True):
            faq_q = st.text_input("Pertanyaan Singkat"); faq_a = st.text_area("Jawaban Singkat")
            if st.form_submit_button("Publish ke Karyawan", type="primary"):
                if faq_q and faq_a: session.add(HRFAQ(question=faq_q, answer=faq_a)); session.commit(); st.success("FAQ dipublish!"); st.rerun()
        for f in session.query(HRFAQ).all():
            with st.expander(f.question):
                st.write(f.answer); 
                if st.button("Hapus FAQ Ini", key=f"hr_del_faq_{f.id}"): session.delete(f); session.commit(); st.rerun()

    elif menu == "👥 Manajemen Staf HR":
        st.title("👥 Manajemen Akun HRD")
        with st.expander("➕ Tambah Akun Tim HR Baru", expanded=False):
            with st.form("hr_form_tambah_admin", clear_on_submit=True):
                new_username = st.text_input("Username Baru")
                new_password = st.text_input("Password Sementara", type="password")
                if st.form_submit_button("💾 Buat Akun", type="primary"):
                    if new_username and new_password:
                        if session.query(HRUser).filter_by(username=new_username).first(): st.error("⚠️ Username sudah ada!")
                        else: session.add(HRUser(username=new_username, password_hash=pbkdf2_sha256.hash(new_password), role='admin')); session.commit(); st.success(f"Akun dibuat!"); st.rerun()
        admins = session.query(HRUser).filter_by(role='admin').all()
        st.dataframe(pd.DataFrame([{"ID": a.id, "Username": a.username} for a in admins]), use_container_width=True, hide_index=True)

    elif menu == "📋 Antrean Laporan":
        st.title("📋 HR Laporan Masuk")
        query = session.query(HRTicket).order_by(HRTicket.created_at.desc()).all()
        if query:
            data = []
            for t in query:
                anon_icon = "🕵️ " if t.is_anonymous else "👤 "
                data.append({"Token ID": t.id, "Waktu": t.created_at.strftime('%d/%m %H:%M'), "Pelapor": anon_icon + t.requester_name, "Kategori": t.category, "Urgensi": t.priority, "Status": t.status, "PIC/Staf": t.assigned_to if t.assigned_to else "-"})
            def hr_apply_row_styles(s):
                if s.name == 'Urgensi': return ['background-color: #ffebee; color: #c62828; font-weight: bold;' if 'Urgent' in str(v) else '' for v in s]
                return [''] * len(s)
            st.dataframe(pd.DataFrame(data).style.apply(hr_apply_row_styles, axis=0), use_container_width=True, hide_index=True)
            selected_id_raw = st.selectbox("Pilih Laporan untuk Ditindaklanjuti:", [t.id for t in query], format_func=lambda x: f"Laporan {x}")
            if selected_id_raw: hr_show_ticket_detail(session.query(HRTicket).get(selected_id_raw), is_admin=True)

# ==========================================
# 12. SISTEM LOGIN ROUTER
# ==========================================
def render_employee_login_ui():
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown(f"<h2 style='text-align: center; color: #00D2FF;'>🧑‍💻 Employee Access</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Masuk untuk membuat tiket IT atau Laporan HR</p><hr>", unsafe_allow_html=True)
            tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Daftar Akun Baru", "🆘 Lupa Password"])
            with tab1:
                with st.form("emp_login_form"):
                    l_user = st.text_input("Username Karyawan")
                    l_pass = st.text_input("Password", type="password")
                    if st.form_submit_button("Log In Karyawan", type="primary", use_container_width=True):
                        user = verify_employee(l_user, l_pass)
                        if user:
                            st.session_state.emp_logged_in = True; st.session_state.emp_username = user.username
                            st.session_state.emp_name = user.full_name; st.session_state.emp_dept = user.department; st.session_state.emp_email = user.email; st.rerun()
                        else: st.error("❌ Username atau Password salah.")
            with tab2:
                with st.form("emp_register_form"):
                    r_user = st.text_input("Buat Username*")
                    r_pass = st.text_input("Buat Password*", type="password")
                    r_name = st.text_input("Nama Lengkap*")
                    r_dept = st.selectbox("Departemen*", ["HRD", "Finance", "Marketing", "Operations", "IT", "Sales"])
                    st.info("💡 Masukkan email asli Anda agar bisa memulihkan password jika lupa.")
                    r_email = st.text_input("Email (Wajib untuk reset password)*")
                    if st.form_submit_button("Daftar Sekarang", use_container_width=True):
                        if r_user and r_pass and r_name and r_email:
                            if register_employee(r_user, r_pass, r_name, r_dept, r_email): st.success("✅ Akun berhasil dibuat! Silakan Login di tab sebelah.")
                            else: st.error("⚠️ Username sudah dipakai.")
                        else: st.error("⚠️ Harap isi semua field yang bertanda bintang (*)")
            with tab3:
                st.info("Ketikkan alamat email terdaftar Anda. Kami akan mengirimkan password sementara.")
                with st.form("forgot_pass_form"):
                    f_email = st.text_input("Email Terdaftar")
                    if st.form_submit_button("Kirim Password Reset", use_container_width=True):
                        if f_email:
                            user = session.query(Employee).filter_by(email=f_email).first()
                            if user:
                                temp_pass = f"NEXUS-{uuid.uuid4().hex[:5].upper()}"
                                user.password_hash = pbkdf2_sha256.hash(temp_pass); session.commit()
                                if send_reset_email(user.email, user.full_name, temp_pass): st.success("✅ Password sementara dikirim ke email Anda!")
                                else: st.error("⚠️ Gagal mengirim email. Cek konfigurasi SMTP.")
                            else: st.error("❌ Email tidak ditemukan.")
                        else: st.error("⚠️ Masukkan email.")

def show_it_helpdesk():
    if st.session_state.it_logged_in: it_admin_dashboard()
    elif st.session_state.emp_logged_in: it_user_dashboard()
    else:
        st.button("⬅️ Kembali ke Lobby Utama", on_click=go_to_lobby)
        t_emp, t_admin = st.tabs(["🏢 Portal Karyawan", "👨‍💻 Panel Admin IT"])
        with t_emp: render_employee_login_ui()
        with t_admin:
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.container(border=True):
                    st.markdown("<h3 style='text-align: center; color: #1E88E5;'>👨‍💻 Admin IT Login</h3><hr>", unsafe_allow_html=True)
                    with st.form("it_login_form"):
                        username = st.text_input("Username IT"); password = st.text_input("Password IT", type="password")
                        if st.form_submit_button("Masuk Admin IT", type="primary", use_container_width=True):
                            user = it_verify_user(username, password)
                            if user: 
                                st.session_state.it_logged_in = True; st.session_state.it_username = user.username
                                log_admin_action(user.username, 'IT', 'Login ke sistem'); st.rerun()
                            else: st.error("❌ Kredensial Admin IT salah.")

def show_hr_hotline():
    if st.session_state.hr_logged_in: hr_admin_dashboard()
    elif st.session_state.emp_logged_in: hr_user_dashboard()
    else:
        st.button("⬅️ Kembali ke Lobby Utama", on_click=go_to_lobby)
        t_emp, t_admin = st.tabs(["🏢 Portal Karyawan", "👔 Panel Admin HRD"])
        with t_emp: render_employee_login_ui()
        with t_admin:
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.container(border=True):
                    st.markdown("<h3 style='text-align: center; color: #E53935;'>👔 Admin HR Login</h3><hr>", unsafe_allow_html=True)
                    with st.form("hr_login_form"):
                        username = st.text_input("Username HR"); password = st.text_input("Password HR", type="password")
                        if st.form_submit_button("Masuk Admin HR", type="primary", use_container_width=True):
                            user = hr_verify_user(username, password)
                            if user: 
                                st.session_state.hr_logged_in = True; st.session_state.hr_username = user.username
                                log_admin_action(user.username, 'HR', 'Login ke sistem'); st.rerun()
                            else: st.error("❌ Kredensial Admin HR salah.")

# ==========================================
# 13. MESIN PENJALAN (MAIN EXECUTION)
# ==========================================
if st.session_state.current_building == "Lobby": show_lobby()
elif st.session_state.current_building == "IT": show_it_helpdesk()
elif st.session_state.current_building == "HR": show_hr_hotline()