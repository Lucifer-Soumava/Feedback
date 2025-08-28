from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from collections import Counter
import os, csv

app = Flask(__name__)
app.secret_key = "supersecretkey_change_me"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "feedback.db")
ADMIN_PASSWORD = "admin123"

# ---------- SQLAlchemy Setup ----------
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_FILE}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    message = db.Column(db.Text)
    rating = db.Column(db.Integer)
    date = db.Column(db.String(50))   # ISO string stored

# Create tables
with app.app_context():
    db.create_all()

# ---------- DB Functions ----------
def insert_feedback(fb):
    feedback = Feedback(
        name=fb["name"],
        email=fb["email"],
        message=fb["message"],
        rating=fb["rating"],
        date=fb["date"]
    )
    db.session.add(feedback)
    db.session.commit()

def read_feedback():
    rows = Feedback.query.all()
    ratings = [r.rating for r in rows]
    entries = [
        {"name": r.name, "email": r.email, "message": r.message, "rating": r.rating, "date": r.date}
        for r in rows
    ]
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
