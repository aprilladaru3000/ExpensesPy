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
BUDGET_FILE = Path(__file__).with_name("budget.json")
RECURRING_FILE = Path(__file__).with_name("recurring.json")

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))

def load_budget():
    if BUDGET_FILE.exists():
        return json.loads(BUDGET_FILE.read_text()).get("budget", 0)
    return 0

def save_budget(amount):
    BUDGET_FILE.write_text(json.dumps({"budget": amount}, indent=2))

def load_recurring():
    if RECURRING_FILE.exists():
        return json.loads(RECURRING_FILE.read_text())
    return []

def save_recurring(data):
    RECURRING_FILE.write_text(json.dumps(data, indent=2))

# Utility: Add due recurring expenses to main data
def apply_due_recurring():
    data = load_data()
    recs = load_recurring()
    now = dt.datetime.now().date()
    updated = False
    for rec in recs:
        last_applied = rec.get("last_applied")
        freq = rec["frequency"]
        start_date = dt.datetime.fromisoformat(rec["start_date"]).date()
        if last_applied:
            last = dt.datetime.fromisoformat(last_applied).date()
        else:
            last = start_date - dt.timedelta(days=1)
        # Find next due date
        next_due = last
        while True:
            if freq == "daily":
                next_due += dt.timedelta(days=1)
            elif freq == "weekly":
                next_due += dt.timedelta(weeks=1)
            elif freq == "monthly":
                # Add 1 month (approx)
                month = next_due.month + 1 if next_due.month < 12 else 1
                year = next_due.year if next_due.month < 12 else next_due.year + 1
                day = min(next_due.day, 28)  # avoid invalid dates
                next_due = dt.date(year, month, day)
            if next_due > now:
                break
            if next_due >= start_date:
                # Add expense
                data.append({
                    "id": str(uuid.uuid4()),
                    "desc": rec["desc"],
                    "amount": rec["amount"],
                    "category": rec["category"],
                    "ts": dt.datetime.combine(next_due, dt.datetime.min.time()).isoformat()
                })
                rec["last_applied"] = next_due.isoformat()
                updated = True
    if updated:
        save_data(data)
        save_recurring(recs)

@app.route('/set_budget', methods=['GET', 'POST'])
def set_budget():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('budget', 0))
            save_budget(amount)
            flash('Budget updated!')
            return redirect(url_for('dashboard'))
        except Exception:
            flash('Invalid budget amount!')
    budget = load_budget()
    return render_template('set_budget.html', budget=budget)

@app.route('/')
def home():
    apply_due_recurring()
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    data = load_data()
    now = dt.datetime.now()
    today_total = sum(tx["amount"] for tx in data if dt.datetime.fromisoformat(tx["ts"]).date() == now.date())
    month_total = sum(tx["amount"] for tx in data if dt.datetime.fromisoformat(tx["ts"]).strftime("%Y-%m") == now.strftime("%Y-%m"))
    num_tx = len(data)
    recent = sorted(data, key=lambda x: x["ts"], reverse=True)[:5]
    # Mini chart: last 7 days
    last7 = [(now.date() - dt.timedelta(days=i)) for i in range(6, -1, -1)]
    last7_labels = [d.strftime('%a %d') for d in last7]
    last7_totals = []
    for d in last7:
        total = sum(tx['amount'] for tx in data if dt.datetime.fromisoformat(tx['ts']).date() == d)
        last7_totals.append(total)
    budget = load_budget()
    budget_progress = month_total / budget * 100 if budget else 0
    return render_template('dashboard.html', today_total=today_total, month_total=month_total, num_tx=num_tx, recent=recent, last7_labels=last7_labels, last7_totals=last7_totals, budget=budget, budget_progress=budget_progress)

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
    budget = load_budget()
    budget_progress = month_total / budget * 100 if budget else 0
    return render_template('summary.html', today_total=today_total, month_total=month_total, by_cat=by_cat, budget=budget, budget_progress=budget_progress)

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

@app.route('/add_recurring', methods=['GET', 'POST'])
def add_recurring():
    if request.method == 'POST':
        desc = request.form.get('desc')
        amount = request.form.get('amount')
        category = request.form.get('category', 'misc')
        frequency = request.form.get('frequency')
        start_date = request.form.get('start_date')
        if not desc or not amount or not frequency or not start_date:
            flash('Missing data!')
            return render_template('add_recurring.html')
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount!')
            return render_template('add_recurring.html')
        recs = load_recurring()
        recs.append({
            "id": str(uuid.uuid4()),
            "desc": desc,
            "amount": amount,
            "category": category,
            "frequency": frequency,
            "start_date": start_date,
            "last_applied": None
        })
        save_recurring(recs)
        flash('Recurring expense added!')
        return redirect(url_for('list_recurring'))
    return render_template('add_recurring.html')

@app.route('/list_recurring')
def list_recurring():
    recs = load_recurring()
    return render_template('list_recurring.html', recs=recs)

if __name__ == '__main__':
    app.run(debug=True)
