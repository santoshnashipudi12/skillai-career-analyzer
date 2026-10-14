"""Train the local career recommendation model.

Training data is generated from the app's curated role-skill catalogue using
skill subsets and wording variations. This is a transparent educational model,
not a model trained on real resumes or hiring outcomes.
"""
import os, pickle, random, re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from app import ROLES

random.seed(20261011)
ALIASES = {
    "JavaScript": ["JS", "browser scripting", "frontend scripting"],
    "Python": ["Python programming", "scripting with Python"],
    "SQL": ["relational database queries", "SQL querying"],
    "Machine Learning": ["ML", "predictive modeling", "machine learning projects"],
    "HTML": ["HTML5", "web markup"],
    "CSS": ["CSS3", "web styling"],
    "React": ["React.js", "React frontend"],
    "Networking": ["computer networks", "network administration"],
    "Linux": ["Linux administration", "Linux command line"],
    "Cloud Computing": ["cloud platforms", "cloud infrastructure"],
    "AutoCAD": ["AutoCAD drafting", "2D CAD"],
    "SolidWorks": ["SolidWorks CAD", "3D mechanical CAD"],
    "Fusion 360": ["Autodesk Fusion 360", "Fusion CAD/CAM"],
    "Power BI": ["PowerBI dashboards", "business intelligence dashboards"],
    "Excel": ["Microsoft Excel", "spreadsheet analysis"],
    "Cybersecurity": ["security operations", "information security"],
}
GENERIC = ["project work", "hands-on practice", "technical problem solving", "team collaboration", "documentation", "learning and implementation"]
texts, labels = [], []
for role, info in ROLES.items():
    skills = info["required"]
    # Many variations per role teach the model to recognize combinations rather than one fixed phrase.
    for _ in range(100):
        k = random.randint(max(2, min(3, len(skills))), len(skills))
        chosen = random.sample(skills, min(k, len(skills)))
        phrases = []
        for skill in chosen:
            phrases.append(skill)
            if skill in ALIASES and random.random() < 0.65:
                phrases.append(random.choice(ALIASES[skill]))
        phrases.extend(random.sample(GENERIC, random.randint(1, 3)))
        random.shuffle(phrases)
        texts.append(" ".join(phrases))
        labels.append(role)

vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True, min_df=1, max_features=30000)
X = vectorizer.fit_transform(texts)
model = LogisticRegression(max_iter=1200, class_weight="balanced", C=3.0, random_state=2026)
model.fit(X, labels)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "career_model.pkl")
with open(path, "wb") as f:
    pickle.dump({"vectorizer": vectorizer, "model": model, "metadata": {
        "model_type": "TF-IDF + Logistic Regression",
        "roles": len(ROLES), "synthetic_training_examples": len(texts),
        "training_data_note": "Synthetic skill combinations generated from the curated role catalogue; not real resumes."
    }}, f, protocol=pickle.HIGHEST_PROTOCOL)
print(f"Saved {path}; trained on {len(texts)} generated examples across {len(ROLES)} roles.")
