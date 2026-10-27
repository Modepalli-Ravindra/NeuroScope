import os
import sys
import json
import time
import urllib.request
import concurrent.futures

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
CLASSES = ["MSA", "PD", "CTRL", "PSP"]
GITHUB_API = "https://api.github.com/repos/innovation-center-etf/FINGER-TAPPING-PARKINSONISMS-DATABASE/contents/DATA/{}"

def download_file(item, target_dir):
    filename = item["name"]
    download_url = item["download_url"]
    target_path = os.path.join(target_dir, filename)
    
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        return True, filename, "Already exists"
    
    for attempt in range(3):
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "NeuroScope-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(target_path, "wb") as f:
                f.write(resp.read())
            return True, filename, "Downloaded"
        except Exception as e:
            time.sleep(1 + attempt)
            if attempt == 2:
                return False, filename, str(e)

def main():
    print(f"Target dataset directory: {DATASET_DIR}")
    total_files = 0
    downloaded_files = 0
    failed_files = []

    for cls in CLASSES:
        cls_dir = os.path.join(DATASET_DIR, cls)
        os.makedirs(cls_dir, exist_ok=True)
        
        print(f"\nFetching metadata for class: {cls}...")
        url = GITHUB_API.format(cls)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                items = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Error getting items for {cls}: {e}")
            continue

        print(f"Found {len(items)} files in {cls}. Downloading in parallel...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_item = {executor.submit(download_file, item, cls_dir): item for item in items}
            for future in concurrent.futures.as_completed(future_to_item):
                success, fname, msg = future.result()
                total_files += 1
                if success:
                    downloaded_files += 1
                else:
                    failed_files.append((cls, fname, msg))
                    print(f"Failed to download {fname}: {msg}")

        print(f"Class {cls} complete. Available files in {cls}: {len(os.listdir(cls_dir))}")

    print("\n--- Download Summary ---")
    print(f"Total processed: {total_files}")
    print(f"Successfully available: {downloaded_files}")
    if failed_files:
        print(f"Failures: {len(failed_files)}")
    else:
        print("All dataset files successfully synchronized!")

if __name__ == "__main__":
    main()
