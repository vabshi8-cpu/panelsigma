# panel.py
import os, sqlite3, time, threading, secrets, hashlib, json, subprocess, re
from flask import Flask, request, session, redirect, jsonify, render_template_string, url_for
import docker

DB = "panel.db"
IMG = "ubuntu:22.04"
LIMITS = {"mem": "32g", "cpus": 4.0, "disk": "80g"}
CPU_KILL = 80.0

app = Flask(__name__)
app.secret_key = secrets.token_hex(24)
dcli = docker.from_env()

# ---------- db ----------
def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db(); q = c.cursor()
    q.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT,
        email TEXT, is_admin INTEGER DEFAULT 0, reg_ip TEXT, fp TEXT);
    CREATE TABLE IF NOT EXISTS vps(
        id INTEGER PRIMARY KEY, owner INTEGER UNIQUE, container TEXT,
        ssh TEXT, created REAL, suspended INTEGER DEFAULT 0, reason TEXT);
    CREATE TABLE IF NOT EXISTS sessions(
        sid TEXT PRIMARY KEY, uid INTEGER, ip TEXT, fp TEXT, ts REAL);
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, vps_id INTEGER, line TEXT, ts REAL);
    """)
    c.commit(); c.close()

def hpw(p): return hashlib.sha256(p.encode()).hexdigest()

# ---------- setup wizard ----------
def wizard():
    print("\n=== First-run setup ===")
    while True:
        u = input("Admin username: ").strip()
        p = input("Admin password: ").strip()
        e = input("Admin email: ").strip()
        if u and p and e: break
        print("all fields required")
    c = db()
    c.execute("INSERT INTO users(username,password,email,is_admin,reg_ip,fp) VALUES(?,?,?,1,'setup','setup')",
              (u, hpw(p), e))
    c.comm
