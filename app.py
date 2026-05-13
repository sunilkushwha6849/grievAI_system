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

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS citizens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, mobile TEXT, password TEXT, city TEXT,
        is_verified INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dept_name TEXT, officer_name TEXT, email TEXT UNIQUE, password TEXT,
        mobile TEXT, city TEXT, is_verified INTEGER DEFAULT 1)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT UNIQUE, citizen_name TEXT, citizen_email TEXT,
        mobile TEXT, complaint_text TEXT, department TEXT, status TEXT DEFAULT 'pending',
        photo_path TEXT, voice_path TEXT, latitude REAL, longitude REAL, address TEXT, city TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT, citizen_name TEXT, citizen_email TEXT,
        department TEXT, rating INTEGER, message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT, user_type TEXT, title TEXT, message TEXT,
        link TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'admin')''')
    
    # Clear and insert default data
    c.execute("DELETE FROM departments")
    c.execute("DELETE FROM citizens")
    c.execute("DELETE FROM admins")
    
    default_depts = [
        ('Water Supply','Ramesh Sharma','water@grievai.com',hash_password('WaterSupply123'),'9876543201','Bhopal',1),
        ('Electricity','Suresh Verma','electricity@grievai.com',hash_password('Electricity123'),'9876543202','Bhopal',1),
        ('Roads & PWD','Mahesh Patel','roads@grievai.com',hash_password('RoadsPWD123'),'9876543203','Bhopal',1),
        ('Sanitation','Dinesh Kumar','sanitation@grievai.com',hash_password('Sanitation123'),'9876543204','Bhopal',1),
        ('Healthcare','Rakesh Singh','healthcare@grievai.com',hash_password('Healthcare123'),'9876543205','Bhopal',1),
    ]
    for d in default_depts:
        c.execute('INSERT INTO departments VALUES (?,?,?,?,?,?,?)', d)
    
    c.execute("INSERT INTO admins VALUES (1,'Super Admin','admin@grievai.com',?,'super_admin')", (hash_password('admin123'),))
    c.execute("INSERT INTO citizens VALUES (1,'Test Citizen','test@citizen.com','9999999999',?,'Bhopal',1,CURRENT_TIMESTAMP)", (hash_password('test123'),))
    
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
    try:
        conn = get_db()
        conn.execute("INSERT INTO citizens (name, email, mobile, password, city, is_verified) VALUES (?,?,?,?,?,1)",
                    (data['name'], data['email'], data['mobile'], hash_password(data['password']), data.get('city', '')))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Registration successful!'})
    except:
        return jsonify({'success': False, 'message': 'Email already exists!'})

@app.route('/api/citizen/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    row = conn.execute("SELECT * FROM citizens WHERE email=? AND password=?", 
                      (data['email'], hash_password(data['password']))).fetchone()
    conn.close()
    if row:
        session['citizen_logged_in'] = True
        session['citizen_email'] = row['email']
        session['citizen_name'] = row['name']
        return jsonify({'success': True, 'name': row['name'], 'email': row['email'], 'mobile': row['mobile'], 'city': row['city'] or ''})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})

@app.route('/api/citizen/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

# ============== PROFILE ==============
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
    return jsonify({'success': True, 'message': 'Password changed!'})

@app.route('/api/citizen/profile', methods=['GET'])
def profile():
    email = request.args.get('email')
    conn = get_db()
    user = conn.execute("SELECT name, email, mobile, city FROM citizens WHERE email=?", (email,)).fetchone()
    conn.close()
    return jsonify({'success': True, 'profile': dict(user)})

# ============== COMPLAINTS ==============
@app.route('/api/complaints', methods=['POST'])
def file_complaint():
    try:
        cid = generate_complaint_id()
        conn = get_db()
        conn.execute("""INSERT INTO complaints 
            (complaint_id, citizen_name, citizen_email, mobile, complaint_text, department, latitude, longitude, address, city, photo_path, voice_path)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, request.form['citizen_name'], request.form['citizen_email'], request.form['mobile'],
             request.form['complaint_text'], request.form['department'],
             request.form.get('latitude'), request.form.get('longitude'), request.form.get('address', ''),
             request.form.get('city', ''), None, None))
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
    conn.execute("UPDATE complaints SET status=? WHERE id=?", (data['status'], data['id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============== FEEDBACK ==============
@app.route('/api/get-complaint-for-feedback', methods=['POST'])
def get_complaint():
    data = request.json
    conn = get_db()
    complaint = conn.execute("SELECT * FROM complaints WHERE complaint_id=? AND citizen_email=?", 
                            (data['complaint_id'], data['email'])).fetchone()
    if not complaint:
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
    return jsonify({'success': True, 'message': 'Feedback submitted!'})

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
    conn = get_db()
    rows = conn.execute("SELECT * FROM notifications WHERE user_email=? ORDER BY created_at DESC LIMIT 30", (email,)).fetchall()
    unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_email=? AND is_read=0", (email,)).fetchone()[0]
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
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_email=?", (data['email'],))
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
        session['dept_logged_in'] = True
        return jsonify({'success': True, 'dept_name': row['dept_name'], 'officer_name': row['officer_name'], 'email': row['email']})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})

# ============== ADMIN ==============
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data['email'] == 'admin@grievai.com' and data['password'] == 'admin123':
        session['admin_logged_in'] = True
        return jsonify({'success': True, 'name': 'Super Admin', 'role': 'super_admin'})
    return jsonify({'success': False, 'message': 'Invalid credentials!'})

@app.route('/api/admin/all-data', methods=['GET'])
def admin_all_data():
    conn = get_db()
    complaints = [dict(r) for r in conn.execute("SELECT * FROM complaints ORDER BY created_at DESC").fetchall()]
    citizens = [dict(r) for r in conn.execute("SELECT id, name, email, mobile, city FROM citizens").fetchall()]
    departments = [dict(r) for r in conn.execute("SELECT * FROM departments").fetchall()]
    conn.close()
    return jsonify({'complaints': complaints, 'citizens': citizens, 'departments': departments})

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

@app.route('/api/chat', methods=['POST'])
def chat():
    msg = request.json.get('message', '').lower()
    if any(w in msg for w in ['namaste', 'hello', 'hi']):
        return jsonify({'response': '🙏 नमस्ते! मैं GrievAI सहायक हूं।'})
    if any(w in msg for w in ['shikayat', 'complaint']):
        return jsonify({'response': '📝 Citizen Portal में लॉगिन करें और "नई शिकायत" पर क्लिक करें।'})
    return jsonify({'response': '🤔 कृपया "help" टाइप करें।'})

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  🏛️ GRIEVAI PORTAL READY!")
    print(f"  🌐 {BASE_URL}")
    print("  👑 Admin: admin@grievai.com / admin123")
    print("  👤 Citizen: test@citizen.com / test123")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=PORT)
