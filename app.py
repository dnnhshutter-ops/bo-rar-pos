from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, json
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DB_PATH", os.path.join(BASE, "pos.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'staff');
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, barcode TEXT UNIQUE,
      category TEXT DEFAULT '', cost REAL NOT NULL DEFAULT 0,
      price REAL NOT NULL DEFAULT 0, stock REAL NOT NULL DEFAULT 0,
      unit TEXT DEFAULT 'ခု', active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS customers(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '',
      address TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS suppliers(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS sales(
      id INTEGER PRIMARY KEY, invoice_no TEXT UNIQUE NOT NULL,
      customer_id INTEGER, subtotal REAL NOT NULL, discount REAL NOT NULL,
      total REAL NOT NULL, paid REAL NOT NULL, debt REAL NOT NULL,
      currency TEXT NOT NULL DEFAULT 'MMK', exchange_rate REAL NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL, user_id INTEGER,
      FOREIGN KEY(customer_id) REFERENCES customers(id),
      FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS sale_items(
      id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
      qty REAL NOT NULL, price REAL NOT NULL, cost REAL NOT NULL, line_total REAL NOT NULL,
      FOREIGN KEY(sale_id) REFERENCES sales(id),
      FOREIGN KEY(product_id) REFERENCES products(id));
    CREATE TABLE IF NOT EXISTS purchases(
      id INTEGER PRIMARY KEY, supplier_id INTEGER, reference TEXT DEFAULT '',
      total REAL NOT NULL, paid REAL NOT NULL, debt REAL NOT NULL,
      currency TEXT NOT NULL DEFAULT 'MMK', exchange_rate REAL NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      FOREIGN KEY(supplier_id) REFERENCES suppliers(id));
    CREATE TABLE IF NOT EXISTS purchase_items(
      id INTEGER PRIMARY KEY, purchase_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
      qty REAL NOT NULL, cost REAL NOT NULL, line_total REAL NOT NULL,
      FOREIGN KEY(purchase_id) REFERENCES purchases(id),
      FOREIGN KEY(product_id) REFERENCES products(id));
    CREATE TABLE IF NOT EXISTS expenses(
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, amount REAL NOT NULL,
      note TEXT DEFAULT '', currency TEXT NOT NULL DEFAULT 'MMK', created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS debt_payments(
      id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL, amount REAL NOT NULL,
      note TEXT DEFAULT '', created_at TEXT NOT NULL,
      FOREIGN KEY(sale_id) REFERENCES sales(id));
    """)
    # Safe, additive migrations for databases created by the earlier starter ZIP.
    for table, column, definition in [
        ('sales','currency',"TEXT NOT NULL DEFAULT 'MMK'"),
        ('sales','exchange_rate','REAL NOT NULL DEFAULT 1'),
        ('purchases','currency',"TEXT NOT NULL DEFAULT 'MMK'"),
        ('purchases','exchange_rate','REAL NOT NULL DEFAULT 1'),
        ('expenses','currency',"TEXT NOT NULL DEFAULT 'MMK'")]:
        cols = [r['name'] for r in con.execute(f'PRAGMA table_info({table})').fetchall()]
        if column not in cols:
            con.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
    con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('krw_rate','3.2')")
    if not con.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        con.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                    ("admin", generate_password_hash("admin123"), "admin"))
    con.commit()
    con.close()

@app.template_filter("mm")
def mm(value):
    return "{:,.0f} ကျပ်".format(float(value or 0))

@app.template_filter("money")
def money(value, currency='MMK'):
    amount = float(value or 0)
    return ("₩{:,.0f}".format(amount) if currency == 'KRW' else "{:,.0f} ကျပ်".format(amount))

def krw_rate(con):
    row = con.execute("SELECT value FROM settings WHERE key='krw_rate'").fetchone()
    return float(row['value']) if row else 3.2

@app.before_request
def setup():
    init_db()

def logged_in():
    return "user_id" in session

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        con = db()
        user = con.execute("SELECT * FROM users WHERE username=?", (request.form["username"],)).fetchone()
        con.close()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.update(user_id=user["id"], username=user["username"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("အကောင့်အမည် သို့မဟုတ် စကားဝှက် မှားနေပါသည်။")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def dashboard():
    if not logged_in(): return redirect(url_for("login"))
    con = db()
    today = datetime.now().strftime("%Y-%m-%d")
    sales = con.execute("SELECT COALESCE(SUM(total),0) n FROM sales WHERE date(created_at)=?",(today,)).fetchone()["n"]
    purchases = con.execute("SELECT COALESCE(SUM(total),0) n FROM purchases WHERE date(created_at)=?",(today,)).fetchone()["n"]
    debts = con.execute("SELECT COALESCE(SUM(debt),0) n FROM sales").fetchone()["n"]
    stock = con.execute("SELECT COUNT(*) n FROM products WHERE active=1").fetchone()["n"]
    recent = con.execute("SELECT id,invoice_no,total,currency,created_at FROM sales ORDER BY id DESC LIMIT 8").fetchall()
    totals = con.execute("SELECT currency,COALESCE(SUM(total),0) total FROM sales WHERE date(created_at)=? GROUP BY currency",(today,)).fetchall()
    con.close()
    return render_template("dashboard.html", sales=sales, purchases=purchases, debts=debts, stock=stock, recent=recent, currency_totals=totals)

@app.route("/products", methods=["GET","POST"])
def products():
    if not logged_in(): return redirect(url_for("login"))
    con = db()
    if request.method == "POST":
        f=request.form
        try:
            con.execute("""INSERT INTO products(name,barcode,category,cost,price,stock,unit)
              VALUES(?,?,?,?,?,?,?)""",(f["name"],f.get("barcode") or None,f.get("category",""),
              float(f.get("cost",0)),float(f.get("price",0)),float(f.get("stock",0)),f.get("unit","ခု")))
            con.commit(); flash("ကုန်ပစ္စည်း သိမ်းဆည်းပြီးပါပြီ။")
        except sqlite3.IntegrityError:
            flash("Barcode ထပ်နေပါသည်။")
    rows=con.execute("SELECT * FROM products WHERE active=1 ORDER BY name").fetchall()
    con.close()
    return render_template("products.html", products=rows)

@app.route("/products/<int:pid>/delete", methods=["POST"])
def delete_product(pid):
    if not logged_in(): return redirect(url_for("login"))
    con=db(); con.execute("UPDATE products SET active=0 WHERE id=?",(pid,)); con.commit(); con.close()
    return redirect(url_for("products"))

@app.route("/api/products")
def api_products():
    if not logged_in(): return jsonify([])
    con=db(); rows=con.execute("SELECT id,name,barcode,price,cost,stock,unit FROM products WHERE active=1 ORDER BY name").fetchall()
    rate = krw_rate(con); con.close()
    products=[dict(r) | {"krw_price": round(float(r["price"])/rate, 2), "krw_cost": round(float(r["cost"])/rate, 2)} for r in rows]
    return jsonify({"products": products, "rate": rate})

@app.route("/sales", methods=["GET","POST"])
def sales():
    if not logged_in(): return redirect(url_for("login"))
    con=db()
    if request.method=="POST":
        try:
            items=json.loads(request.form["items"])
            if not items: raise ValueError("ပစ္စည်း မရွေးရသေးပါ။")
            currency=request.form.get("currency","MMK")
            if currency not in ("MMK","KRW"): raise ValueError("ငွေကြေး မမှန်ပါ။")
            rate=krw_rate(con) if currency == "KRW" else 1.0
            subtotal=0; prepared=[]
            for item in items:
                p=con.execute("SELECT * FROM products WHERE id=? AND active=1",(int(item["id"]),)).fetchone()
                qty=float(item["qty"])
                if not p or qty<=0: raise ValueError("ပစ္စည်း သို့မဟုတ် အရေအတွက် မမှန်ပါ။")
                if p["stock"] < qty: raise ValueError(p["name"]+" လက်ကျန် မလုံလောက်ပါ။")
                unit_price=float(p["price"])/rate
                unit_cost=float(p["cost"])/rate
                line=qty*unit_price; subtotal+=line
                prepared.append((p,qty,line,unit_price,unit_cost))
            discount=float(request.form.get("discount",0)); total=max(0,subtotal-discount)
            paid=float(request.form.get("paid",0))
            if discount<0 or paid<0: raise ValueError("ငွေပမာဏ မမှန်ပါ။")
            debt=max(0,total-paid)
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            invoice="BR"+datetime.now().strftime("%y%m%d%H%M%S%f")[-15:]
            cur=con.execute("""INSERT INTO sales(invoice_no,subtotal,discount,total,paid,debt,currency,exchange_rate,created_at,user_id)
                               VALUES(?,?,?,?,?,?,?,?,?,?)""",(invoice,subtotal,discount,total,min(paid,total),debt,currency,rate,now,session["user_id"]))
            sid=cur.lastrowid
            for p,qty,line,unit_price,unit_cost in prepared:
                con.execute("INSERT INTO sale_items(sale_id,product_id,qty,price,cost,line_total) VALUES(?,?,?,?,?,?)",
                            (sid,p["id"],qty,unit_price,unit_cost,line))
                con.execute("UPDATE products SET stock=stock-? WHERE id=?",(qty,p["id"]))
            con.commit()
            return redirect(url_for("invoice",sid=sid))
        except Exception as e:
            con.rollback(); flash(str(e))
    recent=con.execute("SELECT id,invoice_no,total,paid,debt,currency,created_at FROM sales ORDER BY id DESC LIMIT 30").fetchall()
    rate=krw_rate(con)
    con.close()
    return render_template("sales.html", recent=recent, rate=rate)

@app.route("/invoice/<int:sid>")
def invoice(sid):
    if not logged_in(): return redirect(url_for("login"))
    con=db()
    sale=con.execute("SELECT * FROM sales WHERE id=?",(sid,)).fetchone()
    items=con.execute("""SELECT si.*,p.name,p.unit FROM sale_items si JOIN products p ON p.id=si.product_id
                         WHERE si.sale_id=?""",(sid,)).fetchall()
    con.close()
    if not sale: return "ဘောင်ချာ မတွေ့ပါ။",404
    return render_template("invoice.html",sale=sale,items=items)

@app.route("/purchases", methods=["GET","POST"])
def purchases():
    if not logged_in(): return redirect(url_for("login"))
    con=db()
    if request.method=="POST":
        try:
            items=json.loads(request.form["items"])
            if not items: raise ValueError("ဝယ်ယူမည့်ပစ္စည်း မရွေးရသေးပါ။")
            currency=request.form.get("currency","MMK")
            if currency not in ("MMK","KRW"): raise ValueError("ငွေကြေး မမှန်ပါ။")
            rate=krw_rate(con) if currency == "KRW" else 1.0
            total=0; prepared=[]
            for it in items:
                p=con.execute("SELECT * FROM products WHERE id=?",(int(it["id"]),)).fetchone()
                qty=float(it["qty"]); cost=float(it["cost"])
                if not p or qty<=0 or cost<0: raise ValueError("အချက်အလက် မမှန်ပါ။")
                line=qty*cost; total+=line; prepared.append((p,qty,cost,line))
            paid=float(request.form.get("paid",0)); debt=max(0,total-paid)
            cur=con.execute("INSERT INTO purchases(total,paid,debt,currency,exchange_rate,created_at) VALUES(?,?,?,?,?,?)",
                (total,min(paid,total),debt,currency,rate,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            pid=cur.lastrowid
            for p,q,c,l in prepared:
                con.execute("INSERT INTO purchase_items(purchase_id,product_id,qty,cost,line_total) VALUES(?,?,?,?,?)",(pid,p["id"],q,c,l))
                con.execute("UPDATE products SET stock=stock+?,cost=? WHERE id=?",(q,c*rate,p["id"]))
            con.commit(); flash("အဝယ်စာရင်း သိမ်းဆည်းပြီးပါပြီ။")
        except Exception as e:
            con.rollback(); flash(str(e))
    rows=con.execute("SELECT * FROM purchases ORDER BY id DESC LIMIT 30").fetchall()
    con.close()
    return render_template("purchases.html", purchases=rows)

@app.route("/debts", methods=["GET","POST"])
def debts():
    if not logged_in(): return redirect(url_for("login"))
    con=db()
    if request.method=="POST":
        sid=int(request.form["sale_id"]); amount=float(request.form["amount"])
        sale=con.execute("SELECT * FROM sales WHERE id=?",(sid,)).fetchone()
        if sale and amount>0 and amount<=sale["debt"]:
            con.execute("INSERT INTO debt_payments(sale_id,amount,note,created_at) VALUES(?,?,?,?)",
                (sid,amount,request.form.get("note",""),datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            con.execute("UPDATE sales SET paid=paid+?,debt=debt-? WHERE id=?",(amount,amount,sid)); con.commit()
            flash("အကြွေးဆပ်ငွေ မှတ်တမ်းတင်ပြီးပါပြီ။")
        else: flash("အကြွေးစာရင်း သို့မဟုတ် ပမာဏ မမှန်ပါ။")
    rows=con.execute("SELECT id,invoice_no,total,paid,debt,currency,created_at FROM sales WHERE debt>0 ORDER BY id DESC").fetchall()
    con.close()
    return render_template("debts.html", debts=rows)

@app.route("/expenses", methods=["GET","POST"])
def expenses():
    if not logged_in(): return redirect(url_for("login"))
    con=db()
    if request.method=="POST":
        currency=request.form.get("currency","MMK")
        if currency not in ("MMK","KRW"): currency="MMK"
        con.execute("INSERT INTO expenses(title,amount,note,currency,created_at) VALUES(?,?,?,?,?)",
          (request.form["title"],float(request.form["amount"]),request.form.get("note",""),currency,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.commit(); flash("အသုံးစရိတ် သိမ်းဆည်းပြီးပါပြီ။")
    rows=con.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 100").fetchall()
    con.close()
    return render_template("expenses.html", expenses=rows)


@app.route("/settings", methods=["GET","POST"])
def settings():
    if not logged_in(): return redirect(url_for("login"))
    if session.get("role") != "admin":
        flash("ဤစာမျက်နှာကို Admin သာ ပြင်ဆင်နိုင်ပါသည်။"); return redirect(url_for("dashboard"))
    con=db()
    if request.method == "POST":
        rate=float(request.form.get("krw_rate",0))
        if rate <= 0:
            flash("ငွေလဲနှုန်းသည် သုညထက်ကြီးရပါမည်။")
        else:
            con.execute("INSERT INTO settings(key,value) VALUES('krw_rate',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(rate),))
            con.commit(); flash("ငွေလဲနှုန်း သိမ်းဆည်းပြီးပါပြီ။")
    rate=krw_rate(con); con.close()
    return render_template("settings.html", rate=rate)

@app.route("/reports")
def reports():
    if not logged_in(): return redirect(url_for("login"))
    con=db()
    daily=con.execute("""SELECT date(s.created_at) day, s.currency, SUM(s.total) sales,
      SUM((si.price-si.cost)*si.qty) gross FROM sales s JOIN sale_items si ON si.sale_id=s.id
      GROUP BY date(s.created_at),s.currency ORDER BY day DESC LIMIT 62""").fetchall()
    exp=con.execute("SELECT currency,COALESCE(SUM(amount),0) amount FROM expenses GROUP BY currency").fetchall()
    con.close()
    return render_template("reports.html", daily=daily, expenses=exp)

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
