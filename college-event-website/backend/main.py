"""Campusly College Event API — FastAPI + SQLite starter."""
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).with_name("campusly.db")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Technical',
            event_date TEXT NOT NULL, event_time TEXT NOT NULL DEFAULT 'Time to be announced',
            venue TEXT NOT NULL, capacity INTEGER NOT NULL DEFAULT 30,
            description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL,
            student_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, student_id), FOREIGN KEY(event_id) REFERENCES events(id)
        )""")
        count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count == 0:
            seeds = [
                ("CodeSprint 2026", "Technical", "2026-10-22", "9:30 AM – 4:00 PM", "Innovation Lab · Block B", 40, "A fast-paced coding challenge for curious builders."),
                ("Campus Open Mic", "Cultural", "2026-10-24", "5:00 PM – 7:30 PM", "Amphitheatre", 50, "Music, poetry, comedy, and the courage to take the mic."),
                ("Design for Good", "Workshop", "2026-10-27", "10:00 AM – 1:00 PM", "Design Studio · Floor 2", 25, "Collaborate on design ideas that help your community."),
                ("Inter-College Sports Meet", "Sports", "2026-10-30", "8:00 AM – 5:00 PM", "University Sports Ground", 80, "Bring your team spirit and meet athletes across campuses."),
            ]
            db.executemany("INSERT INTO events(title,category,event_date,event_time,venue,capacity,description) VALUES(?,?,?,?,?,?,?)", seeds)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Campusly College Event API", version="1.0.0", description="API for campus events, student registrations, and an illustrative performance estimate.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class EventCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    category: str = Field(default="Technical", max_length=40)
    event_date: date
    event_time: str = Field(default="Time to be announced", max_length=60)
    venue: str = Field(min_length=2, max_length=120)
    capacity: int = Field(default=30, ge=1, le=10000)
    description: str = Field(default="", max_length=1000)

class RegistrationCreate(BaseModel):
    student_id: str = Field(min_length=2, max_length=80)

class PredictionInput(BaseModel):
    attendance: float = Field(ge=0, le=100)
    previous_marks: float = Field(ge=0, le=100)
    study_hours: float = Field(ge=0, le=24)
    assignments_completed: float = Field(ge=0, le=100)


def event_dict(row, student_id: Optional[str] = None):
    item = dict(row)
    item["registered"] = False
    item["registrations"] = 0
    item["spots_left"] = item["capacity"]
    item["date"] = item["event_date"]
    if student_id:
        with connect() as db:
            item["registered"] = bool(db.execute("SELECT 1 FROM registrations WHERE event_id=? AND student_id=?", (item["id"], student_id)).fetchone())
    with connect() as db:
        item["registrations"] = db.execute("SELECT COUNT(*) FROM registrations WHERE event_id=?", (item["id"],)).fetchone()[0]
    item["spots_left"] = max(0, item["capacity"] - item["registrations"])
    return item

@app.get("/")
def root():
    return {"name": "Campusly College Event API", "version": "1.0.0", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "campusly-api"}

@app.get("/api/events")
def list_events(q: Optional[str] = None, category: Optional[str] = None, student_id: Optional[str] = None):
    sql = "SELECT * FROM events WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR venue LIKE ? OR category LIKE ?)"
        params.extend([f"%{q}%"] * 3)
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY event_date ASC, id ASC"
    with connect() as db:
        rows = db.execute(sql, params).fetchall()
    return [event_dict(row, student_id) for row in rows]

@app.get("/api/events/{event_id}")
def get_event(event_id: int, student_id: Optional[str] = None):
    with connect() as db:
        row = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Event not found")
    return event_dict(row, student_id)

@app.post("/api/events", status_code=201)
def create_event(payload: EventCreate):
    with connect() as db:
        cur = db.execute("INSERT INTO events(title,category,event_date,event_time,venue,capacity,description) VALUES(?,?,?,?,?,?,?)", (payload.title, payload.category, payload.event_date.isoformat(), payload.event_time, payload.venue, payload.capacity, payload.description))
        row = db.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone()
    return event_dict(row)

@app.put("/api/events/{event_id}")
def update_event(event_id: int, payload: EventCreate):
    with connect() as db:
        exists = db.execute("SELECT id FROM events WHERE id=?", (event_id,)).fetchone()
        if not exists:
            raise HTTPException(404, "Event not found")
        db.execute("UPDATE events SET title=?,category=?,event_date=?,event_time=?,venue=?,capacity=?,description=? WHERE id=?", (payload.title, payload.category, payload.event_date.isoformat(), payload.event_time, payload.venue, payload.capacity, payload.description, event_id))
        row = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    return event_dict(row)

@app.delete("/api/events/{event_id}", status_code=204)
def delete_event(event_id: int):
    with connect() as db:
        if not db.execute("SELECT id FROM events WHERE id=?", (event_id,)).fetchone():
            raise HTTPException(404, "Event not found")
        db.execute("DELETE FROM registrations WHERE event_id=?", (event_id,))
        db.execute("DELETE FROM events WHERE id=?", (event_id,))
    return None

@app.post("/api/events/{event_id}/registrations", status_code=201)
def register(event_id: int, payload: RegistrationCreate):
    with connect() as db:
        event = db.execute("SELECT capacity FROM events WHERE id=?", (event_id,)).fetchone()
        if not event:
            raise HTTPException(404, "Event not found")
        count = db.execute("SELECT COUNT(*) FROM registrations WHERE event_id=?", (event_id,)).fetchone()[0]
        if db.execute("SELECT id FROM registrations WHERE event_id=? AND student_id=?", (event_id, payload.student_id)).fetchone():
            raise HTTPException(409, "Student is already registered for this event")
        if count >= event["capacity"]:
            raise HTTPException(409, "This event is full")
        cur = db.execute("INSERT INTO registrations(event_id,student_id) VALUES(?,?)", (event_id, payload.student_id))
        row = db.execute("SELECT * FROM registrations WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@app.delete("/api/events/{event_id}/registrations/{student_id}", status_code=204)
def cancel_registration(event_id: int, student_id: str):
    with connect() as db:
        cur = db.execute("DELETE FROM registrations WHERE event_id=? AND student_id=?", (event_id, student_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Registration not found")
    return None

@app.get("/api/students/{student_id}/registrations")
def student_registrations(student_id: str):
    with connect() as db:
        rows = db.execute("SELECT e.* FROM events e JOIN registrations r ON r.event_id=e.id WHERE r.student_id=? ORDER BY e.event_date", (student_id,)).fetchall()
    return [event_dict(row, student_id) for row in rows]

@app.post("/api/predict")
def predict(payload: PredictionInput):
    # Transparent baseline score for demonstration; replace with a trained, validated model for real use.
    score = round(max(0, min(100, payload.previous_marks * .42 + payload.attendance * .22 + payload.assignments_completed * .21 + min(payload.study_hours, 8) / 8 * 15)), 1)
    band = "Excellent progress" if score >= 85 else "Good progress" if score >= 70 else "Developing steadily" if score >= 55 else "Needs focused support"
    tips = []
    if payload.attendance < 75: tips.append("Consider improving attendance.")
    if payload.assignments_completed < 80: tips.append("Try to complete more assignments on time.")
    if payload.study_hours < 2: tips.append("Build a consistent study routine.")
    if not tips: tips.append("Keep building on your current habits.")
    return {"estimated_score": score, "band": band, "suggestions": tips, "disclaimer": "Illustrative estimate only; not a validated or guaranteed academic prediction."}

@app.get("/api/stats")
def stats():
    with connect() as db:
        total_events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        registrations = db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
        categories = db.execute("SELECT category, COUNT(*) AS count FROM events GROUP BY category ORDER BY count DESC").fetchall()
    return {"total_events": total_events, "total_registrations": registrations, "categories": [dict(r) for r in categories]}
