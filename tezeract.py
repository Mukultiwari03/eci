import os
import cv2
import pytesseract
import cutbox
from PIL import Image
import re
from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv 

load_dotenv() 
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
 
PDF_PATH = os.getenv("PDF_PATH")
VOTER_BOXES_DIR = "voter_boxes"

# DEBUG_DIR = "debug_ocr_crops"
# os.makedirs(DEBUG_DIR, exist_ok=True)
 
 
def crop_epic_region(image_path):
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    
    # Adjusted crop coordinates to avoid touching the right/top black borders
    # which Tesseract often mistakes for the letter 'I', 'L', or '1'
    crop = img[int(h*0.03):int(h*0.18), int(w*0.45):int(w*0.98)]
    
    return crop


def preprocess_for_ocr(crop_img):
    """Prepares image specifically for optimal Tesseract OCR"""
    # 1. Convert to Grayscale
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    
    # 2. Resize (Scale up 2.5x to reach Tesseract's optimal font size)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    
    # 3. Apply Otsu's Thresholding to make it pitch black text on pure white background
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    # 4. Add a white border (padding). 
    # Tesseract's PSM 7 relies on finding the text baseline. Edges touching the frame break it.
    padded = cv2.copyMakeBorder(thresh, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
    
    return padded


def ocr_epic(crop_img, debug_filename=None):
    try:
        # Preprocess the crop
        processed_img = preprocess_for_ocr(crop_img)
        
        # --- NEW: Save the preprocessed image for visual inspection ---
        # if debug_filename:
        #     debug_path = os.path.join(DEBUG_DIR, debug_filename)
        #     cv2.imwrite(debug_path, processed_img)
        # --------------------------------------------------------------

        # Convert to PIL
        pil_img = Image.fromarray(processed_img)
        
        # Whitelist & Single Line mode
        custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/'
        
        text = pytesseract.image_to_string(pil_img, config=custom_config)
        text = text.strip().upper().replace(" ", "").replace("\n", "")
        
        # REGEX CLEANUP: Extract only the valid EPIC patterns
        epic_pattern = r'([A-Z]{3}\d{7}|[A-Z]{2}/\d{2}/\d{3}/\d{6})'
        match = re.search(epic_pattern, text)
        
        if match:
            return match.group(1) 
        else:
            return text 
            
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""


def process_image(image_path):
    crop = crop_epic_region(image_path)
    
    # --- NEW: Generate a unique name like "page_3_voter_15.png" ---
    folder_name = os.path.basename(os.path.dirname(image_path)) # e.g., "page_3"
    file_name = os.path.basename(image_path)                    # e.g., "voter_15.png"
    debug_name = f"{folder_name}_{file_name}"
    
    text = ocr_epic(crop, debug_filename=debug_name)
    text = ocr_epic(crop)

    return text
 
 
def collect_all_images():
 
    image_paths = []
 
    for page_folder in os.listdir(VOTER_BOXES_DIR):
 
        if page_folder in ["page_1", "page_2"]:
            continue
 
        page_path = os.path.join(VOTER_BOXES_DIR, page_folder)
 
        if not os.path.isdir(page_path):
            continue
 
        for file in os.listdir(page_path):
 
            if file.endswith(".png"):
                image_paths.append(os.path.join(page_path, file))
 
    return image_paths
 
 
def main(pdf_path):
 
    cutbox.PDF_PATH = pdf_path
    cutbox.main()
 
    image_paths = collect_all_images()
 
    print("Total images:", len(image_paths))
 
    epic_list = []
 
    with ProcessPoolExecutor() as executor:
 
        results = executor.map(process_image, image_paths)
 
        for text in results:
            if text:
                epic_list.append(text)
 
    print("Total EPICs:", len(epic_list))
    print(epic_list)
    return epic_list
 
 
if __name__ == "__main__":
    main()