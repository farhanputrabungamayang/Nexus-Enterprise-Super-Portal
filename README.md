# 🏢 Nexus Enterprise Super Portal

An all-in-one, AI-powered Enterprise Ticketing and Management Portal built for modern HR and IT departments. Designed to streamline employee services, enhance data security, and automate request handling using cutting-edge Generative AI and computer vision.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Framework-FF4B4B.svg)
![Generative AI](https://img.shields.io/badge/AI-Gemini_LLM-orange.svg)

## 🚀 Key Features

### 🔐 Core & Security Ecosystem
* **Single Sign-On (SSO):** Seamless navigation between IT and HR portals with unified employee credentials.
* **Smart Authentication & Recovery:** Secure login, encrypted passwords, and automated SMTP email routing for temporary password recovery.
* **Security Audit Trail:** Immutable system logs tracking all administrative actions (ticket updates, document uploads, broadcasts) for ISO compliance.

### 🧠 The AI Engine
* **AI Auto-Triage:** Automatically determines ticket priority (Low, Medium, High, Critical) based on the context of the user's issue.
* **AI Sentiment Analysis:** Detects employee mood (Angry, Panicked, Happy, etc.) to help admins prioritize sensitive cases.
* **Multimodal Vision AI:** Extracts and analyzes context from user-uploaded images (e.g., software error codes, medical receipts) using OCR and LLMs.
* **RAG SOP Explorer:** An interactive AI chatbot that reads and retrieves answers directly from company PDF documents uploaded by admins.

### 💼 Enterprise Management
* **Dual Dashboards:** Segregated environments for IT Helpdesk (Asset Inventory) and HR Hotline (Anonymous Grievance Reporting).
* **Live Chat & SLA Tracking:** Real-time communication channels between employees and admins with built-in deadline tracking.
* **Emergency Broadcast:** Active running-text banners triggered by admins for critical company-wide announcements.
* **Data Export & Reporting:** One-click automated PDF receipt generation for users, and bulk Excel data export for admins.

### 📊 Advanced Analytics
* **Interactive Dashboards:** Dynamic visual tracking using Plotly for daily ticket trends, category distribution, and sentiment pie charts.
* **Admin Gamification:** A built-in leaderboard ranking support staff based on completed tickets and CSAT (Customer Satisfaction) 5-star ratings, awarding dynamic titles (e.g., *Enterprise Wizard*).

## 🛠️ Tech Stack
* **Frontend/Backend:** Python, Streamlit
* **Database:** SQLite, SQLAlchemy
* **AI/ML:** Google Generative AI (Gemini), PyPDF2, PIL (Pillow)
* **Data Visualization:** Pandas, Plotly Express
* **Utilities:** Passlib (Hashing), FPDF, SMTPLib

## 🌐 Live Demo
Try the application live here: https://nexus-enterprise-super-app-projects.streamlit.app/
