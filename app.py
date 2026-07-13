from flask import Flask, render_template, request, redirect, url_for
import json, os, sqlite3, datetime

app = Flask(__name__)
app.jinja_env.globals['enumerate'] = enumerate

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuel.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS daily_data (id INTEGER PRIMARY KEY, date TEXT UNIQUE, payload TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS log_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_date TEXT, action TEXT, responsible TEXT, status TEXT, created_at TEXT)")
    conn.commit(); conn.close()

DEFAULTS = {
    "date": str(datetime.date.today()), "updated_by": "",
    "stock_total": "", "stock_central": "", "stock_east": "", "stock_south": "",
    "supply_day": "", "supply_npz": "", "supply_rail": "", "supply_truck": "",
    "fuel_in_transit": "", "transit_eta": "", "consumption_day": "", "consumption_norm": "280",
    "trucks_active": "", "trucks_repair": "",
    "route1_name": "Новоазовск — Мариуполь", "route1_vol": "", "route1_risk": "0",
    "route2_name": "Успенка — Донецк", "route2_vol": "", "route2_risk": "0",
    "rail_level": "1", "azs_ok": "", "azs_limit": "", "azs_empty": "", "queues": "0", "dry_zone": "",
    "soc_ambulance_fact": "", "soc_ambulance_norm": "5",
    "soc_fire_fact": "", "soc_fire_norm": "8",
    "soc_police_fact": "", "soc_police_norm": "10",
    "soc_school_fact": "", "soc_school_norm": "7",
    "soc_hospital_fact": "", "soc_hospital_norm": "6",
    "soc_generator_fact": "", "soc_generator_norm": "4",
    "soc_water_fact": "", "soc_water_norm": "9",
    "soc_heat_fact": "", "soc_heat_norm": "3",
    "soc_food_fact": "", "soc_food_norm": "12",
    "price_92": "100", "price_92_min": "", "price_92_max": "",
    "price_95": "120", "price_dt": "", "price_wholesale": "", "price_shadow": "", "price_national": "",
    "social_mentions": "", "social_queues_cnt": "", "social_empty_cnt": "",
    "social_prices_cnt": "", "social_resellers": "0", "social_note": "",
}

def load_data(date=None):
    if not date: date = str(datetime.date.today())
    conn = get_db()
    row = conn.execute("SELECT payload FROM daily_data WHERE date=?", (date,)).fetchone()
    conn.close()
    d = dict(DEFAULTS)
    if row: d.update(json.loads(row["payload"]))
    return d

def save_data(d):
    date = d.get("date", str(datetime.date.today()))
    conn = get_db()
    conn.execute("INSERT INTO daily_data(date,payload) VALUES(?,?) ON CONFLICT(date) DO UPDATE SET payload=excluded.payload",
                 (date, json.dumps(d, ensure_ascii=False)))
    conn.commit(); conn.close()

def safe_pct(fact, norm):
    try: f,n=float(fact),float(norm); return round(f/n*100) if n else None
    except: return None

def safe_div(a, b):
    try: return round(float(a)/float(b),1) if float(b) else None
    except: return None

def enrich(d):
    d["autonomy"] = safe_div(d["stock_total"], d["consumption_day"])
    try: d["spread"] = round(float(d["price_92"])-float(d["price_wholesale"]),2)
    except: d["spread"] = None
    soc_defs = [("ambulance","Скорая помощь"),("fire","Пожарная охрана"),("police","Полиция / МВД"),
                ("school","Школьные маршруты"),("hospital","Больницы"),("generator","Рез. генераторы"),
                ("water","Водоснабжение"),("heat","Теплоснабжение"),("food","Прод. логистика")]
    d["soc_items"] = [{"key":k,"label":l,"fact":d.get(f"soc_{k}_fact",""),"norm":d.get(f"soc_{k}_norm",1),
                        "pct":safe_pct(d.get(f"soc_{k}_fact",""),d.get(f"soc_{k}_norm",1))} for k,l in soc_defs]
    rl={"0":"Безопасен","1":"Повышенный риск","2":"Опасен"}
    rll={"0":"Не задействовано","1":"Частичная","2":"Полная"}
    d["route1_risk_label"]=rl.get(str(d.get("route1_risk","0")),"")
    d["route2_risk_label"]=rl.get(str(d.get("route2_risk","0")),"")
    d["rail_label"]=rll.get(str(d.get("rail_level","1")),"")
    try: d["trucks_total_calc"]=int(d.get("trucks_active") or 0)+int(d.get("trucks_repair") or 0)
    except: d["trucks_total_calc"]="—"
    return d

def load_log():
    conn=get_db()
    rows=conn.execute("SELECT * FROM log_entries ORDER BY id DESC LIMIT 20").fetchall()
    conn.close(); return [dict(r) for r in rows]

@app.route("/")
def dashboard():
    d=enrich(load_data()); d["log"]=load_log()
    return render_template("dashboard.html", d=d)

@app.route("/input", methods=["GET","POST"])
def input_form():
    d=load_data()
    if request.method=="POST":
        for key in DEFAULTS:
            if request.form.get(key) is not None: d[key]=request.form.get(key)
        save_data(d); return redirect(url_for("dashboard"))
    return render_template("input.html", d=d)

@app.route("/log/add", methods=["POST"])
def add_log():
    conn=get_db()
    conn.execute("INSERT INTO log_entries(entry_date,action,responsible,status,created_at) VALUES(?,?,?,?,?)",
                 (request.form.get("log_date",str(datetime.date.today())),
                  request.form.get("log_action","").strip(),
                  request.form.get("log_responsible",""),
                  request.form.get("log_status","В работе"),
                  str(datetime.datetime.now())))
    conn.commit(); conn.close()
    return redirect(url_for("dashboard")+"#log")

@app.route("/log/status", methods=["POST"])
def update_log_status():
    conn=get_db()
    conn.execute("UPDATE log_entries SET status=? WHERE id=?",(request.form.get("status"),request.form.get("id")))
    conn.commit(); conn.close()
    return redirect(url_for("dashboard")+"#log")

@app.route("/history")
def history():
    conn=get_db()
    rows=conn.execute("SELECT date FROM daily_data ORDER BY date DESC").fetchall()
    conn.close()
    return render_template("history.html", dates=[r["date"] for r in rows])

@app.route("/history/<date>")
def history_date(date):
    d=enrich(load_data(date)); d["log"]=load_log()
    return render_template("dashboard.html", d=d, archive_date=date)

init_db()

if __name__=="__main__":
    import socket
    try: ip=socket.gethostbyname(socket.gethostname())
    except: ip="?"
    print(f"\nДашборд: http://localhost:5000  |  По сети: http://{ip}:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
