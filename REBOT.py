import asyncio
import re
import csv
import pdfplumber
from playwright.async_api import async_playwright
import os

# === CONFIGURATION ===
# Unified regex with named group 'rate' for consistent extraction
BANKS = [
    {
        "name": "Truist",
        "url": "https://www.truist.com/mortgage/current-mortgage-rates",
        "combinations": [
            ("Purchase", "dynamic-rates-input-1__mortgage-rates-354528076", "1pt"),
            ("Purchase", "dynamic-rates-input-2__mortgage-rates-354528076", "0pt"),
            ("Refinance", "dynamic-rates-input-1__mortgage-rates-586732436", "1pt"),
            ("Refinance", "dynamic-rates-input-2__mortgage-rates-586732436", "0pt"),
        ],
        "coordinates": {
            "Purchase": {
                "30-Year Fixed": (150.0, 415.0, 235.0, 585.0),
                "15-Year Fixed": (260.0, 415.0, 335.0, 585.0),
                "30-Year Jumbo": (365.0, 415.0, 440.0, 585.0),
            },
            "Refinance": {
                "30-Year Fixed": (210.0, 410.0, 285.0, 580.0),
                "15-Year Fixed": (315.0, 410.0, 385.0, 580.0),
            }
        },
        "regex": r"(?P<rate>[\d]+(?:\.\d+)?%)",
    },
    {
        "name": "Quicken Loans",
        "url": "https://www.quickenloans.com/mortgage-rates",
        "combinations": [
            ("General", "", "0pt"),
        ],
        "coordinates": {
            "General": {
                "30-Year Fixed": (30.0, 305.0, 425.0, 325.0),
                "15-Year Fixed": (30.0, 335.0, 425.0, 355.0),
            }
        },
        "regex": r"(?P<rate>[\d]+(?:\.\d+)?%)",
    },
]

async def capture_pdfs(bank):
    """
    Navigate to each bank's rate page, toggle the proper tabs/points, and save each view as a PDF.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"\n🌐 Navigating to {bank['name']}...")
        await page.goto(bank['url'], wait_until="networkidle")
        await asyncio.sleep(7)

        for mode, toggle_id, point_label in bank['combinations']:
            filename = f"{bank['name']}_{mode}_{point_label}.pdf"

            if toggle_id:
                print(f"➡️ Switching to: {mode} - {point_label}")
                # Click the mode/tab
                await page.evaluate(f"""
                    [...document.querySelectorAll('a[role=tab]')]
                        .find(e => e.textContent.includes("{mode}"))
                        ?.click();
                """
                )
                await asyncio.sleep(2)
                # Click the points toggle
                await page.evaluate(f"""
                    document.getElementById("{toggle_id}")?.click();
                """
                )
                await asyncio.sleep(6)

            # Save the page to PDF
            await page.pdf(path=filename, format="A4", print_background=True)
            print(f"📄 Saved: {filename}")

        await browser.close()
        print(f"✅ Finished capturing PDFs for {bank['name']}.")


def extract_rates(all_results):
    """
    Open each saved PDF, crop to the configured bounding boxes (if any), apply the unified regex,
    and append the structured data to all_results.
    """
    for bank in BANKS:
        pattern = re.compile(bank['regex'], re.IGNORECASE)

        for mode, _, point_label in bank['combinations']:
            pdf_path = f"{bank['name']}_{mode}_{point_label}.pdf"
            if not os.path.exists(pdf_path):
                print(f"⚠️ Missing file: {pdf_path}")
                continue

            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[0]
                boxes = bank['coordinates'].get(mode)

                if boxes:
                    # Use the defined bounding boxes for this mode
                    for loan_type, bbox in boxes.items():
                        cropped_text = page.within_bbox(bbox).extract_text() or ""
                        match = pattern.search(cropped_text)
                        rate = match.group('rate') if match else "N/A"
                        all_results.append({
                            'Bank': bank['name'],
                            'Purpose': mode,
                            'Points': point_label,
                            'Loan Type': loan_type,
                            'Rate': rate
                        })
                else:
                    # Fallback: search the entire page text
                    full_text = page.extract_text() or ""
                    for m in pattern.finditer(full_text):
                        rate = m.group('rate')
                        all_results.append({
                            'Bank': bank['name'],
                            'Purpose': mode,
                            'Points': point_label or "N/A",
                            'Loan Type': 'N/A',
                            'Rate': rate
                        })

async def main():
    # 1) Download all PDFs
    for bank in BANKS:
        await capture_pdfs(bank)

    # 2) Extract rates from every PDF exactly once
    all_data = []
    extract_rates(all_data)

    # 3) Write results to CSV
    output_file = 'all_cleaned_rates.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Bank", "Purpose", "Points", "Loan Type", "Rate"])
        writer.writeheader()
        writer.writerows(all_data)

    print(f"\n✅ All bank rates saved to {output_file}")

if __name__ == '__main__':
    asyncio.run(main())
