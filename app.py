from flask import Flask, request, session, redirect, url_for, render_template_string, jsonify
import sqlite3, hashlib, os, sys, getpass, threading, time
import vps as vpsmod

DB = "panel.db"
app = Flask(__name__)
app.secret_key = os.urandom(32)

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT,
      email TEXT, is_admin INTEGER DEFAULT 0, signup_ip TEXT);
    CREATE TABLE IF NOT EXISTS vps(
      id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE,
      container_id TEXT, ssh TEXT, status TEXT DEFAULT 'creating',
      created_ip TEXT, created_at INTEGER);
    """); c.commit(); c.close()

def h(p): return hashlib.sha256(p.encode()).hexdigest()

def first_run_admin():
    c = db()
    if not c.execute("SELECT 1 FROM users WHERE is_admin=1").fetchone():
        print("\n=== First-run: create admin account ===")
        u = input("Admin username: ").strip()
        e = input("Admin email: ").strip()
        p = getpass.getpass("Admin password: ")
        c.execute("INSERT INTO users(username,password,email,is_admin,signup_ip) VALUES(?,?,?,1,?)",
                  (u, h(p), e, "127.0.0.1"))
        c.commit()
        print(f"Admin '{u}' created.\n")
    c.close()

def client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()

def current_user():
    if "uid" not in session: return None
    c = db(); u = c.execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone(); c.close()
    return u

# ---------- templates ----------
BASE = """
<!doctype html><html><head><title>{{title}}</title>
<style>
body{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:0}
.wrap{max-width:720px;margin:40px auto;padding:24px;background:#1a1a1a;border:1px solid #333;border-radius:8px}
h1,h2{margin-top:0}
input,button{padding:9px 12px;border-radius:5px;border:1px solid #444;background:#222;color:#eee;font-size:14px;margin:4px 0}
button{background:#2d6cdf;border:0;cursor:pointer}
button:hover{opacity:.9}
button.danger{background:#c0392b}
a{color:#6ab0ff;text-decoration:none}
.stat{display:inline-block;padding:8px 14px;background:#222;border-radius:5px;margin:4px 6px 4px 0}
pre{background:#0a0a0a;padding:12px;border-radius:6px;max-height:340px;overflow:auto;font-size:13px}
.msg{padding:8px;background:#402;border-left:3px solid #c33;margin:8px 0}
nav{background:#000;padding:10px 24px}
nav a{margin-right:16px}
table{width:100%;border-collapse:collapse}
td,th{padding:8px;border-bottom:1px solid #333;text-align:left}
</style></head><body>
<nav>
  {% if user %}<a href="/">Home</a>
    {% if user['is_admin'] %}<a href="/admin">Admin</a>{% endif %}
    <a href="/logout">Logout ({{user['username']}})</a>
  {% else %}<a href="/login">Login</a> <a href="/signup">Sign up</a>{% endif %}
</nav>
<div class="wrap">{{ body|safe }}</div></body></html>
"""

def render(title, body, **kw):
    return render_template_string(BASE, title=title, body=render_template_string(body, **kw), user=current_user())

# ---------- auth ----------
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        u = request.form["username"].strip()
        p = request.form["password"]
        e = request.form["email"].strip()
        if not u or not p:
            return render("Signup", "<p class=msg>Missing fields.</p><a href=/signup>back</a>")
        c = db()
        try:
            c.execute("INSERT INTO users(username,password,email,signup_ip) VALUES(?,?,?,?)",
                      (u, h(p), e, client_ip()))
            c.commit()
        except sqlite3.
