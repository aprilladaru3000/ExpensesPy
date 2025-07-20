from flask import Flask, render_template, request, redirect, url_for
import json
import datetime as dt
from pathlib import Path
from collections import defaultdict
import uuid

app = Flask(__name__)
DATA_FILE = Path(__file__).with_name("expenses.json")

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add():
    desc = request.form.get('desc')
    amount = request.form.get('amount')
    category = request.form.get('category', 'misc')

    if not desc or not amount:
        return "Missing data", 400

    try:
        amount = float(amount)
    except ValueError:
        return "Invalid amount", 400

    data = load_data()
    data.append({
        "id": str(uuid.uuid4()),
        "desc": desc,
        "amount": amount,
        "category": category,
        "ts": dt.datetime.now().isoformat()
    })
    save_data(data)
    return redirect(url_for('list_tx'))

@app.route('/delete/<id>', methods=['POST'])
def delete(id):
    data = load_data()
    data = [tx for tx in data if tx["id"] != id]
    save_data(data)
    return redirect(url_for('list_tx'))

@app.route('/list')
def list_tx():
    data = sorted(load_data(), key=lambda x: x["ts"], reverse=True)
    return render_template('list.html', transactions=data)

@app.route('/summary')
def summary():
    data = load_data()
    now = dt.datetime.now()
    today_total = sum(tx["amount"]
                      for tx in data
                      if dt.datetime.fromisoformat(tx["ts"]).date() == now.date())
    month_total = sum(tx["amount"]
                      for tx in data
                      if dt.datetime.fromisoformat(tx["ts"]).strftime("%Y-%m") == now.strftime("%Y-%m"))
    by_cat = defaultdict(float)
    for tx in data:
        by_cat[tx["category"]] += tx["amount"]
    return render_template('summary.html',
                           today_total=today_total,
                           month_total=month_total,
                           by_cat=by_cat)

if __name__ == '__main__':
    app.run(debug=True)
