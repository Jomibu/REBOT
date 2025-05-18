import asyncio
from playwright.async_api import async_playwright

URL = "https://www.truist.com/mortgage/current-mortgage-rates"

# These are the four tab and point combinations
TOGGLE_COMBINATIONS = [
    ("Purchase", "dynamic-rates-input-1__mortgage-rates-354528076"),  # 1 Point
    ("Purchase", "dynamic-rates-input-2__mortgage-rates-354528076"),  # 0 Points
    ("Refinance", "dynamic-rates-input-1__mortgage-rates-586732436"),
    ("Refinance", "dynamic-rates-input-2__mortgage-rates-586732436"),
]

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("🌐 Navigating to Truist...")
        await page.goto(URL, wait_until="networkidle")
        await asyncio.sleep(7)  # Give JS a chance to finish rendering

        for loan_type, input_id in TOGGLE_COMBINATIONS:
            print(f"➡️ Switching to: {loan_type} - {input_id}")
            
            # Click the loan type tab
            await page.evaluate(f"""
                [...document.querySelectorAll('a[role=tab]')].find(e => e.textContent.includes("{loan_type}"))?.click();
            """)
            await asyncio.sleep(2)

            # Click the radio input by id
            await page.evaluate(f"""
                document.getElementById("{input_id}")?.click();
            """)
            await asyncio.sleep(12)  # Wait for the rates to refresh

            # Save PDF
            filename = f"Truist_{loan_type}_{'1pt' if '1__' in input_id else '0pt'}.pdf"
            print(f"📄 Saving: {filename}")
            await page.pdf(path=filename, format="A4", print_background=True)

        await browser.close()
        print("✅ Done.")

if __name__ == "__main__":
    asyncio.run(run())