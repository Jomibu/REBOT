import pdfplumber
import csv
import re

# Define bounding boxes
bounding_boxes = [
    #(150.00, 415.00, 235.00, 585.00),
    #(260.00, 415.00, 335.00, 585.00),
    #(365.00, 415.00, 440.00, 585.00)
    (210.00, 410.00, 285.00, 580.00)
    (315.00, 410.00, 385.00, 445.00
]

# Regex pattern: grab % number after "rate:" and before "+"
rate_pattern = re.compile(r"rate:\s*([\d.]+%)", re.IGNORECASE)

# Open the PDF
with pdfplumber.open("Truist_Purchase_1pt.pdf") as pdf:
    page = pdf.pages[0]  # Adjust if needed

    extracted_data = []
    for box in bounding_boxes:
        cropped = page.crop(bbox=box)
        text = cropped.extract_text() or ""
        match = rate_pattern.search(text)
        rate = match.group(1) if match else ""
        extracted_data.append(rate)

# Write to CSV
with open("output.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Box1", "Box2", "Box3"])
    writer.writerow(extracted_data)

print("Extracted rates saved to output.csv")
