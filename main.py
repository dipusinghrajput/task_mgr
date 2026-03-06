from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

# -------------------------
# DATABASE SETUP
# -------------------------

def init_db():

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        duration REAL,
        deadline TEXT,
        preferred_time TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------
# DAILY ROUTINE
# -------------------------

FIXED_HOURS_PER_DAY = 14


# -------------------------
# FREE TIME CALCULATION
# -------------------------

def free_time(deadline):

    deadline = datetime.strptime(deadline,"%Y-%m-%d %H:%M")

    hours = (deadline - datetime.now()).total_seconds()/3600

    if hours <= 0:
        return 0

    days = hours/24

    free = hours - days*FIXED_HOURS_PER_DAY

    if free < 0:
        free = 0

    return free


# -------------------------
# URGENCY SCORE
# -------------------------

def urgency(task):

    free = free_time(task["deadline"])

    if free == 0:
        return 999

    return task["duration"]/free


# -------------------------
# RISK DETECTION
# -------------------------

def risk(task):

    free = free_time(task["deadline"])

    if task["duration"] > free:
        return "high risk"

    if task["duration"] > free*0.7:
        return "warning"

    return "safe"


# -------------------------
# HOME PAGE
# -------------------------

@app.route("/")
def home():

    return render_template("index.html")


# -------------------------
# ADD TASK
# -------------------------

@app.route("/add-task",methods=["POST"])
def add_task():

    data = request.json

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO tasks(title,duration,deadline,preferred_time)
    VALUES(?,?,?,?)
    """,(data["title"],data["duration"],data["deadline"],data["preferred_time"]))

    conn.commit()
    conn.close()

    return jsonify({"status":"task added"})


# -------------------------
# GET TASKS
# -------------------------

@app.route("/tasks")
def tasks():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    rows = c.execute("SELECT * FROM tasks").fetchall()

    conn.close()

    result=[]

    for r in rows:

        task=dict(r)

        task["free_time"]=round(free_time(task["deadline"]),2)
        task["risk"]=risk(task)

        result.append(task)

    return jsonify(result)


# -------------------------
# PRIORITY LIST
# -------------------------

@app.route("/priorities")
def priorities():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    rows = c.execute("SELECT * FROM tasks").fetchall()

    conn.close()

    tasks=[dict(r) for r in rows]

    tasks.sort(key=lambda x: urgency(x), reverse=True)

    result=[]

    for t in tasks:

        result.append({
            "title":t["title"],
            "urgency":round(urgency(t),3),
            "risk":risk(t)
        })

    return jsonify(result)


# -------------------------
# TODAY PLAN
# -------------------------

@app.route("/today-plan")
def today_plan():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    rows = c.execute("SELECT * FROM tasks").fetchall()

    conn.close()

    tasks=[dict(r) for r in rows]

    tasks.sort(key=lambda x: urgency(x), reverse=True)

    free_today = 24 - FIXED_HOURS_PER_DAY

    used = 0

    plan=[]

    for t in tasks:

        if used >= free_today:
            break

        remaining = free_today - used

        work = min(t["duration"],remaining)

        plan.append({
            "task":t["title"],
            "work_today":round(work,2),
            "remaining":round(t["duration"]-work,2)
        })

        used += work

    return jsonify({
        "today_free_hours":round(free_today,2),
        "plan":plan
    })


if __name__ == "__main__":
    app.run(debug=True)
