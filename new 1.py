import asyncio
import sys
from playwright.async_api import async_playwright

async def fetch_vystar_rates():
    print("🚀 Starting Playwright…")
    rates_payload = {}

    async def handle_response(response):
        if "rates" in response.url and response.headers.get("content-type", "").startswith("application/json"):
            print(f"📨 Captured JSON response: {response.url}")
            try:
                data = await response.json()
                rates_payload.update(data)
            except Exception as e:
                print("❌ JSON parse error:", e)

    async with async_playwright() as p:
        print("🔧 Launching browser…")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("response", lambda resp: asyncio.create_task(handle_response(resp)))

        print("🌐 Navigating to VyStar rates page…")
        await page.goto(
            "https://www.vystarcu.org/personal/rates/mortgage-loan-rates",
            wait_until="networkidle"
        )

        # Try clicking any cookie banner
        try:
            print("🍪 Attempting to accept cookies…")
            await page.click("text=Accept All Cookies", timeout=5_000)
            print("✅ Cookies accepted")
        except Exception:
            print("⚠️ No cookie banner detected or click failed")

        # Give time for React/Vue to render
        await page.wait_for_timeout(1_000)

        # Option B: JSON
        if rates_payload:
            print("🔍 Found JSON payload; extracting rate…")
            # adjust the keys based on what you saw in DevTools
            key = "30_year_fixed"  # or whatever the actual field is
            entry = rates_payload.get(key)
            if entry:
                print("💰 30‑Year Fixed (JSON):", entry.get("rate", entry))
            else:
                print("❗ JSON arrived but didn't contain", key)
                print(rates_payload)
        else:
            # Option A: DOM scraping
            print("🔍 JSON not found; falling back to DOM scrape…")
            selector = "[data-rate='30-year-fixed'], .thirty-year-fixed-rate"
            await page.wait_for_selector(selector, timeout=10_000)
            text = await page.locator(selector).inner_text()
            print("💰 30‑Year Fixed (DOM):", text)

        print("🏁 Done. Closing browser…")
        await browser.close()

def main():
    try:
        asyncio.run(fetch_vystar_rates())
    except Exception as e:
        print("🔥 Script error:", e, file=sys.stderr)
    finally:
        # This keeps the window open if double‑clicked
        input("Press Enter to exit…")

if __name__ == "__main__":
    main()
