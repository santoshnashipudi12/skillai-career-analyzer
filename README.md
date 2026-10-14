# AI-Based Skill Gap Analyzer and Personalized Career Roadmap System

A mobile-friendly Flask web application for an educational project. Users can register, log in, upload a PDF/TXT resume, select a career role, review detected and missing skills, and view a suggested learning roadmap.

## Features
- Registration and login
- Resume upload (PDF/TXT, max 5 MB)
- Skill matching across 50+ career paths spanning software, web/mobile, data/AI, cloud/DevOps, cybersecurity, design/product, digital marketing, and CAD/manufacturing technology
- Match percentage, detected skills, missing skills, and suggested learning steps
- Dashboard and analysis history
- Responsive mobile-first interface

## Machine-learning model and limitations
The app includes a locally trained **TF-IDF + Logistic Regression** classifier that ranks career paths from resume text. `train_model.py` creates and trains the model, and `career_model.pkl` is the saved trained artifact. The training examples are generated from the curated role-skill catalogue; they are **synthetic skill-profile examples, not real resumes**. The selected-role skill checklist still uses keyword matching. Model scores are ranking signals, not calibrated probabilities, job-readiness scores, or hiring predictions. This is an educational prototype and needs evaluation on representative, consented real-world data before production use. Review its suggestions before making career decisions.

## Publish online using Render (phone-friendly steps)

You can do this from Android Chrome. You do not need to write code.

### 1. Download and extract
1. Download the ZIP file.
2. Open your phone's Files app and extract `AI_Skill_Gap_Analyzer_Full.zip`.
3. Inside the extracted folder, open `AI_Skill_Gap_Analyzer_Full`. It contains `app.py`, `requirements.txt`, `templates`, `static`, `Procfile`, and `render.yaml`.

### 2. Upload the project to GitHub
1. Sign in to GitHub and create a new repository named `ai-skill-gap-analyzer`.
2. In the repository, use **Add file → Upload files** (the wording may differ on mobile).
3. Upload the *contents* of the `AI_Skill_Gap_Analyzer_Full` folder, not the outer folder itself.
4. Commit the files to the repository. Make sure `app.py`, `requirements.txt`, `render.yaml`, `Procfile`, `templates/`, and `static/` are at the repository root.

### 3. Deploy on Render
1. Sign in to Render and choose **New → Web Service**.
2. Connect GitHub and select `ai-skill-gap-analyzer`.
3. If Render asks for settings, use:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
4. Deploy the service and wait for the build to finish.
5. Open the `onrender.com` URL Render gives you.

The included `render.yaml` configures the build/start commands and generates a `FLASK_SECRET_KEY` environment variable automatically when Render supports Blueprint configuration.

### 4. Model retraining (optional)
If the career catalogue is changed, retrain the bundled model in a Python environment with dependencies installed:
```bash
python train_model.py
```
The resulting `career_model.pkl` must be committed with the app.

### 5. Local testing (optional)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Data and privacy notes
- This demo stores account and analysis data in a local SQLite database.
- On hosting platforms with an ephemeral filesystem, data may reset when the service restarts or redeploys. For a real public service, configure persistent storage or a managed database before relying on saved accounts/history.
- Do not upload sensitive personal documents to a public demo. Resume files may contain private information.
- Use HTTPS and keep `FLASK_SECRET_KEY` configured for public deployment.


## Career catalogue
The prototype includes 50+ predefined roles across technology and adjacent digital/engineering careers. This is a broad starter catalogue, not literally every occupation in the labour market. Role skill lists are editable in the `ROLES` dictionary in `app.py`.


## All-updates build
Adds OCR fallback for scanned PDFs and image resumes, common skill aliases, personalized roadmap ordering, and account-based roadmap progress. Python OCR packages are installed from `requirements.txt`; Tesseract itself is a separate system dependency. Windows installation details are in `START_HERE.txt`; Render uses `apt.txt`.


### Scanned PDF and photo resume support (Windows)
Run `INSTALL_OCR_WINDOWS.bat` with an internet connection, or install Tesseract from the official UB Mannheim page: https://github.com/UB-Mannheim/tesseract/wiki. Restart the app after installation. Text PDFs and TXT files work without OCR.


## Added career tools
- **AI Tools hub** at `/ai-tools` (login required).
- **Career chat**: guided, local rule-based advice for resume, roadmap, skills, interviews and projects. It is not a hosted LLM chatbot.
- **Interview practice**: role-based question bank and sample study answers.
- **Resume improvement**: text/skills checklist and honest-content suggestions.
- **Project ideas**: portfolio task suggestions, prioritizing detected missing skills where possible.
- **Learning progress**: summary of saved roadmap checklist activity and analysis history.

The existing TF-IDF + Logistic Regression classifier remains responsible for resume-based career ranking when its model file is present. The other tools are deterministic local helpers and do not require an API key. All outputs are guidance; review for correctness and never invent resume experience.
