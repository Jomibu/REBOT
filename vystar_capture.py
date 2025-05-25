import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    cookie_file = "cookies.json"
    output_path = r"C:\Users\Toxic_Robot\Scripts\MortgageRates\REBOT\output.pdf"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Build the context args only if cookies.json exists
    context_args = {}
    if os.path.exists(cookie_file):
        context_args["storage_state"] = cookie_file
        print("🔄 Loading existing cookies.json")
    else:
        print("✨ No cookies.json found; starting fresh")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(**context_args)
        page = await context.new_page()

        # Navigate and wait
        await page.goto(
            "https://vystarcu.org/personal/rates/mortgage-loan-rates",
            wait_until="networkidle"
        )

        # Try clicking the banner
        try:
            await page.wait_for_selector(
                'a:has-text("Accept All Cookies")',
                timeout=5_000
            )
            await page.click('a:has-text("Accept All Cookies")')
            print("✅ Clicked Accept All Cookies")
        except Exception as e:
            print(f"⚠️ Cookie banner not found or error: {e}")

        # Give things a moment
        await page.wait_for_timeout(2_000)

        # Save PDF
        await page.pdf(path=output_path, format="A4", print_background=True)
        print(f"✅ PDF saved to {output_path}")

        # Persist cookies for next run
        await context.storage_state(path=cookie_file)
        print(f"💾 cookies.json written")

        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as e:
        print(f"🔥 Script crashed: {e}")
