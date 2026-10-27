import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil
from backend.ml.inference import InferenceEngine

desktop_dir = r"C:\Users\user\OneDrive\Desktop\demo_test_samples"
engine = InferenceEngine.get_instance()

pd_list = [
    "data/raw/PD/PDBS13_1.mat",
    "data/raw/PD/PDBS13_2.mat",
    "data/raw/PD/PDBS13_3.mat",
    "data/raw/PD/PDBS13_4.mat",
    "data/raw/PD/PDBS13_6.mat",
    "data/raw/PD/PDGA04_1.mat",
    "data/raw/PD/PDGA04_2.mat",
    "data/raw/PD/PDGA04_3.mat",
    "data/raw/PD/PDGA04_4.mat",
    "data/raw/PD/PDGA04_5.mat"
]

msa_list = [
    "data/raw/MSA/MSABM23_1.mat",
    "data/raw/MSA/MSABM23_3.mat",
    "data/raw/MSA/MSABM23_5.mat",
    "data/raw/MSA/MSABM23_6.mat",
    "data/raw/MSA/MSADJV1_1.mat",
    "data/raw/MSA/MSADJV1_2.mat",
    "data/raw/MSA/MSADJV1_3.mat",
    "data/raw/MSA/MSADJV1_4.mat",
    "data/raw/MSA/MSADJV1_5.mat",
    "data/raw/MSA/MSAGS04_1.mat"
]

os.makedirs(desktop_dir, exist_ok=True)

# Clean existing items safely
for item in os.listdir(desktop_dir):
    item_path = os.path.join(desktop_dir, item)
    try:
        if os.path.isdir(item_path):
            shutil.rmtree(item_path, ignore_errors=True)
        elif os.path.isfile(item_path):
            os.remove(item_path)
    except Exception:
        pass

# Interleave PD and MSA
combined_pairs = []
for i in range(10):
    combined_pairs.append(("PD", pd_list[i]))
    combined_pairs.append(("MSA", msa_list[i]))

results = []
for idx, (diag, src_path) in enumerate(combined_pairs, start=1):
    new_name = f"sample_{idx:02d}.mat"
    dst_path = os.path.join(desktop_dir, new_name)
    shutil.copy(src_path, dst_path)
    
    with open(dst_path, "rb") as fp:
        parsed = engine.parse_mat_bytes(fp.read(), new_name)
        res = engine.predict(parsed)
        p = res["prediction"]
        results.append({
            "sample": new_name,
            "original": os.path.basename(src_path),
            "true_class": diag,
            "pred_class": p["predicted_class"],
            "confidence": p["confidence_score"],
            "prob_pd": p["probabilities"]["PD"],
            "prob_msa": p["probabilities"]["MSA"]
        })

print(f"Successfully saved 20 blind samples to: {desktop_dir}\n")
header = f"| {'Sample Name':<13} | {'Prediction':<10} | {'Confidence':<10} | {'Prob (PD)':<10} | {'Prob (MSA)':<10} | {'Original Source':<15} |"
print(header)
print("|" + "-"*15 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*17 + "|")
for r in results:
    line = f"| {r['sample']:<13} | {r['pred_class']:<10} | {r['confidence']*100:>8.1f}% | {r['prob_pd']*100:>8.1f}% | {r['prob_msa']*100:>8.1f}% | {r['original']:<15} |"
    print(line)

key_path = os.path.join(desktop_dir, "SAMPLES_CHEAT_SHEET.txt")
with open(key_path, "w", encoding="utf-8") as f:
    f.write("NEUROSCOPE - 20 BLIND TEST SAMPLES CHEAT SHEET\n")
    f.write("="*65 + "\n\n")
    for r in results:
        f.write(f"{r['sample']} -> {r['pred_class']} ({r['confidence']*100:.1f}%) [Source: {r['original']}]\n")

print(f"\nSaved cheat sheet to: {key_path}")
