from flask import Flask, render_template, request, redirect, url_for, jsonify
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
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_data (
        id INTEGER PRIMARY KEY, date TEXT UNIQUE, payload TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS log_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT, action TEXT, responsible TEXT,
        status TEXT, progress INTEGER DEFAULT 0, created_at TEXT)""")
    conn.commit(); conn.close()

DEFAULTS = {
    "date": str(datetime.date.today()), "updated_by": "", "time_updated": "09:00",
    # Запасы
    "stock_total": "", "stock_donetsk": "", "stock_makeevka": "", "stock_south": "",
    "supply_day": "", "supply_plan": "2000",
    "supply_npz_saratov": "", "supply_rostov": "", "supply_volgograd": "",
    "fuel_in_transit_trucks": "", "fuel_in_transit_count": "",
    "fuel_waiting_name": "п. Новоазовск", "fuel_waiting_tons": "", "fuel_waiting_wagons": "",
    "consumption_day": "", "consumption_norm": "980", "consumption_yesterday": "",
    # Соц службы
    "soc_ambulance_norm": "10", "soc_ambulance_fact": "",
    "soc_fire_norm": "8", "soc_fire_fact": "",
    "soc_police_norm": "15", "soc_police_fact": "",
    "soc_communal_norm": "70", "soc_communal_fact": "",
    "soc_transport_norm": "40", "soc_transport_fact": "",
    "soc_food_norm": "25", "soc_food_fact": "",
    "soc_hospital_norm": "12", "soc_hospital_fact": "",
    "soc_generator_norm_3days": "120", "soc_generator_stock": "",
    # Маршруты
    "route1_name": "Новоазовск → Мариуполь", "route1_vol": "", "route1_uav": "", "route1_risk": "0",
    "route2_name": "Успенка → Донецк", "route2_vol": "", "route2_uav": "", "route2_risk": "1",
    "route3_name": "Харцызск → Макеевка", "route3_vol": "", "route3_uav": "", "route3_risk": "0",
    "route4_name": "Таганрог → Харцызск", "route4_vol": "", "route4_uav": "", "route4_risk": "2",
    "route5_name": "Волноваха → Дебальцево", "route5_vol": "", "route5_uav": "", "route5_risk": "1",
    # АЗС
    "azs_total": "519", "azs_ok": "", "azs_limit": "", "azs_empty": "",
    "azs_queues": "1", "azs_queues_places": "",
    "azs_load_avg": "",
    # Парк бензовозов
    "trucks_working": "", "trucks_involved": "", "trucks_repair": "", "trucks_no_driver": "",
    # Инфраструктура
    "rail_level": "1", "infra_capacity": "5600",
    # Цены АЗС по сетям
    "price_rtk_92": "", "price_rtk_95": "", "price_rtk_dt": "",
    "price_mostek_92": "", "price_mostek_95": "", "price_mostek_dt": "",
    "price_monblan_92": "", "price_monblan_95": "", "price_monblan_dt": "",
    "price_indep_92": "", "price_indep_95": "", "price_indep_dt": "",
    # Агрегированные цены
    "price_92_avg": "", "price_92_min": "", "price_92_max": "",
    "price_95_avg": "", "price_95_min": "", "price_95_max": "",
    "price_dt_avg": "", "price_dt_min": "", "price_dt_max": "",
    "price_wholesale_92": "", "price_wholesale_95": "", "price_wholesale_dt": "",
    "price_shadow_92": "", "price_shadow_95": "",
    "price_national_92": "", "price_national_95": "", "price_national_dt": "",
    "reserve_stock_cost": "",
    # Регионы сравнения
    "price_reg_rostov_92": "", "price_reg_rostov_95": "", "price_reg_rostov_dt": "",
    "price_reg_zapo_92": "", "price_reg_zapo_95": "", "price_reg_zapo_dt": "",
    "price_reg_lnr_92": "", "price_reg_lnr_95": "", "price_reg_lnr_dt": "",
    # Распределение по секторам
    "dist_azs_plan": "600", "dist_azs_fact": "",
    "dist_industry_plan": "250", "dist_industry_fact": "",
    "dist_agro_plan": "130", "dist_agro_fact": "",
    "dist_communal_plan": "80", "dist_communal_fact": "",
    "dist_reserve_plan": "60", "dist_reserve_fact": "",
    # Вымывание
    "washout_fact": "", "washout_norm": "",
    # Соцмониторинг
    "social_queues_msg": "", "social_queues_delta": "",
    "social_noai95_msg": "", "social_noai95_delta": "",
    "social_prices_msg": "", "social_prices_delta": "",
    "social_supply_msg": "", "social_supply_delta": "",
    # Риски
    "risk_deficit_days": "", "risk_critical_consumers": "",
    "risk_consumption_deviation": "", "risk_dry_zones": "",
    "risk_emergency": "",
    # Аварийные ситуации
    "emergency_desc": "",
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

def load_log():
    conn = get_db()
    rows = conn.execute("SELECT * FROM log_entries ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def load_history_chart(days=7):
    conn = get_db()
    rows = conn.execute("SELECT date, payload FROM daily_data ORDER BY date DESC LIMIT ?", (days,)).fetchall()
    conn.close()
    result = []
    for row in reversed(rows):
        d = json.loads(row["payload"])
        result.append({
            "date": row["date"],
            "consumption": d.get("consumption_day", ""),
            "norm": d.get("consumption_norm", "980"),
            "supply": d.get("supply_day", ""),
            "stock": d.get("stock_total", ""),
        })
    return result

def safe_pct(fact, norm):
    try: f,n=float(fact),float(norm); return round(f/n*100) if n else None
    except: return None

def safe_div(a, b):
    try: return round(float(a)/float(b),1) if float(b) else None
    except: return None

def safe_float(v):
    try: return float(v)
    except: return None

def enrich(d):
    d["autonomy"] = safe_div(d["stock_total"], d["consumption_day"])
    # Spreads
    for fuel in ["92","95","dt"]:
        avg = safe_float(d.get(f"price_{fuel}_avg") or d.get(f"price_92_avg"))
        ws  = safe_float(d.get(f"price_wholesale_{fuel}"))
        if fuel == "92": avg = safe_float(d.get("price_92_avg"))
        if fuel == "95": avg = safe_float(d.get("price_95_avg"))
        if fuel == "dt": avg = safe_float(d.get("price_dt_avg"))
        ws = safe_float(d.get(f"price_wholesale_{fuel}"))
        d[f"spread_{fuel}"] = round(avg - ws, 2) if avg is not None and ws is not None else None
    # Supply pct
    d["supply_pct"] = safe_pct(d["supply_day"], d["supply_plan"])
    # Consumption delta
    try: d["consumption_delta"] = round(float(d["consumption_day"]) - float(d["consumption_yesterday"]))
    except: d["consumption_delta"] = None
    # Soc items
    soc_defs = [
        ("ambulance","Скорая помощь"),("fire","Пожарная охрана"),
        ("police","Полиция"),("communal","Коммунальные службы\n(водоснабжение, тепло)"),
        ("transport","Транспорт (автобусы,\nшкольные маршруты)"),
        ("food","Продовольственная логистика"),("hospital","Больницы и поликлиники"),
    ]
    d["soc_items"] = []
    for k,l in soc_defs:
        fact = d.get(f"soc_{k}_fact","")
        norm = d.get(f"soc_{k}_norm",1)
        pct  = safe_pct(fact, norm)
        d["soc_items"].append({"key":k,"label":l,"fact":fact,"norm":norm,"pct":pct})
    d["soc_gen_pct"] = safe_pct(d["soc_generator_stock"], d["soc_generator_norm_3days"])
    # Routes
    rl = {"0":"Низкий","1":"Средний","2":"Высокий"}
    rec = {"0":"Оставить","1":"Оставить","2":"Сменить"}
    rc = {"0":"grn","1":"amb","2":"red"}
    d["routes"] = []
    for i in range(1,6):
        name = d.get(f"route{i}_name","")
        if not name: continue
        risk = str(d.get(f"route{i}_risk","0"))
        d["routes"].append({
            "name": name,
            "vol": d.get(f"route{i}_vol","—"),
            "uav": d.get(f"route{i}_uav","0"),
            "risk": rl.get(risk,""),
            "rec": rec.get(risk,""),
            "rc": rc.get(risk,"grn"),
        })
    # AZS
    try:
        ok = int(d.get("azs_ok") or 0)
        total = int(d.get("azs_total") or 519)
        d["azs_ok_pct"] = round(ok/total*100) if total else None
    except: d["azs_ok_pct"] = None
    # Trucks
    try: d["trucks_total"] = int(d.get("trucks_working") or 0)+int(d.get("trucks_involved") or 0)+int(d.get("trucks_repair") or 0)+int(d.get("trucks_no_driver") or 0)
    except: d["trucks_total"] = "—"
    # Rail
    rl2 = {"0":"Не задействовано","1":"Частично (75%)","2":"Полностью"}
    d["rail_label"] = rl2.get(str(d.get("rail_level","1")),"")
    # Sector dist
    sectors = [("azs","АЗС (коммерческие)"),("industry","Промышленность"),
               ("agro","Сельское хозяйство"),("communal","Коммунальные службы"),("reserve","Резерв")]
    d["sectors"] = []
    for k,l in sectors:
        plan = d.get(f"dist_{k}_plan","")
        fact = d.get(f"dist_{k}_fact","")
        pct  = safe_pct(fact, plan)
        d["sectors"].append({"label":l,"plan":plan,"fact":fact,"pct":pct})
    # Chart data
    d["chart_data"] = json.dumps(load_history_chart(7))
    return d

@app.route("/")
def dashboard():
    d = enrich(load_data())
    d["log"] = load_log()
    return render_template("dashboard.html", d=d)

@app.route("/input", methods=["GET","POST"])
def input_form():
    d = load_data()
    if request.method == "POST":
        for key in DEFAULTS:
            if request.form.get(key) is not None:
                d[key] = request.form.get(key)
        save_data(d)
        return redirect(url_for("dashboard"))
    return render_template("input.html", d=d)

@app.route("/log/add", methods=["POST"])
def add_log():
    conn = get_db()
    conn.execute("INSERT INTO log_entries(entry_date,action,responsible,status,progress,created_at) VALUES(?,?,?,?,?,?)",
                 (request.form.get("log_date", str(datetime.date.today())),
                  request.form.get("log_action","").strip(),
                  request.form.get("log_responsible",""),
                  request.form.get("log_status","В работе"),
                  int(request.form.get("log_progress",0)),
                  str(datetime.datetime.now())))
    conn.commit(); conn.close()
    return redirect(url_for("dashboard")+"#log")

@app.route("/log/update", methods=["POST"])
def update_log():
    conn = get_db()
    conn.execute("UPDATE log_entries SET status=?, progress=? WHERE id=?",
                 (request.form.get("status"), request.form.get("progress",0), request.form.get("id")))
    conn.commit(); conn.close()
    return redirect(url_for("dashboard")+"#log")

@app.route("/history")
def history():
    conn = get_db()
    rows = conn.execute("SELECT date FROM daily_data ORDER BY date DESC").fetchall()
    conn.close()
    return render_template("history.html", dates=[r["date"] for r in rows])

@app.route("/history/<date>")
def history_date(date):
    d = enrich(load_data(date)); d["log"] = load_log()
    return render_template("dashboard.html", d=d, archive_date=date)

init_db()
if __name__ == "__main__":
    import socket
    try: ip = socket.gethostbyname(socket.gethostname())
    except: ip = "?"
    print(f"\n  Дашборд: http://localhost:5000\n  По сети: http://{ip}:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
