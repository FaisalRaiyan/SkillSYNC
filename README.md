# NSUT SkillSync — Campus Skill & Study Partner Directory

**NSUT SkillSync** is a full-stack campus directory and peer-discovery web application built with **Python (Flask)**, **SQLite**, and **Vanilla JavaScript**. Designed for university students, it makes it easy to discover peers across years, branches, and sections who share technical skills, creative hobbies, or fitness interests—whether you are looking for a study partner, a project teammate, or a senior open to answering doubts.

---

## Key Features

- **Smart Roll-Number Validation & Auto-Parsing:** Validates NSUT roll numbers via regular expressions (e.g., `2026UCS1042`) and automatically extracts the student's **Academic Year** and **Branch**
- **Secure PIN Authentication:** Uses salted password hashing (`werkzeug.security`) with 4-digit PINs and server-side Flask sessions.
- **LinkedIn-Style Skill & Interest Builder:** Searchable autocomplete dropdown with suggestions across Cybersecurity, Software/Hardware Engineering, Fitness, and Arts—plus support for adding custom skills paired with proficiency levels (`Beginner`, `Intermediate`, `Advanced`).
- **Live Multi-Criteria Filtering & Compatibility Scoring:** Filter the directory in real time by **Name/Roll No**, **Year**, **Branch**, **Section**, **Skill/Interest**, or **Proficiency Level**, toggle **"My Class Only"**, and sort peers by **Skill Match %**.
- **One-Click Contact & Multi-Select Study Squad Invites:** Copy a peer's Email, WhatsApp, Instagram, LinkedIn, Discord, or GitHub handle with a single click, or select up to 10 peers to send an in-app study group invite alongside a pre-filled `mailto:` email trigger.
- **Adaptive Light & Dark Theme:** Crisp high-contrast Light Mode by default with a persistent Dark Mode toggle and Phosphor Icons.

---

## Tech Stack

- **Backend:** Python 3, Flask (RESTful JSON API)
- **Database:** SQLite (`sqlite3` with relational foreign keys and cascade deletes)
- **Frontend:** HTML5, Modern CSS3 (CSS Custom Properties), Vanilla JavaScript (`fetch` API)
- **Icons:** [Phosphor Icons](https://phosphoricons.com/)
- **Deployment:** Configured for local execution and serverless deployment on **Vercel** (`vercel.json`)

---

## Project Structure

```text
SkillSYNC/
├── app.py              # Flask application & REST API endpoints
├── database.py         # SQLite schema, connection helper & roll-number parser
├── seed.py             # Populates 40 realistic student profiles (default PIN: 1234)
├── requirements.txt    # Python dependencies (Flask)
├── vercel.json         # Vercel serverless routing configuration
├── templates/
│   └── index.html      # Single-page application layout & modals
└── static/
    ├── style.css       # Light/Dark theme tokens, responsive grid & card styling
    └── app.js          # Frontend state management, autocomplete & API calls
```

---

## Local Setup & Running

1. **Clone the repository:**
   ```bash
   git clone https://github.com/FaisalRaiyan/SkillSYNC.git
   cd SkillSYNC
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Seed the database with 40 sample student profiles:**
   ```bash
   python seed.py
   ```

4. **Start the Flask server:**
   ```bash
   python app.py
   ```
   Open **`http://127.0.0.1:5000`** in your browser (or run `python -m flask run --port 5050` to use port `5050`).

> **Demo Login:** You can register a new roll number or log in as any seeded student (e.g., `2026UCS1011`) using PIN **`1234`**.

---

## Deployment (Vercel)

This repository includes `vercel.json` and an automatic `/tmp` SQLite fallback when running in a serverless environment (`VERCEL=1`). Import the repository into [Vercel](https://vercel.com/) with the framework preset set to **Other** to deploy directly.
