import os, json, re, secrets, pickle
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import fitz
from PIL import Image
import pytesseract
from io import BytesIO

# Auto-detect common Windows Tesseract installations. On Linux/Render, use PATH.
if os.name == "nt":
    for _tesseract_path in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ):
        if os.path.isfile(_tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = _tesseract_path
            break

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
UPLOAD_DIR = os.path.join(ROOT, "uploads")
DB_PATH = os.path.join(DATA_DIR, "skillai.sqlite3")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
MODEL_PATH = os.path.join(ROOT, "career_model.pkl")
CAREER_MODEL = None
CAREER_VECTORIZER = None
try:
    with open(MODEL_PATH, "rb") as model_file:
        _bundle = pickle.load(model_file)
        CAREER_MODEL = _bundle["model"]
        CAREER_VECTORIZER = _bundle["vectorizer"]
except (OSError, pickle.PickleError, EOFError, KeyError, AttributeError):
    # The app remains usable if the optional ML artifact is unavailable.
    CAREER_MODEL = None
    CAREER_VECTORIZER = None
ALLOWED_EXTENSIONS = {"pdf", "txt", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"}

ROLES = {
    # Software and application development
    "Software Developer": {"required": ["Python", "Java", "Data Structures", "Algorithms", "SQL", "Git", "REST APIs", "Testing", "OOP"]},
    "Frontend Developer": {"required": ["HTML", "CSS", "JavaScript", "TypeScript", "React", "Responsive Design", "Accessibility", "Git"]},
    "Backend Developer": {"required": ["Python", "Java", "Node.js", "REST APIs", "SQL", "Authentication", "Testing", "Git"]},
    "Full Stack Developer": {"required": ["HTML", "CSS", "JavaScript", "React", "Node.js", "REST APIs", "SQL", "Git"]},
    "Web Developer": {"required": ["HTML", "CSS", "JavaScript", "Responsive Design", "Git", "REST APIs", "Accessibility", "Testing"]},
    "Mobile App Developer": {"required": ["Java", "Kotlin", "Swift", "Dart", "Flutter", "REST APIs", "Git", "Mobile UI"]},
    "Android Developer": {"required": ["Kotlin", "Java", "Android SDK", "REST APIs", "SQLite", "Git", "Testing"]},
    "iOS Developer": {"required": ["Swift", "SwiftUI", "Xcode", "REST APIs", "Core Data", "Git", "Testing"]},
    "Game Developer": {"required": ["C#", "C++", "Unity", "Unreal Engine", "3D Math", "Git", "Debugging"]},
    "Desktop Application Developer": {"required": ["Python", "Java", "C#", "GUI Development", "SQL", "Testing", "Git"]},
    "Embedded Systems Engineer": {"required": ["C", "C++", "Microcontrollers", "Embedded C", "Electronics", "UART", "SPI", "I2C"]},
    "IoT Developer": {"required": ["Python", "C++", "Microcontrollers", "Sensors", "MQTT", "Networking", "Cloud Computing"]},
    "Robotics Engineer": {"required": ["Python", "C++", "ROS", "Control Systems", "Sensors", "Computer Vision", "Embedded Systems"]},
    "Blockchain Developer": {"required": ["JavaScript", "Solidity", "Smart Contracts", "Ethereum", "Cryptography", "Git", "Web3"]},

    # Data, AI and analytics
    "Data Analyst": {"required": ["Python", "SQL", "Excel", "Statistics", "Power BI", "Data Visualization", "Pandas"]},
    "Business Intelligence Analyst": {"required": ["SQL", "Power BI", "Tableau", "Excel", "Data Modeling", "Data Visualization", "Business Analysis"]},
    "Data Scientist": {"required": ["Python", "SQL", "Statistics", "Machine Learning", "Pandas", "NumPy", "Data Visualization", "Model Evaluation"]},
    "Data Engineer": {"required": ["Python", "SQL", "ETL", "Data Warehousing", "Apache Spark", "Cloud Computing", "Data Pipelines", "Git"]},
    "Machine Learning Engineer": {"required": ["Python", "Statistics", "Linear Algebra", "Machine Learning", "NumPy", "Pandas", "Model Evaluation", "Git"]},
    "AI Engineer": {"required": ["Python", "Machine Learning", "Deep Learning", "APIs", "Data Cleaning", "Model Evaluation", "Git"]},
    "Generative AI Engineer": {"required": ["Python", "LLMs", "Prompt Engineering", "Embeddings", "Vector Databases", "RAG", "APIs", "Model Evaluation"]},
    "NLP Engineer": {"required": ["Python", "Natural Language Processing", "Machine Learning", "Deep Learning", "Transformers", "Text Processing", "Model Evaluation"]},
    "Computer Vision Engineer": {"required": ["Python", "OpenCV", "Computer Vision", "Deep Learning", "Image Processing", "PyTorch", "Model Evaluation"]},
    "Data Quality Analyst": {"required": ["SQL", "Excel", "Data Cleaning", "Data Validation", "Statistics", "Documentation"]},

    # Cloud, DevOps and IT infrastructure
    "DevOps Engineer": {"required": ["Linux", "Git", "Docker", "Kubernetes", "CI/CD", "Python", "Cloud Computing", "Monitoring"]},
    "Cloud Engineer": {"required": ["AWS", "Azure", "Google Cloud", "Linux", "Networking", "Docker", "Infrastructure as Code", "Security Fundamentals"]},
    "Site Reliability Engineer": {"required": ["Linux", "Python", "Networking", "Monitoring", "Incident Management", "Cloud Computing", "Docker", "Automation"]},
    "Platform Engineer": {"required": ["Kubernetes", "Docker", "CI/CD", "Linux", "Cloud Computing", "Infrastructure as Code", "Monitoring"]},
    "System Administrator": {"required": ["Linux", "Windows Server", "Networking", "Active Directory", "Backup and Recovery", "Scripting", "Troubleshooting"]},
    "Network Engineer": {"required": ["Networking", "TCP/IP", "DNS", "Routing", "Switching", "Firewalls", "Network Security", "Troubleshooting"]},
    "IT Support Specialist": {"required": ["Troubleshooting", "Windows", "Linux", "Networking", "Hardware Support", "Customer Service", "Ticketing Systems"]},
    "Database Administrator": {"required": ["SQL", "Database Design", "Database Backup", "Performance Tuning", "Security Fundamentals", "Linux", "Monitoring"]},
    "QA Engineer": {"required": ["Software Testing", "Test Cases", "Bug Tracking", "SQL", "API Testing", "Regression Testing", "Documentation"]},
    "Automation Test Engineer": {"required": ["Python", "Java", "Selenium", "API Testing", "Test Automation", "CI/CD", "Git", "SQL"]},
    "Technical Support Engineer": {"required": ["Troubleshooting", "Networking", "Linux", "SQL", "Customer Service", "Documentation", "Ticketing Systems"]},

    # Cybersecurity
    "Cybersecurity Engineer": {"required": ["Networking", "Linux", "Python", "Security Fundamentals", "Web Security", "Risk Assessment", "Git"]},
    "SOC Analyst": {"required": ["Networking", "SIEM", "Log Analysis", "Incident Response", "Security Fundamentals", "Threat Intelligence", "Linux"]},
    "Penetration Tester": {"required": ["Networking", "Linux", "Web Security", "OWASP", "Burp Suite", "Python", "Vulnerability Assessment"]},
    "Security Analyst": {"required": ["Security Fundamentals", "Risk Assessment", "Networking", "Log Analysis", "Incident Response", "Vulnerability Assessment"]},
    "Cloud Security Engineer": {"required": ["AWS", "Azure", "Cloud Security", "Identity and Access Management", "Networking", "Linux", "Security Monitoring"]},
    "Digital Forensics Analyst": {"required": ["Digital Forensics", "Incident Response", "Linux", "Windows", "Log Analysis", "Evidence Handling", "Networking"]},

    # Product, design and business-facing tech roles
    "UI/UX Designer": {"required": ["User Research", "Wireframing", "Prototyping", "Figma", "Usability Testing", "Accessibility", "Design Systems"]},
    "Product Designer": {"required": ["User Research", "Figma", "Prototyping", "Design Systems", "Usability Testing", "Interaction Design", "Accessibility"]},
    "Product Manager": {"required": ["Product Strategy", "Roadmapping", "User Research", "Analytics", "Stakeholder Management", "Agile", "Communication"]},
    "Business Analyst": {"required": ["Business Analysis", "Requirements Gathering", "SQL", "Excel", "Process Mapping", "Documentation", "Communication"]},
    "Project Manager - IT": {"required": ["Project Planning", "Risk Management", "Agile", "Scrum", "Stakeholder Management", "Communication", "Documentation"]},
    "Scrum Master": {"required": ["Scrum", "Agile", "Facilitation", "Sprint Planning", "Conflict Resolution", "Communication", "Retrospectives"]},
    "Technical Writer": {"required": ["Technical Writing", "Documentation", "Editing", "API Documentation", "Markdown", "Communication", "Research"]},
    "Solutions Architect": {"required": ["System Design", "Cloud Computing", "Networking", "Security Fundamentals", "APIs", "Database Design", "Communication"]},
    "Salesforce Developer": {"required": ["Salesforce", "Apex", "Lightning Web Components", "JavaScript", "SOQL", "APIs", "Git"]},
    "SAP Consultant": {"required": ["SAP", "ERP", "Business Processes", "Requirements Gathering", "Data Migration", "Testing", "Documentation"]},

    # Digital business and growth roles
    "Digital Marketing Specialist": {"required": ["SEO", "SEM", "Google Analytics", "Content Marketing", "Social Media Marketing", "Email Marketing", "Reporting"]},
    "SEO Specialist": {"required": ["SEO", "Keyword Research", "Technical SEO", "Google Search Console", "Google Analytics", "Content Optimization", "Reporting"]},
    "Content Strategist": {"required": ["Content Strategy", "SEO", "Writing", "Research", "Analytics", "Editorial Planning", "Communication"]},
    "Growth Marketing Analyst": {"required": ["Google Analytics", "A/B Testing", "SQL", "Excel", "Marketing Analytics", "Conversion Optimization", "Reporting"]},
    "E-commerce Specialist": {"required": ["E-commerce", "Digital Marketing", "SEO", "Analytics", "Product Listings", "Customer Experience", "Excel"]},

    # Engineering and CAD-related technology careers
    "Mechanical CAD Designer": {"required": ["AutoCAD", "SolidWorks", "Fusion 360", "3D Modeling", "Technical Drawing", "GD&T", "Engineering Design"]},
    "CAD/CAM Engineer": {"required": ["CAD", "CAM", "CNC Programming", "Fusion 360", "SolidWorks", "Manufacturing Processes", "Technical Drawing"]},
    "Quality Assurance Engineer": {"required": ["Quality Control", "Quality Assurance", "Root Cause Analysis", "SPC", "Six Sigma", "Documentation", "Problem Solving"]},
    "Manufacturing Engineer": {"required": ["Manufacturing Processes", "CAD", "Lean Manufacturing", "Quality Control", "CNC Programming", "Process Improvement", "Technical Drawing"]},
}

def init_db():
    import sqlite3
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS analyses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, role TEXT NOT NULL, score INTEGER NOT NULL,
            found_json TEXT NOT NULL, missing_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            recommendations_json TEXT NOT NULL DEFAULT '[]',
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        con.execute("""CREATE TABLE IF NOT EXISTS roadmap_progress(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            role TEXT NOT NULL, skill TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL, UNIQUE(user_id, role, skill),
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        columns = [row[1] for row in con.execute("PRAGMA table_info(analyses)").fetchall()]
        if "recommendations_json" not in columns:
            con.execute("ALTER TABLE analyses ADD COLUMN recommendations_json TEXT NOT NULL DEFAULT '[]'")

def db():
    import sqlite3
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def normalize(text):
    return re.sub(r"[^a-z0-9+#. ]+", " ", text.lower())

SKILL_ALIASES = {
    "JavaScript": ["js", "ecmascript"], "TypeScript": ["ts"],
    "REST APIs": ["rest api", "restful api", "restful apis"],
    "Machine Learning": ["ml", "scikit-learn", "sklearn"],
    "Deep Learning": ["neural networks", "neural network"],
    "Data Structures": ["dsa"], "C++": ["cpp"], "C#": ["c sharp"],
    "SQL": ["mysql", "postgresql", "sqlite", "sql server"],
    "Power BI": ["powerbi"], "Git": ["github", "gitlab"],
    "HTML": ["html5"], "CSS": ["css3"], "Computer Vision": ["opencv"],
    "Natural Language Processing": ["nlp"],
    "Cloud Computing": ["aws", "azure", "google cloud"],
    "Quality Control": ["qc"], "Quality Assurance": ["qa"],
    "3D Modeling": ["3d modelling", "solid modeling", "solid modelling"],
}

def contains_skill(skill, text):
    haystack = " " + normalize(text) + " "
    for candidate in [skill] + SKILL_ALIASES.get(skill, []):
        needle = normalize(candidate).strip()
        if not needle: continue
        if len(needle) <= 3 and " " not in needle and "+" not in needle and "#" not in needle:
            if re.search(r"\b" + re.escape(needle) + r"\b", haystack): return True
        elif needle in haystack: return True
    return False


def extract_resume(file_storage):
    """Extract text from TXT, searchable/scanned PDF, or image resume."""
    filename = secure_filename(file_storage.filename or "")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Please upload PDF, TXT, PNG, JPG, JPEG, WEBP, BMP, TIF, or TIFF.")
    raw = file_storage.read()
    if not raw:
        raise ValueError("The uploaded file is empty.")
    if ext == "txt":
        return raw.decode("utf-8-sig", errors="ignore")
    try:
        if ext == "pdf":
            with fitz.open(stream=raw, filetype="pdf") as doc:
                if doc.page_count > 15:
                    raise ValueError("Please upload a resume PDF with 15 pages or fewer.")
                text = "\n".join(page.get_text("text") for page in doc).strip()
                if len(text) >= 30:
                    return text
                parts = []
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
                    parts.append(pytesseract.image_to_string(image))
                return "\n".join(parts).strip()
        image = Image.open(BytesIO(raw)).convert("RGB")
        return pytesseract.image_to_string(image).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError("Photo/scanned-PDF reading needs Tesseract OCR. Install it using INSTALL_OCR_WINDOWS.bat or the instructions in START_HERE.txt, then restart the website. Text PDFs and TXT files work without OCR.") from exc
    except (fitz.FileDataError, OSError) as exc:
        raise ValueError("Could not read this file. Try another PDF, TXT, or image file.") from exc


def perform_analysis(text, role):
    required = ROLES[role]["required"]
    found, missing = [], []
    for skill in required:
        item = {
            "name": skill,
            "description": ROLES[role].get("descriptions", {}).get(skill, f"Learn and practise {skill} with a small hands-on exercise.")
        }
        (found if contains_skill(skill, text) else missing).append(item)
    score = round(100 * len(found) / len(required)) if required else 0
    return score, found, missing

def recommend_careers(resume_text, limit=3):
    """Return ML-based career suggestions from the locally trained TF-IDF + Logistic Regression model."""
    if CAREER_MODEL is None or CAREER_VECTORIZER is None or len(resume_text.strip()) < 10:
        return []
    try:
        vector = CAREER_VECTORIZER.transform([resume_text])
        probabilities = CAREER_MODEL.predict_proba(vector)[0]
        ranked = sorted(zip(CAREER_MODEL.classes_, probabilities), key=lambda pair: pair[1], reverse=True)
        results = []
        for role, probability in ranked[:limit]:
            # Show confidence as a model ranking score, not as a guarantee of suitability.
            results.append({"role": str(role), "score": round(float(probability) * 100)})
        return results
    except Exception:
        app.logger.exception("Career recommendation model failed")
        return []

@app.context_processor
def inject_user():
    return {"current_user": session.get("user_name")}

@app.route("/")
def home():
    return render_template("index.html", roles=list(ROLES.keys()), roles_count=len(ROLES))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:80]
        email = request.form.get("email", "").strip().lower()[:160]
        password = request.form.get("password", "")
        if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Enter a name and a valid email address.")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return render_template("register.html")
        try:
            with db() as con:
                cur = con.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                                  (name, email, generate_password_hash(password), datetime.now().isoformat(timespec="seconds")))
                user_id = cur.lastrowid
        except Exception:
            flash("That email may already be registered. Try logging in.")
            return render_template("register.html")
        session.clear()
        session["user_id"] = user_id
        session["user_name"] = name
        flash("Account created successfully.")
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as con:
        rows = con.execute("SELECT * FROM analyses WHERE user_id=? ORDER BY id DESC LIMIT 10",
                           (session["user_id"],)).fetchall()
    analyses = [dict(r) for r in rows]
    average = round(sum(a["score"] for a in analyses) / len(analyses)) if analyses else 0
    return render_template("dashboard.html", analyses=analyses, average=average, roles_count=len(ROLES))

@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    if request.method == "GET":
        return render_template("analyze.html", roles=list(ROLES.keys()))
    role = request.form.get("job_role", "")
    file = request.files.get("resume")
    if role not in ROLES or not file or not file.filename:
        flash("Choose a career role and upload a resume.")
        return redirect(url_for("analyze"))
    try:
        resume_text = extract_resume(file)
    except Exception as exc:
        flash(str(exc) if isinstance(exc, ValueError) else "Could not read the file. Try a text-based PDF or TXT resume.")
        return redirect(url_for("analyze"))
    if len(resume_text.strip()) < 20:
        flash("Not enough readable text was found. For scanned PDFs/photos, install Tesseract OCR or try a text-based PDF/TXT resume.")
        return redirect(url_for("analyze"))
    score, found, missing = perform_analysis(resume_text, role)
    recommendations = recommend_careers(resume_text)
    created_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    with db() as con:
        cur = con.execute("INSERT INTO analyses(user_id,role,score,found_json,missing_json,created_at,recommendations_json) VALUES(?,?,?,?,?,?,?)",
                           (session["user_id"], role, score, json.dumps(found), json.dumps(missing), created_at, json.dumps(recommendations)))
        analysis_id = cur.lastrowid
    return redirect(url_for("results", analysis_id=analysis_id))

@app.route("/results/<int:analysis_id>")
@login_required
def results(analysis_id):
    with db() as con:
        row = con.execute("SELECT * FROM analyses WHERE id=? AND user_id=?",
                          (analysis_id, session["user_id"])).fetchone()
    if not row:
        flash("Analysis not found.")
        return redirect(url_for("dashboard"))
    result = dict(row)
    result["found"] = json.loads(result.pop("found_json"))
    result["missing"] = json.loads(result.pop("missing_json"))
    result["recommendations"] = json.loads(result.pop("recommendations_json", "[]"))
    return render_template("results.html", result=result)

@app.route("/roadmap")
@login_required
def roadmap():
    role = request.args.get("role", "Software Developer")
    if role not in ROLES: role = "Software Developer"
    with db() as con:
        progress_rows = con.execute("SELECT skill, completed FROM roadmap_progress WHERE user_id=? AND role=?",
                                    (session["user_id"], role)).fetchall()
        latest = con.execute("SELECT missing_json FROM analyses WHERE user_id=? AND role=? ORDER BY id DESC LIMIT 1",
                             (session["user_id"], role)).fetchone()
    completed = {r["skill"] for r in progress_rows if r["completed"]}
    missing = []
    if latest:
        try: missing = [x["name"] for x in json.loads(latest["missing_json"])]
        except (ValueError, TypeError, KeyError): pass
    skills = list(ROLES[role]["required"])
    skills.sort(key=lambda s: (s not in missing, s))
    items = []
    for i, skill in enumerate(skills, 1):
        items.append({"number": i, "skill": skill,
                      "description": ROLES[role].get("descriptions", {}).get(skill, f"Learn the fundamentals of {skill} and practise with examples."),
                      "project": f"Build a small portfolio task demonstrating {skill}.",
                      "completed": skill in completed})
    return render_template("roadmap.html", roles=list(ROLES.keys()), role=role, items=items)

@app.route("/api/progress", methods=["POST"])
@login_required
def update_progress():
    payload = request.get_json(silent=True) or {}
    role, skill = str(payload.get("role", "")), str(payload.get("skill", ""))
    done = 1 if payload.get("completed") else 0
    if role not in ROLES or skill not in ROLES[role]["required"]:
        return {"ok": False, "error": "Invalid role or skill."}, 400
    with db() as con:
        con.execute("""INSERT INTO roadmap_progress(user_id, role, skill, completed, updated_at)
            VALUES(?,?,?,?,?) ON CONFLICT(user_id, role, skill) DO UPDATE SET
            completed=excluded.completed, updated_at=excluded.updated_at""",
            (session["user_id"], role, skill, done, datetime.now().isoformat(timespec="seconds")))
    return {"ok": True, "completed": bool(done)}



# --- AI-assisted career tools (local, no paid API key required) ---
PROJECT_IDEAS = {
    "Python": ["Resume Keyword Analyzer", "Student Attendance Tracker", "Expense Tracker with CSV reports"],
    "SQL": ["College Database Dashboard", "Retail Sales Analysis", "Library Management Database"],
    "HTML": ["Responsive Portfolio Website", "College Event Landing Page", "Accessible Registration Form"],
    "JavaScript": ["Interactive Quiz App", "Task Planner with Local Storage", "Weather Dashboard using a public API"],
    "Machine Learning": ["Resume Category Classifier", "Student Performance Explorer", "Spam Text Classifier"],
    "Excel": ["Monthly Budget Dashboard", "Sales Pivot Report", "Student Marks Analysis"],
    "Power BI": ["Sales KPI Dashboard", "Attendance Analytics Dashboard", "Customer Overview Report"],
    "CAD": ["Parametric Part Model", "Exploded Assembly Drawing", "Manufacturing Drawing Portfolio"],
}
INTERVIEW_BANK = {
    "Software Developer": [("What is object-oriented programming?", "OOP organizes software around objects and classes. Its common principles are encapsulation, abstraction, inheritance and polymorphism."), ("How do you debug a program?", "Reproduce the issue, read the error, isolate the failing section, inspect values, fix the root cause and run tests again."), ("Why is version control useful?", "Version control records code changes, supports collaboration and allows developers to compare or restore earlier versions.")],
    "Data Analyst": [("What is the difference between data and information?", "Data are raw facts; information is data processed and organized to support understanding or decisions."), ("What is SQL used for?", "SQL is used to query, insert, update and manage data in relational databases."), ("What is data cleaning?", "Data cleaning identifies and handles missing values, duplicates, inconsistent formats and invalid records before analysis.")],
    "AI Engineer": [("What is overfitting?", "Overfitting happens when a model learns training examples too closely and performs poorly on unseen data."), ("Why split data into train and test sets?", "Training data fits the model; test data provides a more independent estimate of how it performs on unseen examples."), ("What is precision?", "Precision is the fraction of predicted positive cases that are actually positive: TP divided by TP plus FP.")],
    "Machine Learning Engineer": [("What is overfitting?", "Overfitting happens when a model learns training examples too closely and performs poorly on unseen data."), ("What is feature engineering?", "Feature engineering creates or transforms input variables to help a model learn useful patterns."), ("Why evaluate a model?", "Evaluation checks whether a model performs adequately on data it did not train on, using metrics suited to the task.")],
    "Mechanical CAD Designer": [("What is parametric modeling?", "Parametric modeling uses dimensions and constraints to control geometry so design changes can be made consistently."), ("What is an engineering drawing?", "It communicates a component's geometry, dimensions, tolerances, material and manufacturing requirements."), ("What is GD&T?", "Geometric Dimensioning and Tolerancing defines allowable variation in a part's geometry and feature relationships.")],
}
DEFAULT_INTERVIEW = [("Tell me about yourself.", "Give a short summary of your education, relevant skills, one genuine project and the type of role you want."), ("Describe a challenge you solved.", "Use the STAR structure: Situation, Task, Action and Result. Be specific and truthful about your own contribution."), ("Why should we hire you?", "Connect two or three relevant skills to the role, support them with examples, and explain how you learn and collaborate.")]

def _role_skills(role):
    return ROLES.get(role, ROLES["Software Developer"]).get("required", [])

def _latest_analysis():
    with db() as con:
        row=con.execute("SELECT * FROM analyses WHERE user_id=? ORDER BY id DESC LIMIT 1", (session["user_id"],)).fetchone()
    return dict(row) if row else None

@app.route("/ai-tools")
@login_required
def career_tools():
    return render_template("ai_tools.html", roles=list(ROLES.keys()))

@app.route("/career-chat", methods=["GET", "POST"])
@login_required
def career_chat():
    answer = None
    question = ""
    if request.method == "POST":
        question = (request.form.get("question") or "").strip()[:1000]
        q = question.lower()
        if any(w in q for w in ["roadmap", "plan", "start", "begin"]):
            latest = _latest_analysis()
            if latest:
                missing = [x.get("name", "") for x in json.loads(latest.get("missing_json", "[]"))]
                answer = f"Your latest target role is {latest['role']}. Start with these skills not detected in your resume: {', '.join(missing[:5]) or 'review and practise the role skills'} . Open Roadmap to follow the checklist."
            else:
                answer = "Start by choosing one target role, upload a readable resume in Analyze, then follow the missing-skill checklist in Roadmap."
        elif any(w in q for w in ["resume", "cv", "profile"]):
            answer = "For a stronger resume, use clear headings, measurable results, relevant skills and 2–3 projects. Keep every claim truthful. Upload a text PDF/TXT or a clear photo with OCR configured for analysis."
        elif any(w in q for w in ["interview", "question"]):
            answer = "Open AI Tools → Interview Practice. Practise aloud, structure examples with STAR (Situation, Task, Action, Result), and tailor each answer to the target role."
        elif any(w in q for w in ["project", "portfolio"]):
            answer = "Open AI Tools → Project Ideas. Pick a project that uses a missing skill, finish a small working version, document setup and results, and publish the code only when it contains no secrets."
        elif any(w in q for w in ["skill", "career", "job", "role"]):
            answer = "Choose a target role and compare its skill checklist with your resume. Treat the match score as a rough text-based estimate, not a hiring probability. Build evidence for missing skills through practice projects."
        else:
            answer = "I can help with resume improvement, skill gaps, career roadmaps, interview practice and project ideas. Ask about one of these topics for a more useful suggestion. This local assistant uses guided rules, not a hosted general-purpose LLM."
    return render_template("career_chat.html", question=question, answer=answer)

@app.route("/interview-practice", methods=["GET", "POST"])
@login_required
def interview_practice():
    role = request.values.get("role", "Software Developer")
    if role not in ROLES: role = "Software Developer"
    questions = INTERVIEW_BANK.get(role, DEFAULT_INTERVIEW)
    if request.method == "POST":
        # Keep the chosen role and display a model answer as a study guide.
        q_index = request.form.get("q_index", "0")
        try: idx = max(0, min(int(q_index), len(questions)-1))
        except ValueError: idx = 0
        return render_template("interview_practice.html", roles=list(ROLES.keys()), role=role, questions=questions, selected=idx, sample_answer=questions[idx][1])
    return render_template("interview_practice.html", roles=list(ROLES.keys()), role=role, questions=questions, selected=None, sample_answer=None)

@app.route("/resume-improve", methods=["GET", "POST"])
@login_required
def resume_improve():
    result = None
    if request.method == "POST":
        summary = (request.form.get("summary") or "").strip()[:3000]
        skills_text = (request.form.get("skills") or "").strip()[:2000]
        role = request.form.get("role", "Software Developer")
        if role not in ROLES: role = "Software Developer"
        present = [s for s in _role_skills(role) if contains_skill(s, skills_text + " " + summary)]
        missing = [s for s in _role_skills(role) if s not in present]
        suggestions = []
        if len(summary.split()) < 20:
            suggestions.append("Expand your summary to 2–4 concise sentences describing your education, strongest relevant skills and target role.")
        if not re.search(r"\d+|%|increased|reduced|built|designed|developed|analysed|analyzed|implemented", summary, re.I):
            suggestions.append("Where truthful, add measurable evidence: users served, time saved, accuracy, cost, dimensions or project results.")
        if not skills_text:
            suggestions.append("Add a short skills section containing only tools and skills you can discuss confidently.")
        if not present:
            suggestions.append("No role-specific skills were detected in the text you entered. Add relevant skills only if you genuinely have them.")
        result = {"role":role,"present":present,"missing":missing,"suggestions":suggestions,"summary":summary}
    return render_template("resume_improve.html", roles=list(ROLES.keys()), result=result)

@app.route("/project-ideas", methods=["GET", "POST"])
@login_required
def project_ideas():
    role = request.values.get("role", "Software Developer")
    if role not in ROLES: role = "Software Developer"
    latest = _latest_analysis()
    missing = [x.get("name", "") for x in json.loads(latest.get("missing_json", "[]"))] if latest else []
    skill_pool = missing or _role_skills(role)
    ideas = []
    for skill in skill_pool:
        for key, values in PROJECT_IDEAS.items():
            if key.lower() in skill.lower() or skill.lower() in key.lower():
                ideas.extend([{"skill":skill,"title":v,"level":"Beginner–Intermediate","steps":["Define the problem and requirements", "Build a small working version", "Test with sample data", "Write a README with screenshots and limitations"]} for v in values[:1]])
    if not ideas:
        ideas = [{"skill":s,"title":f"{s} Practice Portfolio Project","level":"Beginner–Intermediate","steps":["Define a real use case", "Build a small working version", "Test with sample data", "Document results and limitations"]} for s in skill_pool[:5]]
    return render_template("project_ideas.html", roles=list(ROLES.keys()), role=role, ideas=ideas[:8])

@app.route("/progress")
@login_required
def learning_progress():
    with db() as con:
        completed = con.execute("SELECT COUNT(*) AS n FROM roadmap_progress WHERE user_id=? AND completed=1", (session["user_id"],)).fetchone()["n"]
        total = con.execute("SELECT COUNT(*) AS n FROM roadmap_progress WHERE user_id=?", (session["user_id"],)).fetchone()["n"]
        analyses = con.execute("SELECT COUNT(*) AS n FROM analyses WHERE user_id=?", (session["user_id"],)).fetchone()["n"]
        roles_done = con.execute("SELECT COUNT(DISTINCT role) AS n FROM roadmap_progress WHERE user_id=? AND completed=1", (session["user_id"],)).fetchone()["n"]
    pct = round(completed * 100 / total) if total else 0
    return render_template("progress.html", completed=completed, total=total, pct=pct, analyses=analyses, roles_done=roles_done)

@app.errorhandler(413)
def too_large(_error):
    flash("File is too large. Maximum upload size is 5 MB.")
    return redirect(url_for("analyze"))

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
