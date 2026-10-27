# NeuroScope: Academic Project Demonstration & Viva Guide

**Project:** NeuroScope — Explainable AI-Based Differential Screening of Multiple System Atrophy and Parkinson's Disease  
**Target Audience:** Academic Evaluators, University Project Reviewers, External Examiners  

---

## 1. Quick Demonstration Steps (5-Minute Live Walkthrough)

### Step 1: Launch System
Double-click `run.bat` (or in PowerShell execute `.\start.ps1`).  
Verify both servers are running:
* **Frontend:** [http://127.0.0.1:5173](http://127.0.0.1:5173)
* **Backend:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Top navbar displays **"200 Hz ML Engine Online"** with glowing emerald badge.

### Step 2: Show Dataset & Cohort Profile (Tab: "Dataset & Cohort")
* Explain that the project uses **real clinical movement sensors**, not synthetic data.
* Point to the $140$ evaluated recordings across $27$ independent participants ($13$ MSA, $14$ PD) from University of Belgrade (*Heliyon* 2023).
* Highlight the study limitation banner: predominantly **MSA-P** subtype.

### Step 3: Execute Differential Screening (Tab: "Differential Screening")
* **Test Example 1 (MSA):** Select **Kinematic Recording A (`Subj-M23-T1`)** from the authentic dropdown.
  * Click **"Run Differential Screening"**.
  * Show the interactive **200 Hz gyroscope waveform** (Flexion Y, Abduction Y, Adduction X).
  * Show the primary result: **Multiple System Atrophy (MSA)** with $87.2\%$ confidence score.
  * Show the dual model verification: Logistic Regression also predicts MSA ($89.1\%$).
  * Show the extracted kinematics: Tap rate ($2.86\text{ Hz}$), Rhythm CV ($0.082$), Decay slope ($-0.134$).
* **Test Example 2 (PD):** Select **Kinematic Recording D (`Subj-P13-T1`)**.
  * Click **"Run Differential Screening"**.
  * Show the result: **Parkinson's Disease (PD)** with $96.5\%$ confidence score.
  * Show the negative SHAP bars pushing towards PD.

### Step 4: TreeSHAP Interpretability (Tab: "SHAP Explorer")
* Explain that the prediction is completely transparent.
* Point out the local bar chart: features with green bars pushed the decision toward MSA; cyan bars pushed toward PD.
* Show the global importance ranking: `gyroThumbZ_rms`, `gyroThumbX_p2p`, and `tap_amplitude_decay` are the top 3 distinguishing biomarkers.

### Step 5: Leakage-Safe Model Validation (Tab: "Model Validation")
* Emphasize **Subject-Wise Group K-Fold**: no patient appears in both train and test.
* Show the **Confusion Matrix**: Random Forest achieves **72.8% Balanced Accuracy** and **0.767 ROC-AUC**.
* Explain why Logistic Regression achieves **74.4% Balanced Accuracy** (linear regularization has lower variance on 27 patients).

### Step 6: PDF Report & Persistent History (Tab: "Research Reports")
* Show the SQLite history table recording every completed trial.
* Click **"PDF"** to instantly generate and download the executive research report with patient metadata, kinematics, SHAP evidence, and academic disclaimers.

### Step 7: Voice Lab Scientific Isolation (Tab: "Voice Lab")
* Explain why this reused audio module is kept strictly separate: vocal dysphonia differentiates PD from healthy controls, but cannot differentiate MSA from PD.

---

## 2. Top 10 Viva Questions & Expert Answers

### Q1: Why is differentiating MSA from Parkinson's disease clinically difficult?
**Answer:** Both diseases involve basal ganglia dopaminergic deficits presenting with bradykinesia, rigidity, and tremors. In early stages, clinical misdiagnosis rates reach 15–20%. However, MSA progresses much more aggressively and does not respond sustainably to levodopa, making early differential screening crucial for prognosis.

### Q2: Why did you use 6-axis gyroscopes instead of voice or webcam video?
**Answer:** Gyroscopes directly capture continuous angular velocity ($200\text{ Hz}$) on both the thumb and index finger. This enables sub-millisecond measurement of rotational jerk, micro-hesitations, and amplitude fatigue decrement—biomechanical properties that video frame rates ($30\text{ Hz}$) cannot reliably measure.

### Q3: What is "subject-level data leakage," and how did you prevent it?
**Answer:** Each patient performed 5 to 7 tapping trials. If recordings are split randomly, trials from the same patient land in both training and test sets. The model would then memorize individual patient movement habits (reporting fake 95%+ accuracies). We prevented this by using `StratifiedGroupKFold` grouped strictly by `person_id`, ensuring completely unseen patients in the test folds.

### Q4: Why did Logistic Regression achieve 74.4% balanced accuracy while Random Forest achieved 72.8%?
**Answer:** Our dataset has 27 independent patients and 45 features. With small patient cohorts, high-dimensional non-linear decision trees have higher hypothesis variance and risk overfitting inter-subject noise. $L_2$-regularized Logistic Regression constrains hypothesis variance, yielding slightly higher stability and lower Brier calibration loss (0.190 vs 0.203).

### Q5: What is TreeSHAP and how does it mathematically explain the model?
**Answer:** TreeSHAP calculates exact Shapley values from cooperative game theory across tree paths in polynomial time. For any prediction, the sum of all 45 feature SHAP values plus the base expected value ($0.512$) exactly reconstructs the model output probability with machine-precision accuracy ($10^{-16}$).

### Q6: What does the feature `tap_amplitude_decay` signify biologically?
**Answer:** It measures the slope of peak tapping amplitude over time. A negative decay slope indicates progressive amplitude decrement (hypometria and motor sequence breakdown), which is a classic clinical neuro-cardinal sign of Parkinsonian fatigue.

### Q7: Why do you flag predictions between 45% and 55% as uncertain?
**Answer:** A model score near 50% indicates that feature evidence between MSA and PD is balanced and the model lacks decisive margin separation. Rather than forcing a clinical diagnosis, the system transparently reports an "Uncertain / Low Separation" state.

### Q8: What are the main clinical limitations of your model?
**Answer:** First, the cohort has 27 independent subjects, which is appropriate for a mini-project prototype but requires multi-center expansion for clinical trials. Second, the MSA cohort is predominantly MSA-P (parkinsonian subtype); the model cannot be assumed to generalize to MSA-C (cerebellar subtype).

### Q9: Does SHAP prove medical causation?
**Answer:** No. SHAP reveals statistical feature attribution—how the trained machine learning model arrived at its numerical score. It reflects correlation in sensor kinematics, not anatomical causation or cellular pathology.

### Q10: How does the architecture maintain security and prevent arbitrary code execution?
**Answer:** The application uses pre-trained, version-controlled model artifacts. Incoming uploads are checked for file extension (`.mat`), channel presence, duration, and a 25 MB size limit. No serialized pickle objects from users are ever executed dynamically.
