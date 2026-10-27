# Dataset Documentation & Source Attribution

## 1. Primary Dataset Overview
* **Name:** Finger Tapping Parkinsonisms Database
* **Original Research Publication:**
  * **Title:** *"Objective assessment of finger-tapping kinematics in parkinsonian syndromes using wearable miniature gyroscopes"*
  * **Journal:** *Heliyon*, Volume 9, Issue 4, April 2023, e14824.
  * **DOI:** [10.1016/j.heliyon.2023.e14824](https://doi.org/10.1016/j.heliyon.2023.e14824)
* **Open Source Repository:** [https://github.com/innovation-center-etf/FINGER-TAPPING-PARKINSONISMS-DATABASE](https://github.com/innovation-center-etf/FINGER-TAPPING-PARKINSONISMS-DATABASE)
* **Institution:** Innovation Center, School of Electrical Engineering (ETF), University of Belgrade, Serbia.

---

## 2. Sensor Configuration & Acquisition Protocol
* **Sensor Type:** Dual miniature triaxial gyroscopes.
* **Placement:**
  * Sensor 1: Proximal phalanx of the thumb.
  * Sensor 2: Distal phalanx of the index finger.
* **Channels Recorded:**
  1. `gyroThumbX` (Thumb flexion / extension)
  2. `gyroThumbY` (Thumb abduction / adduction — primary tapping axis)
  3. `gyroThumbZ` (Thumb axial rotation)
  4. `gyroIndexX` (Index flexion / extension)
  5. `gyroIndexY` (Index tapping excursion — primary tapping axis)
  6. `gyroIndexZ` (Index lateral drift)
* **Sampling Frequency:** $200\text{ Hz}$ continuous acquisition.
* **Task Duration:** $15$ to $30$ seconds of repetitive, maximum-amplitude finger tapping per trial.

---

## 3. Verified Class Distribution & Participant Cohort
The authentic dataset directory contains $268$ total MATLAB `.mat` files across four clinical groups:

| Diagnosis Category | Abbreviation | Total Recordings | Independent Participants | Clinical Description |
| :--- | :--- | :--- | :--- | :--- |
| **Multiple System Atrophy** | **MSA** | **72** | **13** | Atypical parkinsonism (Predominantly MSA-P) |
| **Parkinson's Disease** | **PD** | **68** | **14** | Idiopathic Parkinson's disease cohort |
| **Progressive Supranuclear Palsy** | **PSP** | 76 | 16 | Tauopathy movement disorder (reference cohort) |
| **Healthy Controls** | **CTRL** | 52 | 11 | Age-matched neurological controls |

### Primary Research Task: MSA vs. PD
* Total evaluated recordings: **140**
* Total independent subjects: **27**
* Average recordings per subject: **5.1 trials**

---

## 4. Critical Scientific & Clinical Caveats
1. **Subtype Homogeneity (MSA-P Predominance):**
   The MSA cohort in this dataset comprises patients diagnosed with the parkinsonian subtype (MSA-P). The cerebellar subtype (MSA-C) is not separately differentiated in the repository. Findings must not be assumed to generalize across cerebellar-variant MSA.
2. **Independent Subject Isolation:**
   Because each participant performed multiple consecutive trials, evaluating models via simple random train/test splits across recordings introduces severe patient-identity data leakage (artificially inflating test accuracy up to 95%+). NeuroScope enforces **5-Fold Stratified Group Cross-Validation** by `person_id` to ensure truthful generalizability.
3. **Academic Research Use Only:**
   This dataset and resulting models are intended exclusively for academic, educational, and computational explainability research. They are not approved for clinical diagnostic workflows.

---

## 5. Secondary Full-Stack Attribution
* **Full-Stack Reference:** [https://github.com/AbderrezzakMrch/Parkinson-s-Disease-Voice-Detector](https://github.com/AbderrezzakMrch/Parkinson-s-Disease-Voice-Detector) (MIT License, AbderrezzakMrch).
* **Architecture Reused:** FastAPI route structure and React/Tailwind frontend concepts.
* **Preserved Audio Module:** Reused acoustic dysphonia model (`best_pd_voice_model.pkl`) is preserved as a separate experimental demonstration of PD vs. Healthy voice detection.
