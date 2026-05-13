import os
import secrets
import hashlib
import datetime
import random
import sqlite3
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)

PORT = int(os.environ.get('PORT', 10000))
BASE_URL = os.environ.get('BASE_URL', 'https://grievai-system.onrender.com')
DB_PATH = 'grievai.db'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

OTP_STORE = {}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_complaint_id():
    return f"GRV{datetime.datetime.now().strftime('%y%m%d')}{''.join(random.choices('0123456789', k=4))}"

def create_notification(user_email, user_type, title, message, link=''):
    """Create notification for user"""
    try:
        conn = get_db()
        conn.execute('''INSERT INTO notifications (user_email, user_type, title, message, link, is_read, created_at) 
                       VALUES (?,?,?,?,?,0, CURRENT_TIMESTAMP)''',
                    (user_email, user_type, title, message, link))
        conn.commit()
        conn.close()
        print(f"🔔 Notification: {title} -> {user_email}")
    except Exception as e:
        print(f"Notification error: {e}")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Drop and recreate for clean state (remove if you want to keep data)
    c.execute("DROP TABLE IF EXISTS citizens")
    c.execute("DROP TABLE IF EXISTS departments")
    c.execute("DROP TABLE IF EXISTS complaints")
    c.execute("DROP TABLE IF EXISTS feedback")
    c.execute("DROP TABLE IF EXISTS notifications")
    c.execute("DROP TABLE IF EXISTS admins")
    
    c.execute('''CREATE TABLE citizens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, 
        email TEXT UNIQUE NOT NULL,
        mobile TEXT NOT NULL, 
        password TEXT NOT NULL,
        city TEXT DEFAULT '',
        is_verified INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dept_name TEXT NOT NULL, 
        officer_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL, 
        password TEXT NOT NULL,
        mobile TEXT DEFAULT '',
        city TEXT DEFAULT '',
        is_verified INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE complaints (
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
    
    c.execute('''CREATE TABLE feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT NOT NULL,
        citizen_name TEXT NOT NULL,
        citizen_email TEXT NOT NULL,
        department TEXT NOT NULL,
        rating INTEGER DEFAULT 0,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        user_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        link TEXT DEFAULT '',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        mobile TEXT DEFAULT '',
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Default departments
    default_depts = [
        ('Water Supply','Ramesh Sharma','water@grievai.com',hash_password('WaterSupply123'),'9876543201','Bhopal',1),
        ('Electricity','Suresh Verma','electricity@grievai.com',hash_password('Electricity123'),'9876543202','Bhopal',1),
        ('Roads & PWD','Mahesh Patel','roads@grievai.com',hash_password('RoadsPWD123'),'9876543203','Bhopal',1),
        ('Sanitation','Dinesh Kumar','sanitation@grievai.com',hash_password('Sanitation123'),'9876543204','Bhopal',1),
        ('Healthcare','Rakesh Singh','healthcare@grievai.com',hash_password('Healthcare123'),'9876543205','Bhopal',1),
    ]
    for d in default_depts:
        c.execute("INSERT INTO departments (dept_name, officer_name, email, password, mobile, city, is_verified) VALUES (?,?,?,?,?,?,?)", d)
    
    # Admin
    c.execute("INSERT INTO admins (name, email, password, role) VALUES (?,?,?,?)", 
              ('Super Admin', 'admin@grievai.com', hash_password('admin123'), 'super_admin'))
    
    # Test citizen
    c.execute("INSERT INTO citizens (name, email, mobile, password, city, is_verified) VALUES (?,?,?,?,?,?)",
              ('Test Citizen', 'test@citizen.com', '9999999999', hash_password('test123'), 'Bhopal', 1))
    
    # Sample complaint for testing feedback
    c.execute("INSERT INTO complaints (complaint_id, citizen_name, citizen_email, mobile, complaint_text, department, status, city) VALUES (?,?,?,?,?,?,?,?)",
              ('GRV241201001', 'Test Citizen', 'test@citizen.com', '9999999999', 'Sample complaint for feedback', 'Water Supply', 'resolved', 'Bhopal'))
    
    conn.commit()
    conn.close()
    print("✅ Database ready!")

init_db()

@app.route('/')
def index(): return render_template('index.html')
@app.route('/citizen')
def citizen_page(): return render_template('citizen_login.html')
@app.route('/citizen/dashboard')
def citizen_dash(): return render_template('citizen_dashboard.html')
@app.route('/department')
def dept_page(): return render_template('dept_login.html')
@app.route('/department/dashboard')
def dept_dash(): return render_template('dept_dashboard.html')
@app.route('/admin')
def admin_page(): return render_template('admin_login.html')
@app.route('/admin/dashboard')
def admin_dash(): return render_template('admin_dashboard.html')
@app.route('/faq')
def faq_page(): return render_template('faq.html')
@app.route('/instructions')
def instructions_page(): return render_template('instructions.html')

# ============== AUTH ==============
@app.route('/api/citizen/register', methods=['POST'])
def register():
    data = request.json
    if not data.get('name') or not data.get('email') or not data.get('mobile') or not data.get('password'):
        return jsonify({'success': False, 'message': 'सभी फील्ड भरें'})
    if len(data['password']) < 6:
        return jsonify({'success': False, 'message': 'पासवर्ड 6+ कैरेक्टर'})
    if len(data['mobile']) != 10 or not data['mobile'].isdigit():
        return jsonify({'success': False, 'message': 'मोबाइल नंबर 10 अंकों का होना चाहिए'})
    conn = get_db()
    try:
        conn.execute("INSERT INTO citizens (name, email, mobile, password, city, is_verified) VALUES (?,?,?,?,?,1)",
                    (data['name'], data['email'].lower(), data['mobile'], hash_password(data['password']), data.get('city', '')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Registration successful!'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Email already registered!'})
    finally:
        conn.close()

@app.route('/api/citizen/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    row = conn.execute("SELECT * FROM citizens WHERE email=? AND password=?", 
                      (data['email'], hash_password(data['password']))).fetchone()
    conn.close()
    if row:
        session['citizen_logged_in'] = True
        return jsonify({'success': True, 'name': row['name'], 'email': row['email'], 'mobile': row['mobile'], 'city': row['city'] or ''})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})

@app.route('/api/citizen/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/citizen/change-password', methods=['POST'])
def change_password():
    data = request.json
    conn = get_db()
    user = conn.execute("SELECT * FROM citizens WHERE email=? AND password=?", 
                       (data['email'], hash_password(data['old_password']))).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Current password incorrect!'})
    conn.execute("UPDATE citizens SET password=? WHERE email=?", (hash_password(data['new_password']), data['email']))
    conn.commit()
    conn.close()
    create_notification(data['email'], 'citizen', 'Password Changed', 'Your password has been updated successfully.')
    return jsonify({'success': True, 'message': 'Password changed!'})

@app.route('/api/citizen/profile', methods=['GET'])
def profile():
    email = request.args.get('email')
    conn = get_db()
    user = conn.execute("SELECT name, email, mobile, city FROM citizens WHERE email=?", (email,)).fetchone()
    conn.close()
    return jsonify({'success': True, 'profile': dict(user)} if user else {'success': False})

# ============== OTP ==============
@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Email required'})
    otp = ''.join(random.choices('0123456789', k=6))
    OTP_STORE[email] = {'otp': otp, 'expires': datetime.datetime.now() + datetime.timedelta(minutes=10)}
    print(f"📧 OTP for {email}: {otp}")
    return jsonify({'success': True, 'otp': otp, 'message': 'OTP sent!'})

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    stored = OTP_STORE.get(email)
    if not stored:
        return jsonify({'success': False, 'message': 'OTP not requested'})
    if datetime.datetime.now() > stored['expires']:
        del OTP_STORE[email]
        return jsonify({'success': False, 'message': 'OTP expired'})
    if stored['otp'] != otp:
        return jsonify({'success': False, 'message': 'Invalid OTP'})
    del OTP_STORE[email]
    return jsonify({'success': True, 'message': 'OTP verified'})

# ============== COMPLAINTS ==============
@app.route('/api/complaints', methods=['POST'])
def file_complaint():
    try:
        cid = generate_complaint_id()
        conn = get_db()
        conn.execute("""INSERT INTO complaints 
            (complaint_id, citizen_name, citizen_email, mobile, complaint_text, department, latitude, longitude, address, city)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (cid, request.form['citizen_name'], request.form['citizen_email'], request.form['mobile'],
             request.form['complaint_text'], request.form['department'],
             request.form.get('latitude'), request.form.get('longitude'), request.form.get('address', ''),
             request.form.get('city', '')))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'complaint_id': cid})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/complaints', methods=['GET'])
def get_complaints():
    email = request.args.get('email')
    dept = request.args.get('department')
    conn = get_db()
    if email:
        rows = conn.execute("SELECT * FROM complaints WHERE citizen_email=? ORDER BY created_at DESC", (email,)).fetchall()
    elif dept:
        rows = conn.execute("SELECT * FROM complaints WHERE department=? ORDER BY created_at DESC", (dept,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM complaints ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/complaints/update-status', methods=['POST'])
def update_status():
    data = request.json
    conn = get_db()
    # Get complaint details before update
    complaint = conn.execute("SELECT * FROM complaints WHERE id=?", (data['id'],)).fetchone()
    if complaint and data['status'] == 'resolved' and complaint['status'] != 'resolved':
        # Send notification to citizen
        create_notification(complaint['citizen_email'], 'citizen', 
                           f'Complaint Resolved - {complaint["complaint_id"]}', 
                           f'Your complaint has been resolved by {complaint["department"]} department.',
                           '/citizen/dashboard?tab=my')
    conn.execute("UPDATE complaints SET status=? WHERE id=?", (data['status'], data['id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============== FEEDBACK (with Notifications) ==============
@app.route('/api/get-complaint-for-feedback', methods=['POST'])
def get_complaint():
    data = request.json
    conn = get_db()
    complaint = conn.execute("SELECT * FROM complaints WHERE complaint_id=? AND citizen_email=?", 
                            (data['complaint_id'], data['email'])).fetchone()
    if not complaint:
        conn.close()
        return jsonify({'success': False, 'message': 'Complaint not found!'})
    existing = conn.execute("SELECT * FROM feedback WHERE complaint_id=?", (data['complaint_id'],)).fetchone()
    conn.close()
    if existing:
        return jsonify({'success': False, 'message': 'Feedback already given!'})
    return jsonify({'success': True, 'complaint_id': complaint['complaint_id'], 'department': complaint['department'], 'status': complaint['status']})

@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO feedback (complaint_id, citizen_name, citizen_email, department, rating, message) VALUES (?,?,?,?,?,?)",
                (data['complaint_id'], data['citizen_name'], data['citizen_email'], data['department'], data['rating'], data['message']))
    conn.commit()
    conn.close()
    
    # Send notification to department
    create_notification(data['department'], 'department', 
                       f'New Feedback Received - {data["complaint_id"]}', 
                       f'Rating: {data["rating"]}/5\nMessage: {data["message"][:100]}',
                       '/department/dashboard?tab=feedback')
    
    return jsonify({'success': True, 'message': 'Feedback submitted! Thank you!'})

@app.route('/api/my-feedbacks', methods=['GET'])
def my_feedbacks():
    email = request.args.get('email')
    conn = get_db()
    rows = conn.execute("SELECT * FROM feedback WHERE citizen_email=? ORDER BY created_at DESC", (email,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/dept-feedbacks', methods=['GET'])
def dept_feedbacks():
    dept = request.args.get('department')
    conn = get_db()
    rows = conn.execute("SELECT * FROM feedback WHERE department=? ORDER BY created_at DESC", (dept,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/all-feedbacks', methods=['GET'])
def all_feedbacks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ============== NOTIFICATIONS ==============
@app.route('/api/notifications', methods=['GET'])
def notifications():
    email = request.args.get('email')
    user_type = request.args.get('user_type', 'citizen')
    if not email:
        return jsonify({'notifications': [], 'unread_count': 0})
    conn = get_db()
    rows = conn.execute("SELECT * FROM notifications WHERE user_email=? AND user_type=? ORDER BY created_at DESC LIMIT 50", (email, user_type)).fetchall()
    unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_email=? AND user_type=? AND is_read=0", (email, user_type)).fetchone()[0]
    conn.close()
    return jsonify({'notifications': [dict(r) for r in rows], 'unread_count': unread})

@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_read():
    data = request.json
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=?", (data['notification_id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_read():
    data = request.json
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_email=? AND user_type=?", (data['email'], data['user_type']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============== DEPARTMENT ==============
@app.route('/api/department/login', methods=['POST'])
def dept_login():
    data = request.json
    conn = get_db()
    row = conn.execute("SELECT * FROM departments WHERE email=? AND password=?", 
                      (data['email'], hash_password(data['password']))).fetchone()
    conn.close()
    if row:
        return jsonify({'success': True, 'dept_name': row['dept_name'], 'officer_name': row['officer_name'], 'email': row['email']})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})

@app.route('/api/department/register', methods=['POST'])
def dept_register():
    data = request.json
    conn = get_db()
    try:
        conn.execute("INSERT INTO departments (dept_name, officer_name, email, password, mobile, city, is_verified) VALUES (?,?,?,?,?,?,0)",
                    (data['dept_name'], data['officer_name'], data['email'], hash_password(data['password']), data.get('mobile',''), data.get('city','')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Application submitted!'})
    except:
        return jsonify({'success': False, 'message': 'Email exists!'})
    finally:
        conn.close()

# ============== ADMIN ==============
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    conn = get_db()
    row = conn.execute("SELECT * FROM admins WHERE email=? AND password=?", 
                      (data['email'], hash_password(data['password']))).fetchone()
    conn.close()
    if row:
        return jsonify({'success': True, 'name': row['name'], 'role': row['role']})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})

@app.route('/api/admin/all-data', methods=['GET'])
def admin_all_data():
    conn = get_db()
    complaints = [dict(r) for r in conn.execute("SELECT * FROM complaints ORDER BY created_at DESC").fetchall()]
    citizens = [dict(r) for r in conn.execute("SELECT id, name, email, mobile, city FROM citizens").fetchall()]
    departments = [dict(r) for r in conn.execute("SELECT * FROM departments").fetchall()]
    admins = [dict(r) for r in conn.execute("SELECT id, name, email, role FROM admins").fetchall()]
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
    data = request.json
    conn = get_db()
    try:
        conn.execute("INSERT INTO admins (name, email, password, mobile, role) VALUES (?,?,?,?,?)",
                    (data['name'], data['email'], hash_password(data['password']), data.get('mobile',''), 'admin'))
        conn.commit()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})
    finally:
        conn.close()

@app.route('/api/admin/delete/<int:aid>', methods=['DELETE'])
def delete_admin(aid):
    conn = get_db()
    admin = conn.execute("SELECT * FROM admins WHERE id=? AND role='super_admin'", (aid,)).fetchone()
    if admin:
        conn.close()
        return jsonify({'success': False, 'message': 'Cannot delete Super Admin!'})
    conn.execute("DELETE FROM admins WHERE id=?", (aid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
def chat():
    msg = request.json.get('message', '').lower()
    if any(w in msg for w in ['namaste', 'hello', 'hi']):
        return jsonify({'response': '🙏 नमस्ते! मैं GrievAI सहायक हूं।'})
    if any(w in msg for w in ['shikayat', 'complaint']):
        return jsonify({'response': '📝 Citizen Portal में लॉगिन करें और "नई शिकायत" टैब पर जाएं।'})
    return jsonify({'response': '🤔 कृपया "help" टाइप करें।'})

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  🏛️ GRIEVAI PORTAL READY!")
    print(f"  🌐 {BASE_URL}")
    print("  👑 Admin: admin@grievai.com / admin123")
    print("  👤 Citizen: test@citizen.com / test123")
    print("  🏢 Dept: water@grievai.com / WaterSupply123")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=PORT)
