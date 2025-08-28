from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import os, csv, sqlite3
from datetime import datetime
from collections import Counter

app = Flask(__name__)
app.secret_key = "supersecretkey_change_me"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "feedback.db")
ADMIN_PASSWORD = "admin123"

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            message TEXT,
            rating INTEGER,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def insert_feedback(fb):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (name,email,message,rating,date) VALUES (?,?,?,?,?)",
              (fb["name"], fb["email"], fb["message"], fb["rating"], fb["date"]))
    conn.commit()
    conn.close()

def read_feedback():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name,email,message,rating,date FROM feedback")
    rows = c.fetchall()
    conn.close()

    ratings = [r[3] for r in rows]
    entries = [{"name": r[0], "email": r[1], "message": r[2], "rating": r[3], "date": r[4]} for r in rows]
    return ratings, entries

# ---------- PUBLIC ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/feedback', methods=['POST'])
def feedback():
    fb = {
        "name": request.form.get('name', '').strip(),
        "email": request.form.get('email', '').strip(),
        "message": request.form.get('message', '').strip(),
        "rating": int(request.form.get('rating', 0)),
        "date": datetime.now().isoformat(timespec="seconds")
    }

    # Save in SQLite DB only
    insert_feedback(fb)

    return jsonify({"status": "success", "message": "Thank you for your feedback!"})

# ---------- ADMIN LOGIN ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('chart'))
        return render_template('admin.html', error="❌ Wrong password")
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

def require_admin():
    return session.get('admin') is True

# ---------- ADMIN: CHART ----------
@app.route('/chart')
def chart():
    if not require_admin():
        return redirect(url_for('admin_login'))
    ratings, _ = read_feedback()
    avg = round(sum(ratings) / len(ratings), 2) if ratings else 0
    return render_template('chart.html', initial_avg=avg)

@app.route('/chart-data')
def chart_data():
    if not require_admin():
        return jsonify({"error": "unauthorized"}), 403
    ratings, entries = read_feedback()
    count = Counter(ratings)
    buckets = [count.get(1,0), count.get(2,0), count.get(3,0), count.get(4,0), count.get(5,0)]
    total = sum(buckets)
    avg = round(sum(ratings)/total, 2) if total else 0
    latest = entries[-1]["message"] if entries else None
    return jsonify({"buckets": buckets, "average": avg, "total": total, "latest": latest})

# ---------- ADMIN: DOWNLOAD CSV ----------
@app.route('/download-feedback')
def download_feedback():
    if not require_admin():
        return redirect(url_for('admin_login'))
    csv_path = os.path.join(BASE_DIR, "feedback_export.csv")
    _, entries = read_feedback()
    with open(csv_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Name", "Email", "Message", "Rating", "Date"])
        for fb in entries:
            writer.writerow([fb["name"], fb["email"], fb["message"], fb["rating"], fb["date"]])
    return send_file(csv_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
