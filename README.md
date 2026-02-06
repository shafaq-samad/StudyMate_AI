# StudyMate AI 🧠
### *The Ultimate Intelligent Learning Assistant*

StudyMate AI is a premium, full-stack educational platform designed to transform tedious studying into active, efficient learning. By leveraging the power of **Google Gemini 1.5 Pro** and **Groq Cloud AI**, the platform offers a suite of advanced tools to help students master any subject twice as fast.

[![Deployment Status](https://img.shields.io/badge/Deployment-Ready-brightgreen)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

---

## 🌟 Key Features

*   **⚡ Smart Summarizer**: Distill complex documents into 3 levels of detail (Short, Medium, Comprehensive).
*   **🧪 AI Quiz Generator**: Instantly turn your notes into MCQs and True/False assessments.
*   **🎴 Active Recall Flashcards**: AI-curated flashcards for high-impact memorization.
*   **💬 Document Intel (Q&A)**: Chat with your PDF, DOCX, or TXT files for context-aware answers.
*   **📁 File Lab**: Advanced extraction lab for processing academic materials up to 10MB.
*   **⏲️ Deep Focus Timer**: Built-in Pomodoro timer with cycle tracking and focus analytics.
*   **📜 Intel Repository**: Complete history of all your AI generations with review and management capabilities.
*   **🔐 Professional Auth**: Secure login/signup system with password reset flow and profile management.

---

## 🛠️ Technology Stack

*   **Frontend**: HTML5, Vanilla JavaScript, **Tailwind CSS**, FontAwesome (Premium Design System).
*   **Backend**: Python, **Flask**, Gunicorn (Production WSGI).
*   **AI Engines**: Google Generative AI (Gemini), Groq API (LLaMA-3/Mixtral).
*   **Database**: SQLite (ACID compliant user data and session management).
*   **Deployment**: Procfile-ready for Railway/Render.

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.11+
*   Google Gemini API Key
*   Groq API Key

### 2. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory and add your keys:
```env
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
FLASK_SECRET_KEY=your_secret_key
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### 4. Run Locally
```bash
python app.py
```
Visit `http://localhost:5000` to start learning!

---

## ☁️ Deployment (Railway / Render)

This project is configured for one-click deployment:
1.  **Repository**: Push this code to your GitHub.
2.  **Platform**: Connect your repository to [Railway.app](https://railway.app) or [Render.com](https://render.com).
3.  **Environment**: Add your `.env` variables in the platform's dashboard.
4.  **Automatic**: The platform will detect the `Procfile` and `runtime.txt` and deploy automatically.

---

## 🛡️ Privacy & Compliance
*   **Data Sovereignty**: Users can delete their entire account and history at any time through the Profile settings.
*   **Secure Processing**: Files are processed in real-time and are never stored on the server permanently.
*   **Encryption**: All passwords are encrypted using industry-standard hashing algorithms (PBKDF2).

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

---
*Created with ❤️ for students everywhere.*

