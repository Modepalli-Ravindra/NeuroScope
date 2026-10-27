# NeuroScope: Explainable AI-Based Differential Screening of Multiple System Atrophy and Parkinson's Disease

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF.svg)](https://vitejs.dev)
[![SHAP](https://img.shields.io/badge/Explainability-TreeSHAP-brightgreen.svg)](https://github.com/shap/shap)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An academic research prototype and educational software platform designed for the **differential screening of Multiple System Atrophy (MSA-P) and Parkinson's Disease (PD)** using continuous $200\text{ Hz}$ 6-axis gyroscope finger-tapping kinematic signals. Built as a B.Tech Computer Science / AI & ML mini-project.

> **Academic Medical Disclaimer:** This software is strictly an educational research prototype. It is NOT approved as a medical device and must never be utilized for clinical diagnosis or prescription of therapy.

---

## 1. Clinical Problem & Motivation

Multiple System Atrophy (particularly the parkinsonian subtype, **MSA-P**) and idiopathic **Parkinson's Disease (PD)** share severe symptomatic overlap in early disease stages—including bradykinesia, rigidity, and postural instability. Despite their clinical resemblance, MSA is a rapidly progressive atypical parkinsonism with poor response to levodopa and a severe prognosis.

Autopsy-confirmed clinical studies demonstrate that up to **15–20% of early-stage MSA cases are initially misdiagnosed as Parkinson's disease**. NeuroScope addresses this dilemma by extracting subtle, objective biomechanical biomarkers from miniature gyroscopes placed on the thumb and index finger during repetitive tapping.

---

## 2. Key Features

* **Authentic Sensor Dataset Integration:**
  * Uses real movement sensor data from the University of Belgrade Finger Tapping Parkinsonisms Database (*Heliyon* 2023).
  * Direct parsing of MATLAB `.mat` files containing $200\text{ Hz}$ continuous rotational velocity.
* **45 Compact, Reproducible Kinematic Features:**
  * **Tapping Cadence:** Tap rate ($\text{Hz}$), total tap count.
  * **Rhythmicity & Hesitation:** Coefficient of variation of inter-tap intervals (`tap_interval_cv`).
  * **Motor Fatigue & Decrement:** Sequential amplitude decay slope (`tap_amplitude_decay`).
  * **Smoothness & Kinetic Energy:** Angular jerk RMS (abruptness), relative finger separation RMS.
  * **Spectral Properties:** Welch power spectral density, tapping band energy ratio ($0.5 - 5\text{ Hz}$), and spectral entropy.
* **Leakage-Free Subject-Wise Evaluation:**
  * Strict **5-Fold Stratified Group K-Fold** cross-validation on participant IDs.
  * Ensures zero data leakage between training and testing partitions.
* **Native TreeSHAP Explainability:**
  * Deconstructs Random Forest predictions into local additive feature attributions.
  * Visualizes top positive features pushing toward MSA vs. negative features pushing toward PD.
  * Ranks global feature importance across all 140 recordings in the database.
* **Calibrated Uncertainty Reporting:**
  * Automatically flags predictions as uncertain if model probabilities fall in the $45\% - 55\%$ decision boundary or if sensor recording duration is under 4 seconds.
* **Executive PDF Report Export:**
  * One-click generation of professional research reports using ReportLab, containing patient metadata, predictions, kinematics, SHAP evidence, and research caveats.
* **Full SQLite Persistence:**
  * Historical trials stored locally in SQLite (`neuroscope.db`) for tracking, auditing, and deletion.
* **Reused Experimental Voice Module:**
  * Preserved from the reused full-stack open-source reference (AbderrezzakMrch, MIT License) as a separate multimodal demonstration of vocal dysphonia in PD.

---

## 3. Technology Stack

* **Frontend:** React 19, Vite, TypeScript, Tailwind CSS, Lucide Icons, Recharts (responsive analytics).
  * Designed in an ultra-modern dark teal palette (`#030f11` background, `#004741` Cyprus green accents, `#F0EDE4` sand typography).
* **Backend:** FastAPI, Python 3.12+, Uvicorn.
* **Machine Learning:** NumPy, SciPy (Welch PSD, peak finding), Pandas, scikit-learn (RandomForest, KNN, LogisticRegression), SHAP (TreeExplainer), Joblib.
* **Database:** SQLite via SQLAlchemy.
* **Reporting:** ReportLab PDF Generation engine.

---

## 4. Directory Structure

```
NeuroScope/
├── data/
│   └── raw/
│       ├── MSA/                   # 72 authentic MSA .mat recordings
│       ├── PD/                    # 68 authentic PD .mat recordings
│       ├── CTRL/                  # 52 healthy control recordings
│       └── PSP/                   # 76 PSP recordings
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── database.py            # SQLite connection
│   │   ├── models_db.py           # SQLAlchemy history schema
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── analysis.py        # POST /api/analyze & /api/explain
│   │   │   ├── dataset.py         # GET /api/dataset/info & /api/samples
│   │   │   ├── models.py          # GET /api/model/info & /api/model/evaluation
│   │   │   ├── reports.py         # GET /api/history & PDF generation
│   │   │   └── voice.py           # Experimental voice route
│   │   └── utils/
│   │       └── pdf_generator.py   # ReportLab PDF generator
│   ├── ml/
│   │   ├── feature_extractor.py   # 6-channel kinematic extractor
│   │   ├── dataset_loader.py      # MAT parsing & batch feature extraction
│   │   ├── train_models.py        # Subject-wise CV & model trainer
│   │   └── inference.py           # Runtime InferenceEngine + SHAP
│   └── saved_models/
│       ├── neuroscope_rf_model.joblib
│       ├── neuroscope_knn_model.joblib
│       ├── feature_schema.json
│       ├── evaluation_results.json
│       └── dataset_summary.json
├── frontend/
│   ├── src/
│   │   ├── components/Navbar.tsx
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── AnalysisPage.tsx
│   │   │   ├── ShapExplorerPage.tsx
│   │   │   ├── EvaluationPage.tsx
│   │   │   ├── ReportsPage.tsx
│   │   │   └── VoiceLabPage.tsx
│   │   ├── api.ts
│   │   ├── types.ts
│   │   ├── index.css
│   │   └── App.tsx
│   └── package.json
├── tests/
│   └── test_backend.py            # Automated test suite
├── run.bat                        # Windows 1-click launcher
├── start.ps1                      # PowerShell launcher
├── requirements.txt               # Backend dependencies
├── MODEL_CARD.md                  # Comprehensive ML model specifications
├── DATASET_SOURCES.md             # Dataset documentation & attribution
└── README.md
```

---

## 5. Quickstart & Installation (Windows)

### Prerequisites
* **Python 3.12 or 3.13** installed and added to PATH.
* **Node.js (v18+) & npm** installed.

### Option A: One-Click Windows Launcher (Recommended)
Simply double-click:
```cmd
run.bat
```
or in PowerShell:
```powershell
.\start.ps1
```
This automatically verifies dependencies, checks for trained model artifacts, and launches both the backend (`http://127.0.0.1:8000`) and the frontend dashboard (`http://127.0.0.1:5173`).

---

### Option B: Manual Step-by-Step Launch

#### 1. Install Backend Dependencies & Train Artifacts
```bash
python -m pip install -r requirements.txt
python -m backend.ml.train_models
```

#### 2. Run Backend API Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
API Documentation will be live at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

#### 3. Run Frontend Dev Server
In a separate terminal:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Open your browser at: [http://127.0.0.1:5173](http://127.0.0.1:5173).

---

## 6. Running Automated Tests

Run the backend integration test suite to verify endpoints, model inference, SHAP calculations, and PDF generation:
```bash
python -m tests.test_backend
```

---

## 7. Model Performance & Validation Summary

Evaluated on 140 recordings from 27 independent participants using 5-Fold Stratified Group Cross-Validation (zero subject leakage):

| Architecture | Balanced Accuracy | Sensitivity (MSA) | Specificity (PD) | ROC-AUC | F1-Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Random Forest (Primary)** | **72.8%** | **73.6%** | **72.1%** | **0.767** | **0.728** |
| **KNN Baseline** | 68.9% | 83.3% | 54.4% | 0.798 | 0.693 |
| **Logistic Regression** | 74.3% | 72.2% | 76.5% | 0.792 | 0.743 |

*For complete details, see [MODEL_CARD.md](MODEL_CARD.md).*

---

## 8. Citations & Attribution

1. **Finger Tapping Dataset:**
   * Innovation Center, School of Electrical Engineering (ETF), University of Belgrade.
   * *Heliyon*, 9(4): e14824 (2023). DOI: [10.1016/j.heliyon.2023.e14824](https://doi.org/10.1016/j.heliyon.2023.e14824).
   * GitHub: `innovation-center-etf/FINGER-TAPPING-PARKINSONISMS-DATABASE`.
2. **Reused Reference Architecture:**
   * AbderrezzakMrch: `Parkinson-s-Disease-Voice-Detector` (MIT License).
3. **SHAP (SHapley Additive exPlanations):**
   * Lundberg, S. M., & Lee, S. I. (2017). A unified approach to interpreting model predictions. *NeurIPS 2017*.

---

## 9. License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
