import pdfplumber
import csv

# Define bounding boxes
bounding_boxes = [
    (150.00, 427.68, 235.00, 577.94),
    (260.00, 427.68, 335.00, 577.94),
    (365.00, 427.68, 440.00, 577.94)
]

# Open the PDF
with pdfplumber.open("Truist_Purchase_1pt.pdf") as pdf:
    page = pdf.pages[0]  # Adjust if needed

    extracted_data = []
    for box in bounding_boxes:
        cropped = page.crop(bbox=box)
        text = cropped.extract_text() or ""
        extracted_data.append(text.strip())

# Write to CSV
with open("output.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Box1", "Box2", "Box3"])
    writer.writerow(extracted_data)

print("Data saved to output.csv")
