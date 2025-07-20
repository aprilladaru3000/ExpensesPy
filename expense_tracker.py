import sys, json, datetime as dt
from pathlib import Path
from collections import defaultdict, Counter

DATA_FILE = Path(__file__).with_name("expenses.json")

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))

def add(desc, amount, category="misc"):
    data = load_data()
    data.append({
        "desc": desc,
        "amount": float(amount),
        "category": category,
        "ts": dt.datetime.now().isoformat()
    })
    save_data(data)
    print(f"✔ Added: {desc} – Rp{amount} ({category})")

def list_tx():
    data = sorted(load_data(), key=lambda x: x["ts"], reverse=True)
    if not data:
        print("No transactions yet.")
        return
    for tx in data:
        time = dt.datetime.fromisoformat(tx["ts"]).strftime("%Y-%m-%d %H:%M")
        print(f"{time:16} | {tx['desc']:<20} | {tx['category']:<10} | Rp{tx['amount']:,.0f}")

def summary():
    data = load_data()
    if not data:
        print("No transactions yet.")
        return

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

    print(f"Total spent today ({now:%d %b %Y}): Rp{today_total:,.0f}")
    print(f"Total this month ({now:%b %Y}) : Rp{month_total:,.0f}")
    print("\nBy category:")
    for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  • {cat:<12} Rp{amt:,.0f}")

def help_msg():
    print(__doc__)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help_msg(); sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) >= 4:
        _, _, desc, amount, *rest = sys.argv
        category = rest[0] if rest else "misc"
        add(desc, amount, category)
    elif cmd == "list":
        list_tx()
    elif cmd == "summary":
        summary()
    else:
        help_msg()