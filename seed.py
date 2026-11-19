"""Create 40 NSUT demo students: two sections per branch and year, PIN 1234."""
import os
from werkzeug.security import generate_password_hash
from database import DB_PATH, get_db, init_db, parse_roll_number

NAMES = [
    "Aarav Mehta", "Isha Kapoor", "Kabir Bansal", "Ananya Rao", "Rohan Sethi", "Meera Nair",
    "Dev Malhotra", "Sana Qureshi", "Arjun Khanna", "Tara Das", "Nikhil Verma", "Priya Menon",
    "Yash Gupta", "Simran Kaur", "Aditya Bose", "Zoya Ali", "Rahul Jain", "Diya Shah",
    "Ishaan Dutta", "Leela Thomas", "Vivaan Sood", "Aditi Mukherjee", "Rehan Siddiqui", "Kavya Iyer",
    "Manav Bhatia", "Nandini Sen", "Ayaan Chawla", "Ritika Ghosh", "Siddharth Rao", "Mira Kulkarni",
    "Karan Oberoi", "Pooja Reddy", "Neil Fernandes", "Sakshi Anand", "Farhan Mirza", "Tanvi Desai",
    "Om Prakash", "Rhea Banerjee", "Akhil Narang", "Nisha Pillai",
]

BRANCH_CODES = {"CSE": "CS", "IT": "IT", "ECE": "EC", "EE": "EE", "ME": "ME"}
BRANCH_SKILLS = {
    "CSE": ["Python", "C++ / DSA", "Web Development", "Machine Learning", "Cybersecurity", "Chess", "Creative Writing"],
    "IT": ["Linux & Networking", "Web Pentesting", "OSINT", "UI/UX Design", "Data Science", "Photography", "Public Speaking & Debate"],
    "ECE": ["PCB & KiCad", "Robotics & IoT", "Embedded Systems", "Electronics", "Python", "Music & Guitar", "Sketching"],
    "EE": ["Machine Learning", "Robotics & IoT", "Electronics", "Python", "Gym & Strength Training", "Running & Endurance", "Digital Painting"],
    "ME": ["Mechanical Design", "SolidWorks & CAD", "3D Printing", "AutoCAD", "Robotics & IoT", "Badminton", "Photography"],
}
BIOS = [
    "Enjoys learning with peers and sharing practical notes after class.",
    "Looking for collaborators who like steady progress and thoughtful feedback.",
    "Happy to compare approaches, explain a tricky topic, or build a small project.",
    "Splits time between coursework and a few hands-on projects outside class.",
    "Interested in meeting people with different skills and working styles.",
    "Often found practicing a new skill and trading useful resources with friends.",
    "Would like a reliable study group for problem solving and exam revision.",
    "Interested in campus projects that combine technical and creative work.",
]
INTENTS = ["Study Partner", "Open to Doubts", "Project Team"]
ADMISSION_YEARS = {1: 2026, 2: 2025, 3: 2024, 4: 2023}


def profiles():
    """Generate a balanced directory with exactly sections 1 and 2 in each cohort."""
    index = 0
    for year in range(1, 5):
        for branch_index, branch in enumerate(BRANCH_CODES):
            for section_number in (1, 2):
                name = NAMES[index]
                section = f"{branch}-{section_number}"
                roll_tail = 1000 + branch_index * 100 + section_number * 10 + year
                roll = f"{ADMISSION_YEARS[year]}U{BRANCH_CODES[branch]}{roll_tail:04d}"
                skill_pool = BRANCH_SKILLS[branch]
                start = (year + section_number + branch_index) % len(skill_pool)
                skills = [(skill_pool[(start + offset) % len(skill_pool)],
                           ("Beginner", "Intermediate", "Advanced")[(index + offset) % 3])
                          for offset in range(3)]
                slug = "".join(part.lower() for part in name.split())
                whatsapp = f"91{9000000000 + index + 1}"
                contacts = {
                    "whatsapp": str(9000000000 + index + 1),
                    "instagram": f"{slug}_{section_number}",
                    "linkedin": f"linkedin.com/in/{slug}",
                    "discord": f"{slug}.{index + 1}",
                    "github": slug,
                }
                yield {
                    "name": name, "roll_no": roll, "section": section, "year": year,
                    "branch": branch, "intent": INTENTS[index % len(INTENTS)],
                    "bio": BIOS[(index + year) % len(BIOS)],
                    "email": f"{roll.lower()}@nsut.ac.in", "contacts": contacts, "skills": skills,
                }
                index += 1


def populate_profiles():
    inserted = 0
    with get_db() as db:
        for profile in profiles():
            roll, year, branch = parse_roll_number(profile["roll_no"])
            # Keep section tied to the roll-number branch; only cohorts 1 and 2 are valid.
            if profile["section"] not in (f"{branch}-1", f"{branch}-2") or profile["year"] != year:
                raise ValueError(f"Invalid demo cohort for {roll}.")
            contact = profile["contacts"]
            cur = db.execute("""INSERT OR IGNORE INTO users
                (roll_no,pin_hash,name,email,whatsapp,instagram,linkedin,discord,github,year,branch,section,intent,bio)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (roll, generate_password_hash("1234"), profile["name"], profile["email"],
                 contact["whatsapp"], contact["instagram"], contact["linkedin"], contact["discord"],
                 contact["github"], year, branch, profile["section"], profile["intent"], profile["bio"]))
            if cur.rowcount:
                db.executemany("INSERT INTO user_skills(user_id,skill_name,proficiency) VALUES(?,?,?)",
                               [(cur.lastrowid, skill, level) for skill, level in profile["skills"]])
                inserted += 1
    return inserted


def seed_if_empty():
    """Auto-populate an empty or nearly empty directory when Flask starts."""
    init_db()
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count < 5:
        populate_profiles()


def seed():
    """Delete and recreate the SQLite file, then insert all 40 demo students."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    inserted = populate_profiles()
    print(f"SkillSync database ready: {inserted} profiles inserted across 4 years, 5 branches, and 2 sections; all PINs are 1234.")


if __name__ == "__main__":
    seed()
