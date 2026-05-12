from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import sqlite3
import hashlib
import datetime
import os
import random
import secrets
from functools import wraps
from time import time

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

DB_PATH = 'grievai.db'
OTP_STORE = {}
VERIFICATION_TOKENS = {}
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import sqlite3
import hashlib
import datetime
import os
import random
import secrets
from functools import wraps
from time import time

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

DB_PATH = 'grievai.db'
OTP_STORE = {}
VERIFICATION_TOKENS = {}
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================================
# ⚠️ यहाँ अपना Gmail और App Password डालें ⚠️
# ==============================================
EMAIL_ENABLED = True   # ← False से True करें
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'kushwahasunil6341@gmail.com',    # ← अपना Gmail डालें
    'sender_password': 'igcbslgmehzweqhu' # ← App Password डालें
}
# ==============================================

# ==============================================
# EMAIL FUNCTIONS - ADD THIS TO YOUR app.py
# ==============================================

def send_email_async(recipient, subject, body):
    """Send email in background thread"""
    def send():
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
            server.quit()
            print(f"✅ Email sent to {recipient}")
        except Exception as e:
            print(f"❌ Email error: {e}")
    
    import threading
    thread = threading.Thread(target=send)
    thread.start()

def send_verification_email(email, name, token):
    """Send verification email to user"""
    verification_link = f"http://localhost:5000/verify-email?token={token}&email={email}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial; text-align: center; background: #f4f6fb; padding: 20px;">
        <div style="max-width: 450px; margin: auto; background: white; border-radius: 16px; padding: 30px;">
            <div style="background: linear-gradient(135deg,#1B8A4E,#0E6B6B); padding: 15px; border-radius: 12px;">
                <h1 style="color: white; margin: 0;">🏛️ GrievAI</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0;">मध्य प्रदेश सरकार</p>
            </div>
            
            <h2 style="color: #1B8A4E;">नमस्ते {name}! 👋</h2>
            <p>कृपया अपना ईमेल वेरिफाई करने के लिए नीचे दिए गए बटन पर क्लिक करें:</p>
            
            <a href="{verification_link}" style="background: #1B8A4E; color: white; padding: 12px 28px; text-decoration: none; border-radius: 50px; display: inline-block; margin: 20px 0;">✅ Verify Email</a>
            
            <p style="font-size: 12px; color: #666;">या इस लिंक को कॉपी करें:<br>{verification_link}</p>
            <p style="font-size: 12px; color: #999;">यह लिंक 24 घंटे के लिए वैध है।</p>
        </div>
    </body>
    </html>
    """
    
    if EMAIL_ENABLED:
        send_email_async(email, "GrievAI - Verify Your Email", html_body)
    else:
        print(f"\n📧 [DEMO] Email would be sent to: {email}")
        print(f"🔗 Verification link: {verification_link}\n")

# ==============================================
# DATABASE FUNCTIONS
# ==============================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_complaint_id():
    now = datetime.datetime.now()
    rand = ''.join(random.choices('0123456789', k=4))
    return f"GRV{now.strftime('%y%m%d')}{rand}"

def generate_otp():
    return ''.join(random.choices('0123456789', k=6))

def generate_verification_token():
    return secrets.token_urlsafe(32)

# ==============================================
# INIT DATABASE - COMPLETE
# ==============================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("📦 Creating tables...")
    
    # Citizens table
    c.execute('''CREATE TABLE IF NOT EXISTS citizens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, 
        email TEXT UNIQUE NOT NULL,
        mobile TEXT NOT NULL, 
        password TEXT NOT NULL,
        city TEXT DEFAULT '',
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    print("✓ citizens table ready")
    
    # Departments table
    c.execute('''CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dept_name TEXT NOT NULL, 
        officer_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL, 
        password TEXT NOT NULL,
        mobile TEXT DEFAULT '',
        city TEXT DEFAULT '',
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    print("✓ departments table ready")
    
    # Complaints table
    c.execute('''CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT UNIQUE NOT NULL,
        citizen_name TEXT NOT NULL, 
        citizen_email TEXT NOT NULL,
        mobile TEXT NOT NULL, 
        complaint_text TEXT NOT NULL,
        department TEXT NOT NULL, 
        status TEXT DEFAULT 'pending',
        photo_path TEXT DEFAULT NULL, 
        voice_path TEXT DEFAULT NULL,
        latitude REAL DEFAULT NULL, 
        longitude REAL DEFAULT NULL,
        address TEXT DEFAULT NULL,
        city TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    print("✓ complaints table ready")
    
    # Feedback table
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT, 
        user_type TEXT DEFAULT 'citizen',
        rating INTEGER, 
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    print("✓ feedback table ready")
    
    # Admins table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        mobile TEXT DEFAULT '',
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    print("✓ admins table ready")
    
    # Insert default data
    c.execute("DELETE FROM departments")
    c.execute("DELETE FROM citizens")
    c.execute("DELETE FROM admins")
    
    # Default departments
    default_depts = [
        ('Water Supply','Ramesh Sharma','water@grievai.com',hash_password('WaterSupply123'),'9876543201','Bhopal',1),
        ('Electricity','Suresh Verma','electricity@grievai.com',hash_password('Electricity123'),'9876543202','Bhopal',1),
        ('Roads & PWD','Mahesh Patel','roads@grievai.com',hash_password('RoadsPWD123'),'9876543203','Bhopal',1),
        ('Sanitation','Dinesh Kumar','sanitation@grievai.com',hash_password('Sanitation123'),'9876543204','Bhopal',1),
        ('Healthcare','Rakesh Singh','healthcare@grievai.com',hash_password('Healthcare123'),'9876543205','Bhopal',1),
    ]
    
    for d in default_depts:
        try:
            c.execute('''INSERT INTO departments 
                (dept_name, officer_name, email, password, mobile, city, is_verified) 
                VALUES (?,?,?,?,?,?,?)''', d)
            print(f"✓ Department added: {d[0]}")
        except Exception as e:
            print(f"⚠️ Department error: {e}")
    
    # Admin
    try:
        c.execute('''INSERT OR IGNORE INTO admins (name, email, password, mobile, role) 
                     VALUES (?,?,?,?,?)''',
                  ('Super Admin', 'admin@grievai.com', hash_password('admin123'), '9999999999', 'super_admin'))
        print("✓ Admin created")
    except Exception as e:
        print(f"⚠️ Admin error: {e}")
    
    # Test citizens (pre-verified)
    try:
        c.execute('''INSERT OR IGNORE INTO citizens (name, email, mobile, password, city, is_verified) 
                     VALUES (?,?,?,?,?,?)''',
                  ('Test Citizen', 'test@citizen.com', '9999999999', hash_password('test123'), 'Bhopal', 1))
        print("✓ Test citizen added")
    except Exception as e:
        print(f"⚠️ Citizen error: {e}")
    
    conn.commit()
    conn.close()
    
    print("✅ Database initialized successfully!")

# ==============================================
# PAGES
# ==============================================

@app.route('/') 
def index(): 
    return render_template('index.html')

@app.route('/citizen') 
def citizen_page(): 
    return render_template('citizen_login.html')

@app.route('/citizen/dashboard') 
def citizen_dash(): 
    return render_template('citizen_dashboard.html')

@app.route('/department') 
def dept_page(): 
    return render_template('dept_login.html')

@app.route('/department/dashboard') 
def dept_dash(): 
    return render_template('dept_dashboard.html')

@app.route('/admin') 
def admin_page(): 
    return render_template('admin_login.html')

@app.route('/admin/dashboard') 
def admin_dash(): 
    return render_template('admin_dashboard.html')

@app.route('/faq')
def faq_page():
    return render_template('faq.html')

@app.route('/instructions')
def instructions_page():
    return render_template('instructions.html')

# ==============================================
# VERIFICATION ROUTE
# ==============================================
@app.route('/verify-email')
def verify_email():
    token = request.args.get('token')
    email = request.args.get('email')
    
    print(f"🔍 Verification attempt - Email: {email}")
    print(f"📦 Stored tokens: {VERIFICATION_TOKENS}")
    
    if not token or not email:
        return """
        <html>
        <body style="text-align:center; padding:50px; font-family:Arial;">
            <h2 style="color:#C0392B;">❌ Invalid Link</h2>
            <p>Missing token or email address.</p>
            <a href="/citizen">Go to Login →</a>
        </body>
        </html>
        """
    
    # Check if token exists
    stored = VERIFICATION_TOKENS.get(email)
    
    if not stored:
        return f"""
        <html>
        <body style="text-align:center; padding:50px; font-family:Arial;">
            <h2 style="color:#C0392B;">❌ No Verification Found</h2>
            <p>No verification request found for <strong>{email}</strong></p>
            <p>Please <a href="/citizen">register again</a>.</p>
        </body>
        </html>
        """
    
    if stored['token'] != token:
        return f"""
        <html>
        <body style="text-align:center; padding:50px; font-family:Arial;">
            <h2 style="color:#C0392B;">❌ Invalid Token</h2>
            <p>The verification token is incorrect.</p>
            <p>Please <a href="/citizen">register again</a>.</p>
        </body>
        </html>
        """
    
    if datetime.datetime.now() > stored['expires']:
        del VERIFICATION_TOKENS[email]
        return """
        <html>
        <body style="text-align:center; padding:50px; font-family:Arial;">
            <h2 style="color:#C0392B;">❌ Link Expired</h2>
            <p>This link is valid for 24 hours only.</p>
            <p>Please <a href="/citizen">register again</a>.</p>
        </body>
        </html>
        """
    
    # MARK AS VERIFIED IN DATABASE
    conn = get_db()
    conn.execute('UPDATE citizens SET is_verified = 1 WHERE email = ?', (email,))
    conn.commit()
    
    # Verify update worked
    check = conn.execute('SELECT is_verified FROM citizens WHERE email = ?', (email,)).fetchone()
    print(f"✅ After update - is_verified = {check['is_verified'] if check else 'Not found'}")
    
    conn.close()
    
    # Clean up token
    del VERIFICATION_TOKENS[email]
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Email Verified - GrievAI</title>
        <style>
            body { font-family: Arial; background: linear-gradient(135deg,#0E4D2F,#1B8A4E); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: white; border-radius: 20px; padding: 40px; text-align: center; max-width: 400px; }
            h2 { color: #1B8A4E; }
            .btn { background: #1B8A4E; color: white; padding: 12px 30px; text-decoration: none; border-radius: 30px; display: inline-block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>✅ Email Verified Successfully!</h2>
            <p>आपका ईमेल सफलतापूर्वक वेरिफाई हो गया है।</p>
            <p>अब आप लॉगिन कर सकते हैं।</p>
            <a href="/citizen" class="btn">Login Now →</a>
        </div>
    </body>
    </html>
    """
# ==============================================
# API: SEND VERIFICATION
# ==============================================

@app.route('/api/send-verification', methods=['POST'])
def send_verification():
    data = request.json
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'})
    
    token = generate_verification_token()
    VERIFICATION_TOKENS[email] = {
        'token': token,
        'expires': datetime.datetime.now() + datetime.timedelta(hours=24)
    }
    
    verification_link = f"http://localhost:5000/verify-email?token={token}&email={email}"
    print(f"\n{'='*50}")
    print(f"📧 Verification link for {email}:")
    print(f"🔗 {verification_link}")
    print(f"{'='*50}\n")
    
    return jsonify({'success': True, 'message': 'Verification link generated! Check terminal or email.'})

@app.route('/api/check-verification', methods=['POST'])
def check_verification():
    data = request.json
    email = data.get('email', '').strip().lower()
    
    conn = get_db()
    row = conn.execute('SELECT is_verified FROM citizens WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if row and row['is_verified'] == 1:
        return jsonify({'success': True, 'verified': True})
    return jsonify({'success': True, 'verified': False})

# ==============================================
# API: CITIZEN REGISTER
# ==============================================

@app.route('/api/citizen/register', methods=['POST'])
def citizen_register():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    mobile = data.get('mobile', '').strip()
    password = data.get('password', '')
    city = data.get('city', '').strip()
    
    if not all([name, email, mobile, password]):
        return jsonify({'success': False, 'message': 'सभी फील्ड भरें'})
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'पासवर्ड 6+ कैरेक्टर'})
    if len(mobile) != 10 or not mobile.isdigit():
        return jsonify({'success': False, 'message': 'मोबाइल नंबर 10 अंकों का होना चाहिए'})
    
    conn = get_db()
    
    existing = conn.execute('SELECT * FROM citizens WHERE email = ?', (email,)).fetchone()
    if existing:
        if existing['is_verified'] == 1:
            conn.close()
            return jsonify({'success': False, 'message': 'Email already registered and verified!'})
        else:
            # Update existing unverified user
            conn.execute('''UPDATE citizens SET name=?, mobile=?, password=?, city=?, is_verified=0 
                           WHERE email=?''', (name, mobile, hash_password(password), city, email))
            print(f"🔄 Updated existing unverified user: {email}")
    else:
        # Insert new user
        conn.execute('''INSERT INTO citizens (name, email, mobile, password, city, is_verified) 
                       VALUES (?,?,?,?,?,0)''',
                     (name, email, mobile, hash_password(password), city))
        print(f"📝 Created new user: {email}")
    
    conn.commit()
    conn.close()
    
    # Generate verification token and send email
    token = generate_verification_token()
    VERIFICATION_TOKENS[email] = {
        'token': token,
        'expires': datetime.datetime.now() + datetime.timedelta(hours=24)
    }
    
    # Send verification email
    verification_link = f"http://localhost:5000/verify-email?token={token}&email={email}"
    print(f"\n{'='*60}")
    print(f"📧 VERIFICATION LINK FOR {email}:")
    print(f"🔗 {verification_link}")
    print(f"{'='*60}\n")
    
    # Try to send real email if configured
    if EMAIL_ENABLED:
        send_verification_email(email, name, token)
    
    return jsonify({'success': True, 'message': 'Registration successful! Please check your email for verification link.'})
# ==============================================
# API: CITIZEN LOGIN
# ==============================================

@app.route('/api/citizen/login', methods=['POST'])
def citizen_login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    print(f"🔐 Login attempt - Email: {email}")
    
    conn = get_db()
    row = conn.execute('SELECT * FROM citizens WHERE email=? AND password=?', 
                       (email, hash_password(password))).fetchone()
    
    if not row:
        conn.close()
        print(f"❌ Login failed - User not found or wrong password")
        return jsonify({'success': False, 'message': 'Email या पासवर्ड गलत है'})
    
    print(f"📊 User found - is_verified: {row['is_verified']}")
    
    if row['is_verified'] == 0:
        conn.close()
        print(f"❌ Login failed - Email not verified")
        return jsonify({'success': False, 'not_verified': True, 'message': '❌ Please verify your email first! Check your inbox.'})
    
    conn.close()
    print(f"✅ Login successful for {email}")
    
    return jsonify({'success': True, 'name': row['name'], 'email': row['email'], 'mobile': row['mobile'], 'city': row['city'] or ''})
# ==============================================
# RESET PASSWORD ROUTE
# ==============================================

@app.route('/api/citizen/reset-password', methods=['POST'])
def citizen_reset():
    data = request.json
    email = data.get('email', '').strip().lower()
    new_pass = data.get('new_password', '')
    
    if len(new_pass) < 6:
        return jsonify({'success': False, 'message': 'पासवर्ड 6+ कैरेक्टर'})
    
    conn = get_db()
    result = conn.execute('UPDATE citizens SET password=? WHERE email=?', 
                         (hash_password(new_pass), email))
    conn.commit()
    conn.close()
    
    if result.rowcount == 0:
        return jsonify({'success': False, 'message': 'Email नहीं मिला'})
    
    return jsonify({'success': True, 'message': 'पासवर्ड बदल गया!'})

# ==============================================
# API: OTP
# ==============================================

@app.route('/api/otp/send', methods=['POST'])
def send_otp():
    data = request.json
    target = data.get('target', '').strip()
    
    if not target:
        return jsonify({'success': False, 'message': 'Mobile or Email required'})
    
    otp = generate_otp()
    OTP_STORE[target] = {'otp': otp, 'expires': datetime.datetime.now() + datetime.timedelta(minutes=10)}
    
    print(f"\n{'='*40}")
    print(f"[OTP] {target} => {otp}")
    print(f"{'='*40}\n")
    
    return jsonify({'success': True, 'otp': otp, 'message': 'OTP generated!'})

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    data = request.json
    target = data.get('target', '').strip()
    otp_in = data.get('otp', '').strip()
    
    if target not in OTP_STORE:
        return jsonify({'success': False, 'message': 'OTP not requested'})
    
    entry = OTP_STORE[target]
    if datetime.datetime.now() > entry['expires']:
        del OTP_STORE[target]
        return jsonify({'success': False, 'message': 'OTP expired'})
    
    if entry['otp'] != otp_in:
        return jsonify({'success': False, 'message': 'Wrong OTP'})
    
    del OTP_STORE[target]
    return jsonify({'success': True, 'message': 'OTP verified!'})

# ==============================================
# API: COMPLAINTS
# ==============================================

@app.route('/api/complaints', methods=['POST'])
def file_complaint():
    try:
        citizen_name = request.form.get('citizen_name', '').strip()
        citizen_email = request.form.get('citizen_email', '').strip().lower()
        mobile = request.form.get('mobile', '').strip()
        complaint_text = request.form.get('complaint_text', '').strip()
        department = request.form.get('department', '').strip()
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        address = request.form.get('address', '')
        city = request.form.get('city', '')
        
        # Handle voice file
        voice_path = None
        if 'voice' in request.files:
            voice_file = request.files['voice']
            if voice_file and voice_file.filename:
                fname = f"voice_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.webm"
                voice_file.save(os.path.join(UPLOAD_FOLDER, fname))
                voice_path = fname
        
        # Handle photo file
        photo_path = None
        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file and photo_file.filename:
                ext = photo_file.filename.rsplit('.', 1)[-1].lower() if '.' in photo_file.filename else 'jpg'
                fname = f"photo_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                photo_file.save(os.path.join(UPLOAD_FOLDER, fname))
                photo_path = fname
        
        if not all([citizen_name, citizen_email, department]):
            return jsonify({'success': False, 'message': 'सभी जरूरी फील्ड भरें'})
        if not complaint_text:
            complaint_text = '[Media Complaint]'
        
        cid = generate_complaint_id()
        conn = get_db()
        conn.execute('''INSERT INTO complaints
            (complaint_id, citizen_name, citizen_email, mobile, complaint_text, department, 
             photo_path, voice_path, latitude, longitude, address, city)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (cid, citizen_name, citizen_email, mobile, complaint_text, department,
             photo_path, voice_path, latitude, longitude, address, city))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'complaint_id': cid, 'message': 'शिकायत दर्ज हो गई!'})
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/complaints', methods=['GET'])
def get_complaints():
    try:
        email = request.args.get('email')
        dept = request.args.get('department')
        conn = get_db()
        
        if email:
            rows = conn.execute('SELECT * FROM complaints WHERE citizen_email=? ORDER BY created_at DESC', (email,)).fetchall()
        elif dept:
            rows = conn.execute('SELECT * FROM complaints WHERE LOWER(department) = LOWER(?) ORDER BY created_at DESC', (dept,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM complaints ORDER BY created_at DESC').fetchall()
        
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/complaints/update-status', methods=['POST'])
def update_status():
    try:
        data = request.json
        complaint_id = data.get('id')
        new_status = data.get('status')
        
        if not complaint_id or not new_status:
            return jsonify({'success': False, 'message': 'id and status required'})
        
        conn = get_db()
        conn.execute('UPDATE complaints SET status=? WHERE id=?', (new_status, complaint_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Status updated!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================================
# API: DEPARTMENT (Simplified)
# ==============================================

@app.route('/api/department/login', methods=['POST'])
def dept_login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    conn = get_db()
    row = conn.execute('SELECT * FROM departments WHERE email=? AND password=?', 
                       (email, hash_password(password))).fetchone()
    conn.close()
    
    if not row:
        return jsonify({'success': False, 'message': 'Email या पासवर्ड गलत है'})
    if row['is_verified'] == 0:
        return jsonify({'success': False, 'not_verified': True, 'message': '❌ अकाउंट Verify नहीं हुआ है।'})
    
    return jsonify({'success': True, 'dept_name': row['dept_name'], 'officer_name': row['officer_name'], 'email': row['email']})

# ==============================================
# API: ADMIN
# ==============================================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    conn = get_db()
    row = conn.execute('SELECT * FROM admins WHERE email = ? AND password = ?', 
                       (email, hash_password(password))).fetchone()
    conn.close()
    
    if row:
        return jsonify({'success': True, 'name': row['name'], 'role': row['role']})
    return jsonify({'success': False, 'message': 'Admin credentials गलत हैं'})

# ==============================================
# API: FEEDBACK
# ==============================================

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    conn = get_db()
    conn.execute('INSERT INTO feedback (user_name, rating, message) VALUES (?,?,?)',
                 (data.get('user_name', ''), data.get('rating', 5), data.get('message', '')))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'फीडबैक दर्ज हो गया!'})

# ==============================================
# API: CHATBOT
# ==============================================

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'response': 'कृपया कुछ लिखें'})
    
    msg_lower = message.lower()
    
    if any(g in msg_lower for g in ['namaste', 'hello', 'hi', 'नमस्ते']):
        response = "🙏 नमस्ते! मैं GrievAI सहायक हूं। आपकी कैसे मदद कर सकता हूं?"
    elif any(w in msg_lower for w in ['shikayat', 'complaint', 'शिकायत']):
        response = "📝 शिकायत दर्ज करने के लिए Citizen Portal में लॉगिन करें और 'नई शिकायत' टैब पर जाएं।"
    elif any(w in msg_lower for w in ['help', 'मदद']):
        response = "❓ मैं आपकी मदद कर सकता हूं:\n• शिकायत कैसे दर्ज करें?\n• विभागों के बारे में\n• पासवर्ड रीसेट"
    else:
        response = "🤔 मैं आपका प्रश्न समझ नहीं पाया। कृपया 'help' टाइप करें।"
    
    return jsonify({'success': True, 'response': response})

# ==============================================
# START SERVER
# ==============================================

if __name__ == '__main__':
    init_db()
    print("\n" + "=" * 50)
    print("  🏛️ GRIEVAI PORTAL STARTED!")
    print("  🌐 http://localhost:5000")
    print("  👑 Admin: admin@grievai.com / admin123")
    print("  👤 Citizen: test@citizen.com / test123")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)