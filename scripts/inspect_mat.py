import scipy.io
import glob
import os
import numpy as np

def inspect_file(filepath):
    print(f"\n=== Inspecting: {filepath} ===")
    mat = scipy.io.loadmat(filepath)
    for k in mat.keys():
        if k.startswith('__'):
            continue
        v = mat[k]
        if isinstance(v, np.ndarray):
            print(f"Key: {k:15s} | Shape: {str(v.shape):15s} | Dtype: {v.dtype}")
            if v.size <= 20:
                print(f"   Value: {v.tolist()}")
            elif v.ndim >= 2 and v.shape[0] < 10:
                print(f"   Sample:\n{v}")
            elif v.ndim >= 2 and v.shape[1] < 10:
                print(f"   First 3 rows:\n{v[:3]}")
        else:
            print(f"Key: {k:15s} | Type: {type(v)} | Value: {v}")

def main():
    msa_files = sorted(glob.glob("data/raw/MSA/*.mat"))
    pd_files = sorted(glob.glob("data/raw/PD/*.mat"))
    ctrl_files = sorted(glob.glob("data/raw/CTRL/*.mat"))
    
    if msa_files:
        inspect_file(msa_files[0])
        inspect_file(msa_files[1])
    if pd_files:
        inspect_file(pd_files[0])
    if ctrl_files:
        inspect_file(ctrl_files[0])

if __name__ == "__main__":
    main()
