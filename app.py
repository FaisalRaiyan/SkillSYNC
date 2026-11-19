"""Flask page and JSON API for the NSUT SkillSync directory."""
import os
import re
from flask import Flask, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import BRANCHES, DB_PATH, INTENTS, POPULAR_SKILLS, PROFICIENCIES, get_db, parse_roll_number
from seed import seed_if_empty

app = Flask(__name__)
app.config["DATABASE"] = DB_PATH
app.secret_key = os.environ.get("SKILLSYNC_SECRET", "skillsync-local-demo-secret-change-me")
app.json.ensure_ascii = False
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
CONTACT_FIELDS = ("whatsapp", "instagram", "linkedin", "discord", "github")
MAX_SKILLS = 20


def error(message, status=400):
    return jsonify({"error": message}), status


def current_user(db):
    user_id = session.get("user_id")
    return db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone() if user_id else None


def skills_for(db, user_id):
    return [dict(row) for row in db.execute(
        "SELECT skill_name,proficiency FROM user_skills WHERE user_id=? ORDER BY skill_name COLLATE NOCASE", (user_id,))]


def profile_dict(db, row):
    result = {key: row[key] for key in ("id", "roll_no", "name", "email", *CONTACT_FIELDS,
                 "year", "branch", "section", "intent", "bio")}
    result["skills"] = skills_for(db, row["id"])
    return result


def clean_skills(value):
    """Validate skill entries while allowing useful custom skills and hobbies."""
    if not isinstance(value, list) or len(value) > MAX_SKILLS:
        raise ValueError(f"Add up to {MAX_SKILLS} interests.")
    result, seen = [], set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Each interest needs a name and proficiency.")
        name = re.sub(r"\s+", " ", str(item.get("skill_name", "")).strip())
        level = item.get("proficiency")
        if not name or len(name) > 64 or level not in PROFICIENCIES:
            raise ValueError("Use an interest up to 64 characters and a valid proficiency.")
        key = name.casefold()
        if key not in seen:
            result.append((name, level))
            seen.add(key)
    return result


def validate_contacts(data):
    contacts = {field: str(data.get(field, "")).strip() for field in CONTACT_FIELDS}
    contacts["instagram"] = contacts["instagram"].removeprefix("@").strip()
    whatsapp = contacts["whatsapp"]
    if whatsapp and not re.fullmatch(r"\d{10}", whatsapp):
        raise ValueError("WhatsApp must contain exactly 10 digits.")
    if any(len(value) > 160 for key, value in contacts.items() if key != "whatsapp"):
        raise ValueError("Contact handles must be 160 characters or fewer.")
    return contacts


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/skills")
def list_skills():
    """Return popular starter suggestions plus every saved user-created interest."""
    with get_db() as db:
        present = [row[0] for row in db.execute("SELECT DISTINCT skill_name FROM user_skills ORDER BY skill_name COLLATE NOCASE")]
    by_name = {name.casefold(): name for name in POPULAR_SKILLS}
    by_name.update({name.casefold(): name for name in present})
    return jsonify(sorted(by_name.values(), key=str.casefold))


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    try:
        roll, year, branch = parse_roll_number(data.get("roll_no"))
        if branch not in BRANCHES:
            return error("Roll number must use a supported NSUT branch code.")
        pin = str(data.get("pin", ""))
        if not re.fullmatch(r"\d{4}", pin):
            return error("PIN must be exactly 4 digits.")
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        section = str(data.get("section", "")).strip().upper()
        intent = data.get("intent")
        bio = str(data.get("bio", "")).strip()
        contacts = validate_contacts(data)
        skills = clean_skills(data.get("skills", []))
        if not name or len(name) > 80 or not EMAIL_RE.fullmatch(email) or not section:
            return error("Enter your name, a valid email, and section.")
        if intent not in INTENTS:
            return error("Choose a valid collaboration intent.")
        if section not in (f"{branch}-1", f"{branch}-2"):
            return error(f"Choose section {branch}-1 or {branch}-2 based on your roll number.")
        if len(section) > 20 or len(bio) > 500:
            return error("Section or bio exceeds the allowed length.")
    except ValueError as exc:
        return error(str(exc))
    with get_db() as db:
        try:
            cur = db.execute("""INSERT INTO users
                (roll_no,pin_hash,name,email,whatsapp,instagram,linkedin,discord,github,year,branch,section,intent,bio)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (roll, generate_password_hash(pin), name, email, contacts["whatsapp"], contacts["instagram"],
                 contacts["linkedin"], contacts["discord"], contacts["github"], year, branch, section, intent, bio))
            user_id = cur.lastrowid
            db.executemany("INSERT INTO user_skills(user_id,skill_name,proficiency) VALUES(?,?,?)",
                           [(user_id, skill, level) for skill, level in skills])
        except Exception as exc:
            if "UNIQUE" in str(exc):
                return error("That roll number is already registered.", 409)
            raise
        session["user_id"] = user_id
        return jsonify(profile_dict(db, db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    try:
        roll, _, _ = parse_roll_number(data.get("roll_no"))
    except ValueError as exc:
        return error(str(exc))
    pin = str(data.get("pin", ""))
    if not re.fullmatch(r"\d{4}", pin):
        return error("PIN must be exactly 4 digits.")
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE roll_no=?", (roll,)).fetchone()
        if not row or not check_password_hash(row["pin_hash"], pin):
            return error("Roll number or PIN is incorrect.", 401)
        session["user_id"] = row["id"]
        return jsonify(profile_dict(db, row))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    with get_db() as db:
        row = current_user(db)
        return jsonify(profile_dict(db, row) if row else None)


@app.get("/api/students")
def students():
    args = request.args
    clauses, values = [], []
    search = args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        clauses.append("(u.name LIKE ? OR u.roll_no LIKE ? OR u.bio LIKE ?)")
        values.extend([like, like, like])
    for param, column in (("year", "u.year"), ("branch", "u.branch"), ("section", "u.section"), ("intent", "u.intent")):
        value = args.get(param, "").strip()
        if value:
            clauses.append(f"{column}=?")
            values.append(value)
    skill, proficiency = args.get("skill", "").strip(), args.get("proficiency", "").strip()
    if skill:
        clauses.append("EXISTS (SELECT 1 FROM user_skills sx WHERE sx.user_id=u.id AND sx.skill_name=? COLLATE NOCASE")
        values.append(skill)
        if proficiency:
            clauses[-1] += " AND sx.proficiency=?"
            values.append(proficiency)
        clauses[-1] += ")"
    elif proficiency:
        clauses.append("EXISTS (SELECT 1 FROM user_skills sx WHERE sx.user_id=u.id AND sx.proficiency=?)")
        values.append(proficiency)
    query = "SELECT u.* FROM users u" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY u.name COLLATE NOCASE"
    with get_db() as db:
        me_row = current_user(db)
        own_skills = {s["skill_name"].casefold(): s["proficiency"] for s in skills_for(db, me_row["id"])} if me_row else {}
        result = []
        for row in db.execute(query, values).fetchall():
            item = profile_dict(db, row)
            if me_row:
                peer_skills = {s["skill_name"].casefold(): s["proficiency"] for s in item["skills"]}
                overlap = own_skills.keys() & peer_skills.keys()
                score = (100 * len(overlap) / len(own_skills)) if own_skills else 0
                score += sum(12 for name in overlap if own_skills[name] == "Beginner" and
                             (peer_skills[name] == "Advanced" or row["intent"] == "Open to Doubts"))
                item["match_score"] = min(100, round(score))
            result.append(item)
        return jsonify(result)


@app.put("/api/profile")
def update_profile():
    if not session.get("user_id"):
        return error("Log in to edit your profile.", 401)
    data = request.get_json(silent=True) or {}
    intent, bio = data.get("intent"), str(data.get("bio", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    try:
        contacts = validate_contacts(data)
        skills = clean_skills(data.get("skills", []))
    except ValueError as exc:
        return error(str(exc))
    if intent not in INTENTS or len(bio) > 500 or not EMAIL_RE.fullmatch(email):
        return error("Enter a valid email, choose an intent, and keep the bio under 500 characters.")
    with get_db() as db:
        user_id = session["user_id"]
        db.execute("""UPDATE users SET email=?,intent=?,bio=?,whatsapp=?,instagram=?,linkedin=?,discord=?,github=? WHERE id=?""",
                   (email, intent, bio, contacts["whatsapp"], contacts["instagram"], contacts["linkedin"],
                    contacts["discord"], contacts["github"], user_id))
        db.execute("DELETE FROM user_skills WHERE user_id=?", (user_id,))
        db.executemany("INSERT INTO user_skills(user_id,skill_name,proficiency) VALUES(?,?,?)",
                       [(user_id, skill, level) for skill, level in skills])
        return jsonify(profile_dict(db, db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()))


@app.post("/api/invites")
def create_invites():
    if not session.get("user_id"):
        return error("Log in to send study group invites.", 401)
    data = request.get_json(silent=True) or {}
    ids, topic = data.get("recipient_ids"), str(data.get("group_topic", "")).strip()
    message = str(data.get("message", "")).strip()
    if not isinstance(ids, list) or not 1 <= len(ids) <= 10 or len(set(map(str, ids))) != len(ids):
        return error("Select between 1 and 10 different peers.")
    if not topic or len(topic) > 120 or len(message) > 500:
        return error("Add a topic under 120 characters and a note under 500 characters.")
    try:
        ids = [int(value) for value in ids]
    except (TypeError, ValueError):
        return error("Invalid recipient list.")
    with get_db() as db:
        sender_id = session["user_id"]
        ids = [value for value in ids if value != sender_id]
        if not ids:
            return error("Select at least one other peer.")
        rows = db.execute(f"SELECT id,email FROM users WHERE id IN ({','.join('?' for _ in ids)})", ids).fetchall()
        if len(rows) != len(ids):
            return error("One or more selected peers no longer exist.")
        db.executemany("INSERT INTO invites(sender_id,recipient_id,group_topic,message) VALUES(?,?,?,?)",
                       [(sender_id, recipient_id, topic, message) for recipient_id in ids])
        return jsonify({"ok": True, "recipients": [dict(row) for row in rows]}), 201


@app.get("/api/invites")
def list_invites():
    if not session.get("user_id"):
        return error("Log in to view invites.", 401)
    with get_db() as db:
        user_id = session["user_id"]
        def fetch(where, value):
            return [dict(row) for row in db.execute(f"""SELECT i.*,s.name AS sender_name,s.roll_no AS sender_roll,
                r.name AS recipient_name,r.roll_no AS recipient_roll FROM invites i
                JOIN users s ON s.id=i.sender_id JOIN users r ON r.id=i.recipient_id
                WHERE i.{where}=? ORDER BY i.created_at DESC,i.id DESC""", (value,))]
        return jsonify({"received": fetch("recipient_id", user_id), "sent": fetch("sender_id", user_id)})


@app.put("/api/invites/<int:invite_id>")
def update_invite(invite_id):
    if not session.get("user_id"):
        return error("Log in to respond to invites.", 401)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in ("Accepted", "Declined"):
        return error("Status must be Accepted or Declined.")
    with get_db() as db:
        cur = db.execute("UPDATE invites SET status=? WHERE id=? AND recipient_id=? AND status='Pending'",
                         (status, invite_id, session["user_id"]))
        if not cur.rowcount:
            return error("Pending invite not found.", 404)
        return jsonify({"ok": True, "status": status})


# Both imports use the same absolute DB_PATH; initialize and top up before serving requests.
seed_if_empty()

if __name__ == "__main__":
    app.run(debug=False)
