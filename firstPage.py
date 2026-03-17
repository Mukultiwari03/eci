import os
import re
from PyPDF2 import PdfReader, PdfWriter, PageObject
 
parent_dir = r"/home/muke/Pictures/test"
 
def blank_page():
    page = PageObject.create_blank_page(width=595, height=842)
    return page
 
def extract_sort_number(filename):
    """Extracts the number before -WI in the filename for sorting."""
    match = re.search(r'-(\d+)-WI\.pdf$', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return float('inf')  # Files that don't match pattern go to the end
 
for district_name in sorted(os.listdir(parent_dir)):
    district_path = os.path.join(parent_dir, district_name)
 
    if not os.path.isdir(district_path):
        continue
 
    for block_name in sorted(os.listdir(district_path)):
        block_path = os.path.join(district_path, block_name)
 
        if not os.path.isdir(block_path):
            continue
 
        merged_writer = PdfWriter()
        pages_added = 0
        placeholders = 0
 
        # Get all PDFs except the output file, sorted by the trailing number
        pdf_files = [
            f for f in os.listdir(block_path)
            if f.lower().endswith(".pdf") and f != "combined_first_pages.pdf"
        ]
        pdf_files.sort(key=extract_sort_number)
 
        for file_name in pdf_files:
            file_path = os.path.join(block_path, file_name)
 
            try:
                reader = PdfReader(file_path, strict=False)
                if len(reader.pages) > 0:
                    merged_writer.add_page(reader.pages[0])
                    pages_added += 1
                else:
                    merged_writer.add_page(blank_page())
                    placeholders += 1
                    print(f"  [BLANK] No pages in: {file_name}")
            except Exception as e:
                merged_writer.add_page(blank_page())
                placeholders += 1
                print(f"  [PLACEHOLDER] {file_name}: {e}")
 
        if pages_added + placeholders > 0:
            output_path = os.path.join(block_path, "combined_first_pages.pdf")
            with open(output_path, "wb") as f:
                merged_writer.write(f)
            print(f"✓ Block '{block_name}': {pages_added} real + {placeholders} placeholder pages → combined_first_pages.pdf")
        else:
            print(f"⚠ Block '{block_name}': No PDFs found, skipping.")
 
print("\nAll blocks processed.")

