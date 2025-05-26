#!/usr/bin/env python3

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

# --- Import your secrets ---
from secrets import sender_email, app_password
try:
    from secrets import recipient_emails
except ImportError:
    from secrets import recipient_email
    recipient_emails = [recipient_email]

# --- Define styling colors ---
company_colors = {
    "blue": "#175892",
    "red": "#ce2d47",
    "light": "f6f9f9",
    "gray": "#555"
}

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
                "15-Year Fixed": (17.0, 250.0, 57.0, 267.0),
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
                "30-Year Fixed": (348.0, 31.0, 390.0, 48.0),
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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"\n🌐 Navigating to {bank['name']}...")
        await page.goto(bank['url'], wait_until="networkidle")
        await asyncio.sleep(5)

        for mode, toggle_id, point_label in bank['combinations']:
            filename = f"{bank['name']}_{mode}_{point_label}.pdf"
            if toggle_id:
                print(f"➡️ Switching to {mode} ({point_label})")
                await page.evaluate(f"""
                    [...document.querySelectorAll('a[role=tab]')]
                        .find(e => e.textContent.includes("{mode}"))
                        ?.click();
                """)
                await asyncio.sleep(2)
                await page.evaluate(f"document.getElementById('{toggle_id}')?.click();")
                await asyncio.sleep(5)

            await page.pdf(path=filename, format="A4", print_background=True)
            print(f"📄 Saved {filename}")

        await browser.close()
        print(f"✅ Completed PDFs for {bank['name']}")


def extract_rates(all_results):
    for bank in BANKS:
        pat = re.compile(bank['regex'], re.IGNORECASE)
        for mode, _, point_label in bank['combinations']:
            pdf_f = f"{bank['name']}_{mode}_{point_label}.pdf"
            if not os.path.exists(pdf_f):
                print(f"⚠️ Missing {pdf_f}")
                continue
            with pdfplumber.open(pdf_f) as pdf:
                page = pdf.pages[bank['page']]
                boxes = bank['coordinates'].get(mode, {})
                if boxes:
                    for loan, bbox in boxes.items():
                        txt = page.within_bbox(bbox).extract_text() or ""
                        m = pat.search(txt)
                        rate = m.group('rate') if m else 'N/A'
                        all_results.append({'Bank': bank['name'], 'Purpose': mode, 'Points': point_label, 'Loan Type': loan, 'Rate': rate})
                else:
                    text = page.extract_text() or ""
                    for m in pat.finditer(text):
                        all_results.append({'Bank': bank['name'], 'Purpose': mode, 'Points': point_label or 'N/A', 'Loan Type': 'N/A', 'Rate': m.group('rate')})

# --- Email utilities ---
def load_rates(csv_path):
    d = defaultdict(list)
    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            d[row.get('Bank','Unknown')].append(row)
    return d


def build_bank_table(bank, entries):
    cols = list(entries[0].keys())
    hdr = ''.join(f'<th style="border:1px solid #ccc; padding:6px; background:{company_colors["blue"]}; color:#fff;">{c}</th>' for c in cols)
    body = ''.join('<tr>' + ''.join(f'<td style="border:1px solid #ccc; padding:6px;">{row[c]}</td>' for c in cols) + '</tr>' for row in entries)
    return f"""
    <h3 style="color:{company_colors['blue']};">{bank}</h3>
    <table style="border-collapse:collapse; width:100%; max-width:600px; margin-bottom:20px;"><thead><tr>{hdr}</tr></thead><tbody>{body}</tbody></table>
    """


def build_html(rates_by_bank):
    date_str = datetime.now().strftime('%Y-%m-%d')
    parts = [f'<h2 style="color:{company_colors["blue"]};">Mortgage Rates – {date_str}</h2>']
    for b, e in rates_by_bank.items(): parts.append(build_bank_table(b,e))
    parts.append(f'<p style="font-size:small; color:{company_colors["gray"]};">Generated on {date_str}</p>')
    return '<html><body style="font-family:Arial,sans-serif; background:'+company_colors['light']+'; padding:20px;">' + ''.join(parts) + '</body></html>'


def send_email(html):
    sub = f"Mortgage Rates – {datetime.now().strftime('%Y-%m-%d')}"
    tos = recipient_emails if isinstance(recipient_emails,list) else [recipient_emails]
    msg = EmailMessage()
    msg['Subject'], msg['From'], msg['To'] = sub, sender_email, ', '.join(tos)
    msg.set_content('Please use HTML view')
    msg.add_alternative(html, subtype='html')
    with smtplib.SMTP_SSL('smtp.gmail.com',465,context=ssl.create_default_context()) as s:
        s.login(sender_email, app_password)
        s.sendmail(sender_email, tos, msg.as_string())
    print(f"📧 Email sent to {tos}")

async def main():
    # 1) Capture PDFs
    for bank in BANKS:
        await capture_pdfs(bank)

    # 2) Extract and save CSV
    data = []
    extract_rates(data)
    out = 'all_cleaned_rates.csv'
    with open(out,'w',newline='',encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['Bank','Purpose','Points','Loan Type','Rate'])
        w.writeheader(); w.writerows(data)
    print(f"✅ Saved CSV to {out}")

    # 3) Load CSV and send email
    grouped = load_rates(out)
    html = build_html(grouped)
    send_email(html)

if __name__ == '__main__':
    asyncio.run(main())
