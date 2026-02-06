from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_mail import Mail, Message
import google.generativeai as genai
from groq import Groq
import tempfile
import os
import time
import secrets
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import docx2txt
import PyPDF2
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Email Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# Database setup
DB_FILE = "users.db"


def wants_json():
    """Check if client expects JSON response"""
    return (
        request.accept_mimetypes.accept_json or 
        request.content_type == 'application/json' or 
        request.path.startswith('/api/')
    )


@app.before_request
def check_auth_for_api():
    # Routes that don't require authentication
    public_api_endpoints = [
        '/api/login', '/api/signup', '/api/check-password', 
        '/api/forgot-password', '/api/reset-password',
        '/api/auth-status', '/api/contact'
    ]
    
    # Check if this is an API request (starts with /api/)
    if request.path.startswith('/api/'):
        # Allow public endpoints
        if request.path in public_api_endpoints or request.path.startswith('/api/reset-password/'):
            return None
            
        # Check authentication for protected API routes
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
    
    return None



def validate_password(password):
    """Validate password against rules and return which rules are met"""
    rules = {
        'length': len(password) >= 8,
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'lowercase': bool(re.search(r'[a-z]', password)),
        'number': bool(re.search(r'[0-9]', password)),
        'special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
    }
    return rules
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    reset_token TEXT,
                    reset_token_expiry DATETIME
                )''')
    # Migration: Add reset_token and reset_token_expiry if they don't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        c.execute("ALTER TABLE users ADD COLUMN reset_token_expiry DATETIME")
    except sqlite3.OperationalError:
        # Columns already exist
        pass
    
    # History table
    c.execute('''CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')
    conn.commit()
    conn.close()

init_db()

# -------------------------
# LOGIN / SIGNUP ROUTES
# -------------------------

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    # Password validation
    password_rules = validate_password(password)
    
    # Check if all rules are met
    if not all(password_rules.values()):
        return jsonify({
            'error': 'Password does not meet all requirements',
            'rules': password_rules  # Send back which rules passed/failed
        }), 400

    hashed_pw = generate_password_hash(password)
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Signup successful'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400
    
@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    # Password validation
    password_rules = validate_password(password)
    
    # Check if all rules are met
    if not all(password_rules.values()):
        return jsonify({
            'error': 'Password does not meet all requirements',
            'rules': password_rules
        }), 400

    hashed_pw = generate_password_hash(password)
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Signup successful'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400
    
@app.route('/api/check-password', methods=['POST'])
def check_password():
    """API endpoint to check password strength and return rule status"""
    data = request.get_json()
    password = data.get('password', '')
    
    rules = validate_password(password)
    
    # Return the status of each rule
    return jsonify({
        'valid': all(rules.values()),
        'rules': rules
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, password, username FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[1], password):
        session['user_id'] = user[0]
        session['username'] = user[2]
        return jsonify({'message': 'Login successful', 'username': user[2]}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/auth-status', methods=['GET'])
def auth_status():
    """Sync frontend with backend session"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'username': session.get('username')
        })
    return jsonify({'authenticated': False}), 200

# -------------------------
# PROFILE MANAGEMENT ROUTES
# -------------------------

@app.route('/api/profile', methods=['GET'])
def get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, email FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'username': user[0],
            'email': user[1]
        })
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/change-password', methods=['POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'All fields are required'}), 400
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    
    if not user or not check_password_hash(user[0], old_password):
        conn.close()
        return jsonify({'error': 'Incorrect current password'}), 400
        
    # Validation for new password
    rules = validate_password(new_password)
    if not all(rules.values()):
        conn.close()
        return jsonify({'error': 'New password does not meet requirements', 'rules': rules}), 400
        
    hashed_pw = generate_password_hash(new_password)
    c.execute("UPDATE users SET password=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Password updated successfully'}), 200

@app.route('/api/delete-account', methods=['POST'])
def delete_account():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    password = data.get('password')
    
    if not password:
        return jsonify({'error': 'Password is required to confirm deletion'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    
    if not user or not check_password_hash(user[0], password):
        conn.close()
        return jsonify({'error': 'Incorrect password'}), 400
        
    # Delete everything related to the user
    c.execute("DELETE FROM history WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    session.clear()
    return jsonify({'message': 'Account deleted successfully'}), 200

@app.route("/profile")
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for("login_page"))
    return render_template("profile.html")

# -------------------------
# FORGOT PASSWORD ROUTES
# -------------------------

@app.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    user = c.fetchone()
    
    if user:
        token = secrets.token_urlsafe(32)
        expiry = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute("UPDATE users SET reset_token=?, reset_token_expiry=? WHERE id=?", 
                  (token, expiry, user[0]))
        conn.commit()
        
        # Send Email
        reset_url = url_for('reset_password', token=token, _external=True)
        msg = Message('Password Reset Request - StudyMate AI',
                      recipients=[email])
        msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, simply ignore this email and no changes will be made.
This link will expire in 1 hour.
'''
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {e}")
            return jsonify({'error': 'Failed to send reset email. Please try again later.'}), 500
            
    conn.close()
    
    # Always return success to prevent email enumeration
    return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200

@app.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, reset_token_expiry FROM users WHERE reset_token=?", (token,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        return "Invalid or expired token", 400
        
    # Check expiry
    expiry = datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S')
    if expiry < datetime.now():
        return "Token has expired", 400

    return render_template('reset_password.html', token=token)

@app.route('/api/reset-password/<token>', methods=['POST'])
def api_reset_password(token):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, reset_token_expiry FROM users WHERE reset_token=?", (token,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'Invalid or expired token'}), 400
        
    # Check expiry
    expiry = datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S')
    if expiry < datetime.now():
        conn.close()
        return jsonify({'error': 'Token has expired'}), 400

    # POST request for resetting
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password:
        conn.close()
        return jsonify({'error': 'New password is required'}), 400
        
    password_rules = validate_password(new_password)
    if not all(password_rules.values()):
        conn.close()
        return jsonify({'error': 'Password does not meet requirements', 'rules': password_rules}), 400
        
    hashed_pw = generate_password_hash(new_password)
    c.execute("UPDATE users SET password=?, reset_token=NULL, reset_token_expiry=NULL WHERE id=?", 
              (hashed_pw, user[0]))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Password has been reset successfully'}), 200

# -------------------------
# HISTORY ROUTE
# -------------------------

@app.route('/api/history', methods=['GET'])
def api_history():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get sort and search parameters
    sort = request.args.get('sort', 'desc')  # desc or asc
    search = request.args.get('search', '').strip()
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if search:
        c.execute("SELECT id, action, timestamp FROM history WHERE user_id=? AND action LIKE ? ORDER BY timestamp DESC" if sort == 'desc' else "SELECT id, action, timestamp FROM history WHERE user_id=? AND action LIKE ? ORDER BY timestamp ASC", (user_id, f'%{search}%'))
    else:
        c.execute("SELECT id, action, timestamp FROM history WHERE user_id=? ORDER BY timestamp DESC" if sort == 'desc' else "SELECT id, action, timestamp FROM history WHERE user_id=? ORDER BY timestamp ASC", (user_id,))
    
    records = c.fetchall()
    conn.close()
    
    history_list = [{'id': row[0], 'action': row[1], 'timestamp': row[2]} for row in records]
    return jsonify(history_list)


@app.route('/api/history/<int:entry_id>', methods=['DELETE'])
def delete_history(entry_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM history WHERE id=?", (entry_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    if row[0] != user_id:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    c.execute("DELETE FROM history WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted'}), 200


@app.route('/api/history/clear-all', methods=['POST'])
def clear_all_history():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'All history cleared'}), 200

# -------------------------
# ACTION TRACKING (example)
# -------------------------

def log_action(user_id, action):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO history (user_id, action) VALUES (?, ?)", (user_id, action))
    conn.commit()
    conn.close()
# Regular pages
@app.route("/app")
def app_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for("login_page"))
    return render_template("app.html")

@app.route("/about")
def about_page():
    return render_template("about.html")

# Serve the signup page
@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/contact")
def contact_page():
    return render_template("contact.html")

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    subject_type = data.get('subject', 'General Inquiry')
    message = data.get('message')

    if not name or not email or not message:
        return jsonify({'error': 'All fields are required'}), 400

    msg = Message(f'Contact Form: {subject_type} from {name}',
                  recipients=[os.getenv('MAIL_USERNAME')],
                  reply_to=email)
    msg.body = f"From: {name} <{email}>\nSubject: {subject_type}\n\n{message}"
    
    try:
        mail.send(msg)
        return jsonify({'message': 'Your message has been dispatched successfully!'}), 200
    except Exception as e:
        print(f"Contact form error: {e}")
        return jsonify({'error': 'Failed to send message. Please try again later.'}), 500

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/history")
def history_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for("login_page"))
    return render_template("history.html")

# Example API for recording actions
@app.route('/api/record_action', methods=['POST'])
def record_action():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    action = data.get('action')
    if action:
        log_action(user_id, action)
        return jsonify({'message': 'Action recorded'}), 200
    return jsonify({'error': 'Action required'}), 400

# ==============================
# CONFIGURATION
# ==============================
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max upload

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)
# Try available Gemini models in order of preference
MODEL_NAMES = ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"]
model = None
for model_name in MODEL_NAMES:
    try:
        model = genai.GenerativeModel(model_name)
        print(f"Using Gemini model: {model_name}")
        break
    except Exception as e:
        print(f"Model {model_name} not available: {e}")
        continue

if not model:
    print("Warning: No Gemini model available")
    model = genai.GenerativeModel("gemini-pro")  # Default fallback

# Groq API Configuration (Fallback)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ==============================
# HELPERS
# ==============================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_file_text(file, ext):
    if ext == "txt":
        return file.read().decode("utf-8")
    elif ext == "pdf":
        reader = PyPDF2.PdfReader(file)
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        return text
    elif ext == "docx":
        tmp_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
        file.save(tmp_path)
        text = docx2txt.process(tmp_path)
        os.remove(tmp_path)
        return text
    return ""


def call_gemini(prompt, max_retries=2):
    """Call Gemini API with retry logic."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            print("[DEBUG] Gemini raw response:", repr(response))
            # Compatible with Gemini SDK: check if response has text or candidates
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            elif hasattr(response, "candidates") and response.candidates:
                return response.candidates[0].content.strip()
        except Exception as e:
            print(f"Gemini API Error (attempt {attempt + 1}/{max_retries}):", e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, etc.
    return None


def call_groq(prompt, max_retries=2):
    """Call Groq API as fallback (free, fast alternative)."""
    if not groq_client:
        print("Groq API key not configured")
        return None
    
    # Use currently available Groq models (mixtral-8x7b-32768 is decommissioned)
    GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
    
    for attempt in range(max_retries):
        for model_name in GROQ_MODELS:
            try:
                # Correct Groq SDK API call with proper method structure
                message = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2048,
                )
                print("[DEBUG] Groq raw message:", repr(message))
                # Extract text from proper Groq response structure
                if message.choices and len(message.choices) > 0:
                    return message.choices[0].message.content.strip()
            except Exception as e:
                error_msg = str(e)
                # If model is decommissioned, try next model
                if "decommissioned" in error_msg or "not found" in error_msg:
                    print(f"Groq model {model_name} not available, trying next...")
                    continue
                # Otherwise log error and retry after backoff
                print(f"Groq API Error (attempt {attempt + 1}/{max_retries}):", e)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                break
    return None


def call_ai(prompt):
    """
    Call AI with automatic fallback.
    Tries Gemini first, then falls back to Groq if Gemini fails.
    """
    # Try Gemini first (primary service)
    result = call_gemini(prompt)
    if result:
        print("✓ Response generated using Gemini")
        return result
    
    # Fallback to Groq (free alternative)
    print("⚠ Gemini failed, trying Groq...")
    result = call_groq(prompt)
    if result:
        print("✓ Response generated using Groq (Fallback)")
        return result
    
    # If both fail, return None
    print("✗ Both AI services failed")
    return None


# ==============================
# ROUTES
# ==============================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/summarize", methods=["POST"])
def summarize():
    user_id = session.get('user_id')
    data = request.get_json()
    text = data.get("text", "").strip()
    length = data.get("length", "medium")  # short, medium, long

    if not text:
        return jsonify({"error": "No text provided"}), 400

    prompt = (
        f"Summarize the following text ({length} summary) in a structured, student-friendly format using Markdown.\n\n"
        "Please follow this EXACT structure:\n"
        "📌 Topic Summary\n"
        "• [Key Point 1]\n"
        "• [Key Point 2]\n\n"
        "🧠 Important Terms\n"
        "- Term → Meaning\n\n"
        "📘 Example\n"
        "[A simple real-world example to illustrate the concept]\n\n"
        "⚠️ Exam Tip\n"
        "[A one-liner exam insight or common pitfall]\n\n"
        f"TEXT TO SUMMARIZE:\n{text}"
    )
    debug_path = os.path.join(tempfile.gettempdir(), "ai_debug.log")
    try:
        with open(debug_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] Calling call_ai; prompt_len={len(prompt)}\n")
    except Exception:
        pass

    summary = call_ai(prompt)

    try:
        with open(debug_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] call_ai_returned_is_None={summary is None}\n")
    except Exception:
        pass

    if not summary:
        return jsonify({"error": "Failed to generate summary"}), 500

    # Log action if user is logged in (store full summary)
    if user_id:
        log_action(user_id, f"Summary ({length}): {summary}")

    return jsonify({"summary": summary})


@app.route("/api/ask", methods=["POST"])
def ask_question():
    user_id = session.get('user_id')
    data = request.get_json()
    text = data.get("text", "").strip()
    question = data.get("question", "").strip()

    if not text or not question:
        return jsonify({"error": "Missing text or question"}), 400

    prompt = (
        "You are a study assistant. Answer the question based ONLY on the provided text.\n"
        "Format your response clearly using bullet points if necessary.\n"
        "If the answer is not found, give a simple explanation.\n"
        f"TEXT: {text}\n\nQUESTION: {question}"
    )

    answer = call_ai(prompt)

    if not answer:
        return jsonify({"error": "Failed to generate answer"}), 500

    # Log action if user is logged in (store full Q&A)
    if user_id:
        log_action(user_id, f"Q&A - Question: {question} | Answer: {answer}")

    return jsonify({"answer": answer})


@app.route("/api/quiz", methods=["POST"])
def generate_quiz():
    user_id = session.get('user_id')
    data = request.get_json()
    text = data.get("text", "").strip()
    q_type = data.get("type", "mcq")
    count = int(data.get("count", 5))

    if not text:
        return jsonify({"error": "No text provided"}), 400

    prompt = (
        f"Generate {count} {q_type.upper()} questions from this text.\n"
        "Return the response ONLY as a JSON array of objects. Do not include any other text or markdown formatting.\n"
        "Each object must have: 'question', 'options' (array of strings, e.g., 4 for MCQ, or ['True', 'False'] for TF), and 'answer' (the exact string value of the correct option).\n\n"
        f"TEXT:\n{text}"
    )

    quiz_raw = call_ai(prompt)

    if not quiz_raw:
        return jsonify({"error": "Failed to generate quiz"}), 500

    # Clean the response in case Gemini wraps it in ```json ... ```
    quiz_clean = quiz_raw.strip()
    if quiz_clean.startswith("```"):
        # Remove starting ```json or ```
        quiz_clean = re.sub(r'^```(?:json)?\n?', '', quiz_clean)
        # Remove ending ```
        quiz_clean = re.sub(r'\n?```$', '', quiz_clean)
    
    try:
        import json
        quiz_data = json.loads(quiz_clean)
    except Exception as e:
        print("JSON Parse Error:", e, "Raw output:", quiz_raw)
        return jsonify({"error": "Failed to parse quiz data"}), 500

    # Log action if user is logged in
    if user_id:
        log_action(user_id, f"Quiz generated ({q_type})")

    return jsonify({"quiz": quiz_data})

@app.route("/api/flashcards", methods=["POST"])
def generate_flashcards():
    user_id = session.get('user_id')
    data = request.get_json()
    text = data.get("text", "").strip()
    count = int(data.get("count", 5))

    if not text:
        return jsonify({"error": "No text provided"}), 400

    prompt = (
        f"Generate {count} flashcards from this text.\n"
        "Return the response ONLY as a JSON array of objects. Do not include any other text or markdown formatting.\n"
        "Each object MUST have: 'question' and 'answer'.\n\n"
        f"TEXT:\n{text}"
    )

    raw_output = call_ai(prompt)
    if not raw_output:
        return jsonify({"error": "Failed to generate flashcards"}), 500

    clean_output = raw_output.strip()
    if clean_output.startswith("```"):
        clean_output = re.sub(r'^```(?:json)?\n?', '', clean_output)
        clean_output = re.sub(r'\n?```$', '', clean_output)

    try:
        import json
        flashcards = json.loads(clean_output)
    except Exception as e:
        print("Flashcard Parse Error:", e, "Raw:", raw_output)
        return jsonify({"error": "Failed to parse flashcards"}), 500

    if user_id:
        log_action(user_id, f"Flashcards generated ({count})")

    return jsonify({"flashcards": flashcards})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()

    try:
        text = extract_file_text(file, ext)
        if not text.strip():
            return jsonify({"error": "File is empty or unreadable"}), 400
        return jsonify({"text": text.strip()})
    except Exception as e:
        print("Upload Error:", e)
        return jsonify({"error": "File processing failed"}), 500


# ==============================
# MAIN
# ==============================
# Error Handlers
@app.errorhandler(Exception)
def handle_all_errors(error):
    if wants_json() or request.method == 'POST':
        return jsonify({
            "error": "Server error",
            "message": str(error) if app.debug else "Internal server error"
        }), 500
    # Return HTML for regular pages
    return render_template('error.html', error=error), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
