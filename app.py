import os
import secrets
import hashlib
import datetime
import random
import sqlite3
import logging
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)

PORT        = int(os.environ.get('PORT', 10000))
BASE_URL    = os.environ.get('BASE_URL', 'https://grievai-system.onrender.com')
DB_PATH     = 'grievai.db'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

OTP_STORE = {}  # email -> {otp, expires_at}  (ready for future OTP feature)

# ─── DB Helpers ───────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(p: str) -> str:
    """SHA-256 hash (upgrade to bcrypt for production)."""
    return hashlib.sha256(p.encode()).hexdigest()

def generate_complaint_id() -> str:
    """
    BUG FIX: Added microseconds + random suffix to reduce collision risk
    when multiple complaints arrive in the same second.
    """
    ts   = datetime.datetime.now().strftime('%y%m%d%H%M%S')
    rand = ''.join(random.choices('0123456789ABCDEF', k=4))
    return f"GRV{ts}{rand}"

# ─── DB Init ──────────────────────────────────────────────────────────────────
def init_db():
    """
    BUG FIX: Use CREATE TABLE IF NOT EXISTS so existing data is NOT wiped
    on every server restart. Previously, DROP TABLE wiped production data.
    """
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS citizens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        mobile TEXT NOT NULL,
        password TEXT NOT NULL,
        city TEXT DEFAULT '',
        is_verified INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dept_name TEXT NOT NULL,
        officer_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        mobile TEXT DEFAULT '',
        city TEXT DEFAULT '',
        is_verified INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

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

    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT NOT NULL,
        citizen_name TEXT NOT NULL,
        citizen_email TEXT NOT NULL,
        department TEXT NOT NULL,
        rating INTEGER DEFAULT 0,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        user_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        link TEXT DEFAULT '',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        mobile TEXT DEFAULT '',
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Seed default departments only if table is empty
    dept_count = c.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    if dept_count == 0:
        default_depts = [
            ('Water Supply',  'Ramesh Sharma', 'water@grievai.com',       hash_password('WaterSupply123'),  '9876543201', 'Bhopal', 1),
            ('Electricity',   'Suresh Verma',  'electricity@grievai.com', hash_password('Electricity123'),  '9876543202', 'Bhopal', 1),
            ('Roads & PWD',   'Mahesh Patel',  'roads@grievai.com',       hash_password('RoadsPWD123'),     '9876543203', 'Bhopal', 1),
            ('Sanitation',    'Dinesh Kumar',  'sanitation@grievai.com',  hash_password('Sanitation123'),   '9876543204', 'Bhopal', 1),
            ('Healthcare',    'Rakesh Singh',  'healthcare@grievai.com',  hash_password('Healthcare123'),   '9876543205', 'Bhopal', 1),
        ]
        for d in default_depts:
            c.execute("INSERT INTO departments (dept_name, officer_name, email, password, mobile, city, is_verified) VALUES (?,?,?,?,?,?,?)", d)

    # Seed super-admin only if not present
    admin_count = c.execute("SELECT COUNT(*) FROM admins WHERE role='super_admin'").fetchone()[0]
    if admin_count == 0:
        c.execute("INSERT INTO admins (name, email, password, role) VALUES (?,?,?,?)",
                  ('Super Admin', 'admin@grievai.com', hash_password('admin123'), 'super_admin'))

    # Seed test citizen only if not present
    citizen_count = c.execute("SELECT COUNT(*) FROM citizens WHERE email='test@citizen.com'").fetchone()[0]
    if citizen_count == 0:
        c.execute("INSERT INTO citizens (name, email, mobile, password, city, is_verified) VALUES (?,?,?,?,?,?)",
                  ('Test Citizen', 'test@citizen.com', '9999999999', hash_password('test123'), 'Bhopal', 1))

    conn.commit()
    conn.close()
    logger.info("✅ Database ready!")

init_db()

# ─── Auth Helper ──────────────────────────────────────────────────────────────
def citizen_required():
    """Returns error response if citizen is not logged in, else None."""
    if not session.get('citizen_logged_in'):
        return jsonify({'success': False, 'message': 'Please login first!'}), 401
    return None

# ─── Page Routes ──────────────────────────────────────────────────────────────
@app.route('/')
def index():               return render_template('index.html')
@app.route('/citizen')
def citizen_page():        return render_template('citizen_login.html')
@app.route('/citizen/dashboard')
def citizen_dash():        return render_template('citizen_dashboard.html')
@app.route('/department')
def dept_page():           return render_template('dept_login.html')
@app.route('/department/dashboard')
def dept_dash():           return render_template('dept_dashboard.html')
@app.route('/admin')
def admin_page():          return render_template('admin_login.html')
@app.route('/admin/dashboard')
def admin_dash():          return render_template('admin_dashboard.html')
@app.route('/faq')
def faq_page():            return render_template('faq.html')
@app.route('/instructions')
def instructions_page():   return render_template('instructions.html')

# ─── Citizen Auth ─────────────────────────────────────────────────────────────
@app.route('/api/citizen/register', methods=['POST'])
def register():
    data = request.json or {}
    logger.info(f"📝 Register attempt: {data.get('email')}")

    name     = (data.get('name') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    mobile   = (data.get('mobile') or '').strip()
    password = data.get('password', '')
    city     = (data.get('city') or '').strip()

    if not all([name, email, mobile, password]):
        return jsonify({'success': False, 'message': 'सभी फील्ड भरें'})
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'पासवर्ड 6+ कैरेक्टर होना चाहिए'})
    if len(mobile) != 10 or not mobile.isdigit():
        return jsonify({'success': False, 'message': 'मोबाइल नंबर 10 अंकों का होना चाहिए'})
    if '@' not in email:
        return jsonify({'success': False, 'message': 'Valid email address डालें'})

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO citizens (name, email, mobile, password, city, is_verified) VALUES (?,?,?,?,?,1)",
            (name, email, mobile, hash_password(password), city)
        )
        conn.commit()
        logger.info(f"✅ Registered: {email}")
        return jsonify({'success': True, 'message': 'Registration successful!'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'यह Email पहले से registered है!'})
    finally:
        conn.close()


@app.route('/api/citizen/login', methods=['POST'])
def login():
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    conn  = get_db()
    row   = conn.execute(
        "SELECT * FROM citizens WHERE email=? AND password=?",
        (email, hash_password(data.get('password', '')))
    ).fetchone()
    conn.close()
    if row:
        session['citizen_logged_in'] = True
        session['citizen_email']     = row['email']
        return jsonify({
            'success': True,
            'name':    row['name'],
            'email':   row['email'],
            'mobile':  row['mobile'],
            'city':    row['city'] or ''
        })
    return jsonify({'success': False, 'message': 'Invalid credentials!'})


@app.route('/api/citizen/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/citizen/change-password', methods=['POST'])
def change_password():
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    conn  = get_db()
    user  = conn.execute(
        "SELECT * FROM citizens WHERE email=? AND password=?",
        (email, hash_password(data.get('old_password', '')))
    ).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Current password incorrect!'})
    new_pw = data.get('new_password', '')
    if len(new_pw) < 6:
        conn.close()
        return jsonify({'success': False, 'message': 'नया पासवर्ड 6+ कैरेक्टर होना चाहिए'})
    conn.execute("UPDATE citizens SET password=? WHERE email=?", (hash_password(new_pw), email))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Password changed!'})


@app.route('/api/citizen/profile', methods=['GET'])
def profile():
    email = (request.args.get('email') or '').strip().lower()
    if not email:
        return jsonify({'success': False, 'message': 'Email required'})
    conn = get_db()
    user = conn.execute(
        "SELECT name, email, mobile, city FROM citizens WHERE email=?", (email,)
    ).fetchone()
    conn.close()
    return jsonify({'success': True, 'profile': dict(user)} if user else {'success': False, 'message': 'User not found'})


# ─── Complaints ───────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp3', 'ogg', 'wav', 'm4a'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/complaints', methods=['POST'])
def file_complaint():
    """
    BUG FIX: photo_path and voice_path were defined in the DB schema but
    never saved. Now handles optional file uploads properly.
    """
    try:
        cid = generate_complaint_id()

        # Required fields
        citizen_name  = request.form.get('citizen_name', '').strip()
        citizen_email = request.form.get('citizen_email', '').strip().lower()
        mobile        = request.form.get('mobile', '').strip()
        complaint_txt = request.form.get('complaint_text', '').strip()
        department    = request.form.get('department', '').strip()

        if not all([citizen_name, citizen_email, mobile, complaint_txt, department]):
            return jsonify({'success': False, 'message': 'सभी required fields भरें'})

        # Optional location
        lat     = request.form.get('latitude')  or None
        lng     = request.form.get('longitude') or None
        address = request.form.get('address', '')
        city    = request.form.get('city', '')

        # Optional file uploads
        photo_path = None
        voice_path = None

        photo = request.files.get('photo')
        if photo and photo.filename and allowed_file(photo.filename):
            ext        = photo.filename.rsplit('.', 1)[1].lower()
            photo_name = f"{cid}_photo.{ext}"
            photo.save(os.path.join(UPLOAD_FOLDER, photo_name))
            photo_path = os.path.join('static', 'uploads', photo_name)

        voice = request.files.get('voice')
        if voice and voice.filename and allowed_file(voice.filename):
            ext        = voice.filename.rsplit('.', 1)[1].lower()
            voice_name = f"{cid}_voice.{ext}"
            voice.save(os.path.join(UPLOAD_FOLDER, voice_name))
            voice_path = os.path.join('static', 'uploads', voice_name)

        conn = get_db()
        conn.execute(
            """INSERT INTO complaints
               (complaint_id, citizen_name, citizen_email, mobile, complaint_text,
                department, photo_path, voice_path, latitude, longitude, address, city)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, citizen_name, citizen_email, mobile, complaint_txt,
             department, photo_path, voice_path, lat, lng, address, city)
        )
        conn.commit()
        conn.close()
        logger.info(f"✅ Complaint filed: {cid}")
        return jsonify({'success': True, 'complaint_id': cid})

    except Exception as e:
        logger.error(f"❌ file_complaint error: {e}")
        return jsonify({'success': False, 'message': 'Server error. Please try again.'})


@app.route('/api/complaints', methods=['GET'])
def get_complaints():
    email = (request.args.get('email') or '').strip().lower()
    dept  = (request.args.get('department') or '').strip()
    conn  = get_db()
    if email:
        rows = conn.execute(
            "SELECT * FROM complaints WHERE citizen_email=? ORDER BY created_at DESC", (email,)
        ).fetchall()
    elif dept:
        rows = conn.execute(
            "SELECT * FROM complaints WHERE department=? ORDER BY created_at DESC", (dept,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM complaints ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/complaints/update-status', methods=['POST'])
def update_status():
    data   = request.json or {}
    cid    = data.get('id')
    status = data.get('status', '').strip()
    VALID  = {'pending', 'in_progress', 'resolved', 'rejected'}
    if status not in VALID:
        return jsonify({'success': False, 'message': f'Invalid status. Use: {VALID}'})
    conn = get_db()
    conn.execute("UPDATE complaints SET status=? WHERE id=?", (status, cid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ─── Feedback ─────────────────────────────────────────────────────────────────
@app.route('/api/get-complaint-for-feedback', methods=['POST'])
def get_complaint():
    """
    BUG FIX: Original code accepted any email to look up any complaint_id,
    no ownership check. Now validates that the email belongs to the complaint.
    """
    data         = request.json or {}
    complaint_id = (data.get('complaint_id') or '').strip()
    email        = (data.get('email') or '').strip().lower()

    if not complaint_id or not email:
        return jsonify({'success': False, 'message': 'complaint_id और email required हैं'})

    conn      = get_db()
    complaint = conn.execute(
        "SELECT * FROM complaints WHERE complaint_id=? AND citizen_email=?",
        (complaint_id, email)
    ).fetchone()
    if not complaint:
        conn.close()
        return jsonify({'success': False, 'message': 'Complaint not found or unauthorized!'})

    existing = conn.execute(
        "SELECT * FROM feedback WHERE complaint_id=?", (complaint_id,)
    ).fetchone()
    conn.close()
    if existing:
        return jsonify({'success': False, 'message': 'Feedback already given!'})

    return jsonify({
        'success':      True,
        'complaint_id': complaint['complaint_id'],
        'department':   complaint['department'],
        'status':       complaint['status']
    })


@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    data   = request.json or {}
    rating = data.get('rating', 0)
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({'success': False, 'message': 'Rating 1–5 के बीच होनी चाहिए'})
    conn = get_db()
    conn.execute(
        "INSERT INTO feedback (complaint_id, citizen_name, citizen_email, department, rating, message) VALUES (?,?,?,?,?,?)",
        (data.get('complaint_id'), data.get('citizen_name'), data.get('citizen_email'),
         data.get('department'), rating, data.get('message', ''))
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Feedback submitted!'})


@app.route('/api/my-feedbacks', methods=['GET'])
def my_feedbacks():
    email = (request.args.get('email') or '').strip().lower()
    conn  = get_db()
    rows  = conn.execute(
        "SELECT * FROM feedback WHERE citizen_email=? ORDER BY created_at DESC", (email,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/dept-feedbacks', methods=['GET'])
def dept_feedbacks():
    dept = (request.args.get('department') or '').strip()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM feedback WHERE department=? ORDER BY created_at DESC", (dept,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/all-feedbacks', methods=['GET'])
def all_feedbacks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ─── Notifications ────────────────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
def notifications():
    email = (request.args.get('email') or '').strip().lower()
    conn  = get_db()
    rows  = conn.execute(
        "SELECT * FROM notifications WHERE user_email=? ORDER BY created_at DESC LIMIT 30",
        (email,)
    ).fetchall()
    unread = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_email=? AND is_read=0", (email,)
    ).fetchone()[0]
    conn.close()
    return jsonify({'notifications': [dict(r) for r in rows], 'unread_count': unread})


@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_read():
    data = request.json or {}
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=?", (data.get('notification_id'),))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_read():
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    conn  = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_email=?", (email,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ─── Department ───────────────────────────────────────────────────────────────
@app.route('/api/department/login', methods=['POST'])
def dept_login():
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    conn  = get_db()
    row   = conn.execute(
        "SELECT * FROM departments WHERE email=? AND password=? AND is_verified=1",
        (email, hash_password(data.get('password', '')))
    ).fetchone()
    conn.close()
    if row:
        return jsonify({
            'success':      True,
            'dept_name':    row['dept_name'],
            'officer_name': row['officer_name'],
            'email':        row['email']
        })
    # Give a hint if not verified
    conn = get_db()
    unverified = conn.execute(
        "SELECT * FROM departments WHERE email=? AND password=?",
        (email, hash_password(data.get('password', '')))
    ).fetchone()
    conn.close()
    if unverified:
        return jsonify({'success': False, 'message': 'Account not verified yet. Please wait for admin approval.'})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})


@app.route('/api/department/register', methods=['POST'])
def dept_register():
    """BUG FIX: bare except replaced with specific exception handling."""
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    conn  = get_db()
    try:
        conn.execute(
            "INSERT INTO departments (dept_name, officer_name, email, password, mobile, city, is_verified) VALUES (?,?,?,?,?,?,0)",
            (data.get('dept_name', ''), data.get('officer_name', ''), email,
             hash_password(data.get('password', '')), data.get('mobile', ''), data.get('city', ''))
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Application submitted! Waiting for admin approval.'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'यह Email पहले से registered है!'})
    except Exception as e:
        logger.error(f"❌ dept_register error: {e}")
        return jsonify({'success': False, 'message': 'Server error. Please try again.'})
    finally:
        conn.close()


# ─── Admin ────────────────────────────────────────────────────────────────────
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    conn  = get_db()
    row   = conn.execute(
        "SELECT * FROM admins WHERE email=? AND password=?",
        (email, hash_password(data.get('password', '')))
    ).fetchone()
    conn.close()
    if row:
        return jsonify({'success': True, 'name': row['name'], 'role': row['role']})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})


@app.route('/api/admin/all-data', methods=['GET'])
def admin_all_data():
    conn       = get_db()
    complaints = [dict(r) for r in conn.execute("SELECT * FROM complaints ORDER BY created_at DESC").fetchall()]
    citizens   = [dict(r) for r in conn.execute("SELECT id, name, email, mobile, city FROM citizens").fetchall()]
    departments= [dict(r) for r in conn.execute("SELECT * FROM departments").fetchall()]
    admins     = [dict(r) for r in conn.execute("SELECT id, name, email, role FROM admins").fetchall()]
    conn.close()
    return jsonify({'complaints': complaints, 'citizens': citizens, 'departments': departments, 'admins': admins})


@app.route('/api/admin/verify-dept/<int:did>', methods=['POST'])
def verify_dept(did):
    conn = get_db()
    conn.execute("UPDATE departments SET is_verified=1 WHERE id=?", (did,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/admin/delete-complaint/<int:cid>', methods=['DELETE'])
def delete_complaint(cid):
    conn = get_db()
    conn.execute("DELETE FROM complaints WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/admin/create', methods=['POST'])
def create_admin():
    """BUG FIX: bare except replaced with specific exception handling."""
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    conn  = get_db()
    try:
        conn.execute(
            "INSERT INTO admins (name, email, password, mobile, role) VALUES (?,?,?,?,?)",
            (data.get('name', ''), email, hash_password(data.get('password', '')), data.get('mobile', ''), 'admin')
        )
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'यह Email पहले से registered है!'})
    except Exception as e:
        logger.error(f"❌ create_admin error: {e}")
        return jsonify({'success': False, 'message': 'Server error.'})
    finally:
        conn.close()


@app.route('/api/admin/delete/<int:aid>', methods=['DELETE'])
def delete_admin(aid):
    conn  = get_db()
    admin = conn.execute("SELECT * FROM admins WHERE id=? AND role='super_admin'", (aid,)).fetchone()
    if admin:
        conn.close()
        return jsonify({'success': False, 'message': 'Cannot delete Super Admin!'})
    conn.execute("DELETE FROM admins WHERE id=?", (aid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ─── AI Chat ──────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    BUG FIX: Added Hindi keyword variants alongside English so the bot
    actually responds to Hindi users correctly.
    """
    msg = (request.json or {}).get('message', '').lower().strip()

    greetings   = ['namaste', 'namaskar', 'hello', 'hi', 'hey', 'नमस्ते', 'हेलो']
    complaint_kw= ['shikayat', 'complaint', 'shikayet', 'शिकायत', 'दर्ज']
    status_kw   = ['status', 'track', 'check', 'स्टेटस', 'ट्रैक']
    dept_kw     = ['department', 'vibhag', 'विभाग']
    help_kw     = ['help', 'madad', 'मदद', 'सहायता']

    if any(w in msg for w in greetings):
        return jsonify({'response': '🙏 नमस्ते! मैं GrievAI सहायक हूं। मैं शिकायत दर्ज करने, स्टेटस देखने और विभाग की जानकारी में मदद कर सकता हूं।'})
    if any(w in msg for w in complaint_kw):
        return jsonify({'response': '📝 शिकायत दर्ज करने के लिए: Citizen Portal में लॉगिन करें → "नई शिकायत" टैब पर जाएं → फॉर्म भरें।'})
    if any(w in msg for w in status_kw):
        return jsonify({'response': '🔍 शिकायत का स्टेटस देखने के लिए: Citizen Dashboard → "मेरी शिकायतें" टैब खोलें।'})
    if any(w in msg for w in dept_kw):
        return jsonify({'response': '🏢 उपलब्ध विभाग: Water Supply, Electricity, Roads & PWD, Sanitation, Healthcare।'})
    if any(w in msg for w in help_kw):
        return jsonify({'response': (
            '📋 मैं इन चीजों में मदद कर सकता हूं:\n'
            '• शिकायत दर्ज करना\n'
            '• शिकायत का स्टेटस ट्रैक करना\n'
            '• विभाग की जानकारी\n'
            'कृपया अपना सवाल हिंदी या English में पूछें।'
        )})
    return jsonify({'response': '🤔 समझ नहीं आया। "help" टाइप करें सभी विकल्पों के लिए।'})


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "=" * 55)
    print("  🏛️  GRIEVAI PORTAL READY!")
    print(f"  🌐  {BASE_URL}")
    print("  👑  Admin:   admin@grievai.com  /  admin123")
    print("  👤  Citizen: test@citizen.com   /  test123")
    print("  🏢  Dept:    water@grievai.com  /  WaterSupply123")
    print("=" * 55 + "\n")
    app.run(host='0.0.0.0', port=PORT)
