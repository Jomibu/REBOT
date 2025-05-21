import asyncio
import re
import csv
import pdfplumber
from playwright.async_api import async_playwright
import os

URL = "https://www.truist.com/mortgage/current-mortgage-rates"

COMBINATIONS = [
    ("Purchase", "dynamic-rates-input-1__mortgage-rates-354528076", "1pt"),
    ("Purchase", "dynamic-rates-input-2__mortgage-rates-354528076", "0pt"),
    ("Refinance", "dynamic-rates-input-1__mortgage-rates-586732436", "1pt"),
    ("Refinance", "dynamic-rates-input-2__mortgage-rates-586732436", "0pt"),
]

# Coordinates to extract based on PDF layout
COORDINATES = {
    "Purchase": {
        "30-Year Fixed": (150.0, 415.0, 235.0, 585.0),
        "15-Year Fixed": (260.0, 415.0, 335.0, 585.0),
        "30-Year Jumbo": (365.0, 415.0, 440.0, 585.0),
    },
    "Refinance": {
        "30-Year Fixed": (210.0, 410.0, 285.0, 580.0),
        "15-Year Fixed": (315.0, 410.0, 385.0, 580.0),
    }
}

rate_pattern = re.compile(r"rate:\s*([\d.]+%)", re.IGNORECASE)

async def capture_pdfs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("🌐 Navigating to Truist...")
        await page.goto(URL, wait_until="networkidle")
        await asyncio.sleep(7)

        for mode, toggle_id, point_label in COMBINATIONS:
            print(f"➡️ Switching to: {mode} - {point_label}")
            await page.evaluate(f"""
                [...document.querySelectorAll('a[role=tab]')].find(e => e.textContent.includes("{mode}"))?.click();
            """)
            await asyncio.sleep(2)

            await page.evaluate(f"""
                document.getElementById("{toggle_id}")?.click();
            """)
            await asyncio.sleep(6)

            filename = f"Truist_{mode}_{point_label}.pdf"
            print(f"📄 Saving: {filename}")
            await page.pdf(path=filename, format="A4", print_background=True)

        await browser.close()
        print("✅ PDFs saved.")

def extract_rates():
    results = []

    for mode, _, point_label in COMBINATIONS:
        pdf_path = f"Truist_{mode}_{point_label}.pdf"
        if not os.path.exists(pdf_path):
            print(f"⚠️ Missing file: {pdf_path}")
            continue

        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            boxes = COORDINATES.get(mode, {})

            for loan_type, bbox in boxes.items():
                text = page.within_bbox(bbox).extract_text() or ""
                match = rate_pattern.search(text)
                rate = match.group(1) if match else "N/A"
                results.append({
                    "Purpose": mode,
                    "Points": point_label,
                    "Loan Type": loan_type,
                    "Rate": rate
                })

    with open("truist_cleaned_rates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Purpose", "Points", "Loan Type", "Rate"])
        writer.writeheader()
        writer.writerows(results)

    print("✅ Rates extracted and saved to truist_cleaned_rates.csv")

if __name__ == "__main__":
    asyncio.run(capture_pdfs())
    extract_rates()
