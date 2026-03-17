import os
import cv2
import numpy as np
from pdf2image import convert_from_path
from dotenv import load_dotenv 

#working fine but need some refinements
load_dotenv()
PDF_PATH = ""
PAGES_DIR = "pdf_pages"
OUTPUT_DIR = "voter_boxes"
DPI = 300
 
os.makedirs(PAGES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
 
 
# STEP 1 — PDF → JPEG (Skip if exists)
poppler_path = os.getenv("POPPLER_PATH")
 
def convert_pdf_if_needed():
    # images = [f for f in os.listdir(PAGES_DIR) if f.endswith(".png")]
 
    # if len(images) > 0:
    #     print("✅ PDF already converted.")
    #     return
 
    print("Converting PDF to images...")
 
    pages = convert_from_path(PDF_PATH, dpi=DPI,poppler_path=poppler_path)
    total_pages = len(pages)
 
    for i, page in enumerate(pages):
        # skip first, second and last page
        if i in (0, 1) or i == total_pages - 1:
            continue
 
        path = os.path.join(PAGES_DIR, f"page_{i+1}.png")
        page.save(path, "JPEG")
        print("Saved:", path)
 
    print("✅ Conversion complete")
 
 
# STEP 2 — PREPROCESS IMAGE
 
 
def preprocess(img):
 
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
 
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        5
    )
 
    return binary
 
 
# STEP 3 — DETECT ROWS
 
 
def detect_rows(binary):
 
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 5))
    merged = cv2.dilate(binary, kernel, iterations=2)
 
    projection = np.sum(merged, axis=1)
 
    rows = []
    start = None
    threshold = np.max(projection) * 0.2
 
    for i, val in enumerate(projection):
 
        if val > threshold and start is None:
            start = i
 
        elif val <= threshold and start is not None:
            rows.append((start, i))
            start = None
 
    return rows
 
 
# STEP 4 — DETECT COLUMNS
 
 
def detect_columns(binary):
 
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 80))
    merged = cv2.dilate(binary, kernel, iterations=2)
 
    projection = np.sum(merged, axis=0)
 
    cols = []
    start = None
    threshold = np.max(projection) * 0.2
 
    for i, val in enumerate(projection):
 
        if val > threshold and start is None:
            start = i
 
        elif val <= threshold and start is not None:
            cols.append((start, i))
            start = None
 
    return cols
 
 
# STEP 5 — EXTRACT VOTER BOXES
 
 
def extract_voters():
 
    for page_name in sorted(os.listdir(PAGES_DIR)):
 
 
        if not page_name.endswith(".png"):
            continue
        if page_name=="page_1.png" or page_name=="page_2.png":
            continue
 
        print("\nProcessing:", page_name)
 
        img_path = os.path.join(PAGES_DIR, page_name)
        img = cv2.imread(img_path)
 
        binary = preprocess(img)
 
        rows = detect_rows(binary)
        cols = detect_columns(binary)
 
        print(f"Detected Rows: {len(rows)} | Columns: {len(cols)}")
 
        page_output = os.path.join(
            OUTPUT_DIR,
            page_name.replace(".png", "")
        )
 
        os.makedirs(page_output, exist_ok=True)
 
        voter_id = 1
 
        for (y1, y2) in rows:
            for (x1, x2) in cols:
 
                crop = img[y1:y2, x1:x2]
 
                # ignore tiny noise regions
                if crop.shape[0] < 100 or crop.shape[1] < 100:
                    continue
 
                save_path = os.path.join(
                    page_output,
                    f"voter_{voter_id}.png"
                )
 
                cv2.imwrite(save_path, crop)
                voter_id += 1
 
        print(f"✅ Saved {voter_id-1} voters")
 
 
# MAIN
 
def main():
    convert_pdf_if_needed()
    extract_voters()
 
    print("\nDONE — One box per voter created.")
 
 
if __name__ == "__main__":
    convert_pdf_if_needed()
    extract_voters()
 
    print("\nDONE — One box per voter created.")