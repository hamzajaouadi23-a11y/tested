"""Base persistante SQLite — toutes les données du pipeline survivent aux redémarrages."""
import json
import os
import sqlite3
import threading
import time

from . import config

_lock = threading.Lock()


def connect():
    con = sqlite3.connect(config.DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT,
  publisher TEXT,
  retrieved_at TEXT NOT NULL,
  UNIQUE(url, retrieved_at)
);
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER,
  source_id INTEGER,
  topic TEXT,
  fact TEXT NOT NULL,
  analysis TEXT,
  angle TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE TABLE IF NOT EXISTS research_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT,
  niche TEXT,
  status TEXT NOT NULL,
  queries_json TEXT,
  notes TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER,
  title TEXT NOT NULL,
  niche TEXT,
  problem TEXT,
  solution TEXT,
  product_name TEXT,
  product_url TEXT,
  price TEXT,
  scores_json TEXT,
  priority_score REAL,
  risk TEXT,
  status TEXT NOT NULL DEFAULT 'proposed',  -- proposed | selected | rejected | used
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scripts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id INTEGER,
  style TEXT NOT NULL,              -- A..E
  hook TEXT,
  script_text TEXT,
  vo_text TEXT,
  onscreen_json TEXT,
  shotlist_json TEXT,
  caption TEXT,
  cta TEXT,
  hashtags TEXT,
  claims_json TEXT,                 -- [{claim, source_url}] — toute affirmation factuelle sourcée
  ai_disclosure INTEGER DEFAULT 0,
  provider TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(candidate_id) REFERENCES candidates(id)
);
CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id INTEGER,
  path TEXT NOT NULL,
  kind TEXT NOT NULL,               -- image | video | audio | overlay
  provenance TEXT NOT NULL,         -- user | licensed | original | ai | composition | demo | mock
  license TEXT,
  realness TEXT NOT NULL,           -- real | ai | composition | demo | mock
  note TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(script_id) REFERENCES scripts(id)
);
CREATE TABLE IF NOT EXISTS voices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id INTEGER,
  path TEXT NOT NULL,
  provider TEXT,
  lang TEXT,
  duration_s REAL,
  chars INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY(script_id) REFERENCES scripts(id)
);
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id INTEGER,
  path TEXT NOT NULL,
  filename TEXT,
  duration_s REAL,
  width INTEGER,
  height INTEGER,
  fps REAL,
  size_bytes INTEGER,
  status TEXT NOT NULL DEFAULT 'rendered',  -- rendered | qa_passed | qa_failed | approved | scheduled | published
  qa_json TEXT,
  disclosure_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(script_id) REFERENCES scripts(id)
);
CREATE TABLE IF NOT EXISTS pipeline_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_type TEXT NOT NULL,           -- candidate | script | video
  ref_id INTEGER NOT NULL,
  state TEXT NOT NULL,              -- RESEARCH|SELECT|SCRIPT|ASSETS|VOICE|RENDER|QA|WAITING_APPROVAL|APPROVED|SCHEDULED|PUBLISHED|BLOCKED
  reason TEXT,
  history_json TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(ref_type, ref_id)
);
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  decision TEXT NOT NULL,           -- approved | rejected
  note TEXT,
  decided_at TEXT NOT NULL,
  FOREIGN KEY(video_id) REFERENCES videos(id)
);
CREATE TABLE IF NOT EXISTS schedule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  platform TEXT NOT NULL,
  planned_at TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'planned',  -- planned | due_reminder | done | cancelled
  created_at TEXT NOT NULL,
  FOREIGN KEY(video_id) REFERENCES videos(id)
);
CREATE TABLE IF NOT EXISTS analytics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER,
  platform TEXT,
  views INTEGER, likes INTEGER, comments INTEGER, shares INTEGER, clicks INTEGER, sales INTEGER,
  captured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learning (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL,
  data_json TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings_kv (
  key TEXT PRIMARY KEY,
  value TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT,
  payload_json TEXT,
  created_at TEXT NOT NULL
);
"""


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def init():
    with _lock, connect() as con:
        con.executescript(SCHEMA)


def q(sql, params=(), one=False):
    with _lock, connect() as con:
        cur = con.execute(sql, params)
        rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def run(sql, params=()):
    with _lock, connect() as con:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid


def getjson(row, key, default=None):
    try:
        return json.loads(row[key]) if row and row[key] else default
    except Exception:
        return default


def log_event(kind, payload):
    run("INSERT INTO events(kind,payload_json,created_at) VALUES(?,?,?)",
        (kind, json.dumps(payload, ensure_ascii=False), now()))


init()
