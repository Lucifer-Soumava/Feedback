from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json, os
from datetime import datetime
from collections import Counter

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this to something strong

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.json")

ADMIN_PASSWORD = "admin123"  # change for security

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/feedback', methods=['POST'])
def feedback():
    feedback_data = {
        "name": request.form['name'],
        "email": request.form['email'],
        "message": request.form['message'],
        "rating": int(request.form['rating']),
        "date": datetime.now().isoformat()
    }

    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(feedback_data) + "\n")

    return jsonify({"status": "success", "message": "Thank you for your feedback!"})

# ---------- ADMIN LOGIN ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('chart'))
        else:
            return render_template('admin.html', error="❌ Wrong password")
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# ---------- PROTECTED CHART ----------
@app.route('/chart')
def chart():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    return render_template('chart.html')

# ---------- LIVE CHART DATA ----------
@app.route('/chart-data')
def chart_data():
    if not session.get('admin'):
        return jsonify({"error": "unauthorized"}), 403

    ratings = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r") as f:
            for line in f:
                try:
                    feedback = json.loads(line.strip())
                    ratings.append(feedback.get("rating", 0))
                except:
                    pass

    count = Counter(ratings)
    chart_data = [count.get(1,0), count.get(2,0), count.get(3,0), count.get(4,0), count.get(5,0)]

    return jsonify(chart_data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
