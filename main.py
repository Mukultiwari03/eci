import requests
import base64
import time
import tezeract
import ddddocr
import random
import csv
import os
import threading
import supa
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv 
import shutil
import glob


# Initialize OCR once (global)
ocr = ddddocr.DdddOcr(show_ad=False)

# Lock for thread-safe file writing
csv_lock = threading.Lock()

urltogetcaptcha = "https://gateway-voters.eci.gov.in/api/v1/captcha-service/generateCaptcha"
urltogetdetails = "https://gateway-voters.eci.gov.in/api/v1/elastic/search-by-epic-from-national-display"
urltogetstate = "https://gateway-voters.eci.gov.in/api/v1/common/states"

proxies = [
{"http": "http://wmtjyhke:c4832wd244wd@31.59.20.176:6754/", "https": "http://wmtjyhke:c4832wd244wd@31.59.20.176:6754/"},
{"http": "http://wmtjyhke:c4832wd244wd@23.95.150.145:6114/", "https": "http://wmtjyhke:c4832wd244wd@23.95.150.145:6114/"},
{"http": "http://wmtjyhke:c4832wd244wd@198.23.239.134:6540/", "https": "http://wmtjyhke:c4832wd244wd@198.23.239.134:6540/"},
{"http": "http://wmtjyhke:c4832wd244wd@45.38.107.97:6014/", "https": "http://wmtjyhke:c4832wd244wd@45.38.107.97:6014/"},
{"http": "http://wmtjyhke:c4832wd244wd@107.172.163.27:6543/", "https": "http://wmtjyhke:c4832wd244wd@107.172.163.27:6543/"},
{"http": "http://wmtjyhke:c4832wd244wd@198.105.121.200:6462/", "https": "http://wmtjyhke:c4832wd244wd@198.105.121.200:6462/"},
{"http": "http://wmtjyhke:c4832wd244wd@64.137.96.74:6641/", "https": "http://wmtjyhke:c4832wd244wd@64.137.96.74:6641/"},
{"http": "http://wmtjyhke:c4832wd244wd@216.10.27.159:6837/", "https": "http://wmtjyhke:c4832wd244wd@216.10.27.159:6837/"},
{"http": "http://wmtjyhke:c4832wd244wd@142.111.67.146:5611/", "https": "http://wmtjyhke:c4832wd244wd@142.111.67.146:5611/"},
{"http": "http://wmtjyhke:c4832wd244wd@194.39.32.164:6461/", "https": "http://wmtjyhke:c4832wd244wd@194.39.32.164:6461/"}   
]

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def solve_with_ddddocr(image_bytes):
    return ocr.classification(image_bytes)

def write_to_csv(epic, status, data=""):
    file_exists = os.path.isfile("results.csv")
    with csv_lock:
        with open("results.csv", mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Write header if file is new
            if not file_exists:
                writer.writerow(["EPIC Number", "Status", "Raw Data"])
            writer.writerow([epic, status, data])

def process_single_epic(epNo):
    repetitions = 10
    
    for i in range(repetitions):
        try:
            proxy = random.choice(proxies)
            response = requests.get(urltogetcaptcha, proxies=proxy, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # print(data)
                captcha_value = data["captcha"]
                captcha_id = data["id"]

                image_bytes = base64.b64decode(captcha_value)
                captcha_ans = solve_with_ddddocr(image_bytes)   
                
                if len(captcha_ans) != 6:
                    continue

                payload = {
                    "captchaData": captcha_ans,
                    "captchaId": captcha_id,
                    "epicNumber": epNo,
                    "isPortal": "true",
                    "securityKey": "na",
                    "stateCd": "S19"
                }
                
                response2 = requests.post(urltogetdetails, json=payload, headers=headers, proxies=proxy, timeout=10)
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    # Check if EPIC exists or is deleted (empty list)
                    if isinstance(data2, list) and len(data2) > 0:
                        status = "sahi"
                        write_to_csv(epNo, status, data2[0].get("content", ""))
                        supa.main(data2[0].get("content"))
                        return {"epic": epNo, "status": status}
                    else:
                        status = "Not found as data"
                        write_to_csv(epNo, status)
                        return {"epic": epNo, "status": status}
                
                elif response2.status_code == 400:
                    continue # Try next repetition (wrong captcha)
                else:
                    continue
        except Exception:
            continue
            
    # If all repetitions fail
    write_to_csv(epNo, "galat")
    return {"epic": epNo, "status": "galat"}

def main(epic_list, max_workers):
    print(f"Starting process for {len(epic_list)} EPICs with {max_workers} threads...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_epic = {executor.submit(process_single_epic, epic): epic for epic in epic_list}
        
        # Process as they finish
        for future in as_completed(future_to_epic):
            epic = future_to_epic[future]
            try:
                result = future.result()
                print(f"Done: {epic} -> {result['status']}")
            except Exception as exc:
                print(f"Error processing {epic}: {exc}")

if __name__ == "__main__":   
    # This will now work correctly because we fixed the .env file
    folder_path_pdf = os.getenv("FOLDER_PATH")
    
    # Check if the folder exists to prevent errors
    if not folder_path_pdf or not os.path.exists(folder_path_pdf):
        print(f"Error: FOLDER_PATH '{folder_path_pdf}' does not exist.")
        exit()
    
    # glob already returns the full path!
    pdfs = glob.glob(f"{folder_path_pdf}/*.pdf")
    
    print(f"Found {len(pdfs)} PDFs to process.")
    
    for pdf_path in pdfs:
        # NO NEED for os.path.join here. pdf_path is already correct.
        print(f"Processing: {pdf_path}")
        
        my_epics = tezeract.main(pdf_path)
        
        # Adjust max_workers based on your proxy quality
        main(my_epics, max_workers=5)

        folder_path = "/home/muke/NMBC/eci/voter_boxes"
        pdfpages_path = "/home/muke/NMBC/eci/pdf_pages"

        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
                print("Folder and all contents deleted successfully.")
            except OSError as e:
                print(f"Error deleting folder: {e}")
        
        if os.path.exists(pdfpages_path):
            try:
                shutil.rmtree(pdfpages_path)
                print("Folder and all contents deleted successfully.")
            except OSError as e:
                print(f"Error deleting folder: {e}")

    print("\nSamapti")

   