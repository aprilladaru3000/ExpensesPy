from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, Response
import json
import datetime as dt
from pathlib import Path
from collections import defaultdict
import uuid
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for flash messages
DATA_FILE = Path(__file__).with_name("expenses.json")

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))

@app.route('/')
def index():
    message = get_flashed_messages()
    return render_template('index.html', message=message[0] if message else None)

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
    flash('Expense added successfully!')
    return redirect(url_for('list_tx'))

@app.route('/delete/<id>', methods=['POST'])
def delete(id):
    data = load_data()
    data = [tx for tx in data if tx["id"] != id]
    save_data(data)
    flash('Expense deleted!')
    return redirect(url_for('list_tx'))

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    data = load_data()
    tx = next((item for item in data if item["id"] == id), None)
    if not tx:
        return "Expense not found", 404
    if request.method == 'POST':
        desc = request.form.get('desc')
        amount = request.form.get('amount')
        category = request.form.get('category', 'misc')
        if not desc or not amount:
            return "Missing data", 400
        try:
            amount = float(amount)
        except ValueError:
            return "Invalid amount", 400
        tx['desc'] = desc
        tx['amount'] = amount
        tx['category'] = category
        save_data(data)
        flash('Expense updated!')
        return redirect(url_for('list_tx'))
    return render_template('edit.html', tx=tx)

@app.route('/list')
def list_tx():
    data = sorted(load_data(), key=lambda x: x["ts"], reverse=True)
    message = get_flashed_messages()
    return render_template('list.html', transactions=data, message=message[0] if message else None)

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

@app.route('/charts')
def charts():
    data = load_data()
    now = dt.datetime.now()
    # Prepare last 7 days labels and totals
    last7 = [(now.date() - dt.timedelta(days=i)) for i in range(6, -1, -1)]
    last7_labels = [d.strftime('%a %d') for d in last7]
    last7_totals = []
    for d in last7:
        total = sum(tx['amount'] for tx in data if dt.datetime.fromisoformat(tx['ts']).date() == d)
        last7_totals.append(total)
    # Prepare current month daily totals
    month_days = [now.replace(day=1).date() + dt.timedelta(days=i) for i in range(now.day)]
    month_labels = [d.strftime('%d %b') for d in month_days]
    month_totals = []
    for d in month_days:
        total = sum(tx['amount'] for tx in data if dt.datetime.fromisoformat(tx['ts']).date() == d)
        month_totals.append(total)
    # Prepare category totals for current month
    by_cat = defaultdict(float)
    for tx in data:
        tx_date = dt.datetime.fromisoformat(tx['ts'])
        if tx_date.strftime('%Y-%m') == now.strftime('%Y-%m'):
            by_cat[tx['category']] += tx['amount']
    cat_labels = list(by_cat.keys())
    cat_totals = list(by_cat.values())
    return render_template('charts.html',
        last7_labels=last7_labels,
        last7_totals=last7_totals,
        month_labels=month_labels,
        month_totals=month_totals,
        cat_labels=cat_labels,
        cat_totals=cat_totals)

@app.route('/export')
def export():
    data = load_data()
    if not data:
        flash('No data to export!')
        return redirect(url_for('list_tx'))
    def generate():
        fieldnames = ['id', 'desc', 'amount', 'category', 'ts']
        writer = csv.DictWriter(Response(), fieldnames=fieldnames)
        yield ','.join(fieldnames) + '\n'
        for row in data:
            yield ','.join(str(row.get(f, '')) for f in fieldnames) + '\n'
    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=expenses.csv'
    })

if __name__ == '__main__':
    app.run(debug=True)
