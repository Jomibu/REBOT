import asyncio
import re
import csv
import pdfplumber
from playwright.async_api import async_playwright
import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
from collections import defaultdict

# === CONFIGURATION ===
# Unified regex with named group 'rate' for consistent extraction
BANKS = [
    {
        "name": "Truist",
        "url": "https://www.truist.com/mortgage/current-mortgage-rates",
        "page": 0,
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
        "page": 0,
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
    {
        "name": "Vystar",
        "url": "https://consumer.optimalblue.com/FeaturedRates?GUID=248df9c1-923d-4153-ab2d-050ba1bd6acf",
        "page": 0,
        "combinations": [
            ("General", "", "0pt"),
        ],
        "coordinates": {
            "General": {
                "30-Year Fixed": (17.0, 84.0, 57.0, 100.0),
                "15-Year Fixed": (19.0, 254.0, 55.0, 265.0),
            }
        },
        "regex": r"(?P<rate>[\d]+(?:\.\d+)?%)",
    },
    {
        "name": "Bankrate",
        "url": "https://www.bankrate.com/mortgages/arm-loan-rates/?mortgageType=Purchase&partnerId=br3&pid=br3&pointsChanged=false&purchaseDownPayment=55680&purchaseLoanTerms=3-1arm%2C5-1arm%2C7-1arm%2C10-1arm&purchasePoints=All&purchasePrice=278400&purchasePropertyType=SingleFamily&purchasePropertyUse=PrimaryResidence&searchChanged=false&ttcid&userCreditScore=740&userDebtToIncomeRatio=0&userFha=false&userVeteranStatus=NoMilitaryService&zipCode=32669#todays-arm-rates",
        "page": 3,
        "combinations": [
            ("Refinance", "refinance-1", "0pt"),
            ("Purchase", "purchase-0", "0pt"),
        ],
        "coordinates": {
            "Purchase": {
                "30-Year Fixed": (350.0, 31.0, 390.0, 48.0),
                "15-Year Fixed": (350.0, 68.0, 390.0, 85.0),
            },
            "Refinance": {
                "30-Year Fixed": (350.0, 330.0, 387.0, 350.0),
                "15-Year Fixed": (350.0, 365.0, 387.0, 385.0),
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
        pagenumber = bank['page']

        for mode, _, point_label in bank['combinations']:
            pdf_path = f"{bank['name']}_{mode}_{point_label}.pdf"
            if not os.path.exists(pdf_path):
                print(f"⚠️ Missing file: {pdf_path}")
                continue

            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[pagenumber]
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

# --- Import your secrets ---
from secrets import sender_email, app_password
# Support either a list of recipients or a single address
try:
    from secrets import recipient_emails
except ImportError:
    from secrets import recipient_email
    recipient_emails = [recipient_email]

# --- Define styling colors ---
company_colors = {
    "blue": "#175892",
    "red": "#ce2d47",
    "light": "#f6f9f9",
    "gray": "#555"
}

# --- Read and group rates from CSV ---
def load_rates(csv_path):
    rates_by_bank = defaultdict(list)
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bank = row.get('Bank') or row.get('bank') or 'Unknown'
            rates_by_bank[bank].append(row)
    return rates_by_bank

# --- Build HTML table for one bank ---
def build_bank_table(bank, entries):
    cols = list(entries[0].keys())
    header = ''.join(
        f'<th style="border:1px solid #ccc; padding:6px; background:{company_colors["blue"]}; color:#fff;">{col}</th>'
        for col in cols
    )
    rows = ''
    for entry in entries:
        cells = ''.join(
            f'<td style="border:1px solid #ccc; padding:6px;">{entry[col]}</td>'
            for col in cols
        )
        rows += f'<tr>{cells}</tr>'
    return f"""
    <h3 style="color:{company_colors['blue']};">{bank}</h3>
    <table style="border-collapse:collapse; width:100%; max-width:600px; margin-bottom:20px;">
      <thead><tr>{header}</tr></thead>
      <tbody>
        {rows}
      </tbody>
    </table>
    """

# --- Build full HTML message ---
def build_html(rates_by_bank):
    date_str = datetime.now().strftime('%Y-%m-%d')
    parts = [
        '<html>',
        f'<body style="font-family:Arial,sans-serif; background:{company_colors['light']}; color:#333; padding:20px;">',
        f'<h2 style="color:{company_colors['blue']};">Mortgage Rates Report – {date_str}</h2>'
    ]
    for bank, entries in rates_by_bank.items():
        parts.append(build_bank_table(bank, entries))
    parts.append(f'<p style="font-size:small; color:{company_colors['gray']};">Generated on {date_str}</p>')
    parts.append('</body></html>')
    return ''.join(parts)

# --- Send email via Gmail ---
def send_email(html_content):
    sent_date = datetime.now().strftime('%Y-%m-%d')
    subject = f"Mortgage Rates – {sent_date}"
    recipients = recipient_emails if isinstance(recipient_emails, list) else [recipient_emails]

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    msg.set_content('Please view this email in an HTML-capable client.')
    msg.add_alternative(html_content, subtype='html')

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipients, msg.as_string())
    print(f"📧 Sent: {subject} to {recipients}")


    # 2) Once CSV is ready, send the email report:
    csv_path = 'all_cleaned_rates.csv'  # ensure this matches your existing output filename
    rates_by_bank = load_rates(csv_path)
    html = build_html(rates_by_bank)
    send_email(html)

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