import pdfplumber
import csv
import re

bounding_boxes = [
    (30.00, 305.00, 425.00, 325.00),
    (30.00, 335.00, 425.00, 355.00)
]

rate_pattern = re.compile(r"(30-Year Fixed|15-Year Fixed)\s*\*?\s*([\d.]+)%\s*/", re.IGNORECASE)

with pdfplumber.open("Quicken Loans_General_0pt.pdf") as pdf:
    page = pdf.pages[0]
    extracted_data = []

    for i, box in enumerate(bounding_boxes):
        cropped = page.crop(bbox=box)
        text = cropped.extract_text() or ""
        print(f"\n📦 Box {i+1} text:\n{text}")
        match = rate_pattern.search(text)
        rate = match.group(2) if match else ""
        extracted_data.append(rate)

with open("output.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["30-Year Fixed", "15-Year Fixed"])
    writer.writerow(extracted_data)

print("\n✅ Extracted rates saved to output.csv")
