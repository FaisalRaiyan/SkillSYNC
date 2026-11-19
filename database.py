"""SQLite schema, connection management, and NSUT roll-number parsing."""
import os
import re
import sqlite3
from contextlib import contextmanager

# Vercel exposes only /tmp as writable; local runs keep the database beside the app.
DB_PATH = "/tmp/skillsync.db" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "skillsync.db")
ROLL_RE = re.compile(r"^202[3-6]U[A-Z]{2}\d{4}$", re.IGNORECASE)
BRANCH_NAMES = {"CS": "CSE", "IT": "IT", "EC": "ECE", "EE": "EE", "ME": "ME"}
BRANCHES = tuple(BRANCH_NAMES.values())
VALID_SECTIONS = tuple(f"{branch}-{number}" for branch in BRANCHES for number in (1, 2))
INTENTS = {"Study Partner", "Open to Doubts", "Project Team"}
PROFICIENCIES = {"Beginner", "Intermediate", "Advanced"}

# Seeded as suggestions in the builder; saved custom names join them in /api/skills.
POPULAR_SKILLS = [
    "Red Teaming", "Blue Teaming / SOC", "Web Pentesting", "OSINT", "Linux & Networking",
    "Python", "C++ / DSA", "Web Development", "Machine Learning", "PCB & KiCad",
    "Robotics & IoT", "Competitive Programming", "UI/UX Design", "Cloud Computing",
    "Data Science", "Java", "JavaScript", "SQL & Databases", "Mobile App Development",
    "DevOps & CI/CD", "Blockchain", "Game Development", "Embedded Systems", "Electronics",
    "Git & Open Source", "Public Speaking", "Gym & Strength Training", "Running & Endurance",
    "Calisthenics", "Yoga & Mobility", "Football", "Cricket", "Badminton", "Basketball",
    "Table Tennis", "Chess", "Digital Painting", "Sketching", "Photography", "Video Editing",
    "Music & Guitar", "Music Production", "Dance", "Theatre & Acting", "Public Speaking & Debate",
    "Creative Writing", "Content Creation", "Fashion & Styling", "Cooking & Baking",
    "Personal Finance", "Entrepreneurship", "Event Planning", "Volunteering", "Sustainability",
    "Languages & Linguistics", "Film & Cinema", "Design Research", "Product Management",
    "Mechanical Design", "SolidWorks & CAD", "3D Printing", "AutoCAD", "Thermodynamics",
    "Materials Science", "Product Design", "Mathematics", "Research & Academia",
]


@contextmanager
def get_db():
    """Yield a row-aware connection, committing on success and closing every request."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_roll_number(value):
    """Return (uppercase roll number, current year, expanded branch)."""
    roll = (value or "").strip().upper()
    if not ROLL_RE.fullmatch(roll):
        raise ValueError("Enter a roll number such as 2026UCS1724.")
    year = 2026 - int(roll[:4]) + 1
    branch_code = roll[5:7]
    return roll, year, BRANCH_NAMES.get(branch_code, branch_code)


def init_db():
    """Create the user, skill and invite tables and their lookup indexes."""
    with get_db() as db:
        # Reset an older app schema before it can partially serve the new contact fields.
        existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "users" in existing:
            user_columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
            required = {"id", "roll_no", "pin_hash", "name", "email", "whatsapp", "instagram",
                        "linkedin", "discord", "github", "year", "branch", "section", "intent", "bio"}
            if not required.issubset(user_columns):
                db.executescript("DROP TABLE IF EXISTS invites; DROP TABLE IF EXISTS user_skills; DROP TABLE IF EXISTS users;")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT NOT NULL UNIQUE,
            pin_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            whatsapp TEXT NOT NULL DEFAULT '',
            instagram TEXT NOT NULL DEFAULT '',
            linkedin TEXT NOT NULL DEFAULT '',
            discord TEXT NOT NULL DEFAULT '',
            github TEXT NOT NULL DEFAULT '',
            year INTEGER NOT NULL,
            branch TEXT NOT NULL CHECK(branch IN ('CSE','IT','ECE','EE','ME')),
            section TEXT NOT NULL CHECK(section IN ('CSE-1','CSE-2','IT-1','IT-2','ECE-1','ECE-2','EE-1','EE-2','ME-1','ME-2')),
            intent TEXT NOT NULL CHECK(intent IN ('Study Partner','Open to Doubts','Project Team')),
            bio TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS user_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            skill_name TEXT NOT NULL,
            proficiency TEXT NOT NULL CHECK(proficiency IN ('Beginner','Intermediate','Advanced')),
            UNIQUE(user_id, skill_name)
        );
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            group_topic TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Accepted','Declined')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_users_class ON users(branch, section);
        CREATE INDEX IF NOT EXISTS idx_skills_name ON user_skills(skill_name);
        CREATE INDEX IF NOT EXISTS idx_invites_recipient ON invites(recipient_id, status);
        CREATE INDEX IF NOT EXISTS idx_invites_sender ON invites(sender_id, created_at);
        """)
