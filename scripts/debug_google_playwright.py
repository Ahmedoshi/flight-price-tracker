"""Manual debug script - launches a REAL visible browser and drives
google.com/travel/flights directly via Playwright. Not a pytest test
(moved out of tests/ so pytest's default collection can't import and
execute this at collection time). Run with:
python3 scripts/debug_google_playwright.py
"""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        slow_mo=300
    )

    page = browser.new_page(viewport={"width": 1600, "height": 1000})

    print("Opening Google Flights...")

    page.goto(
        "https://www.google.com/travel/flights",
        wait_until="networkidle"
    )

    page.wait_for_timeout(4000)

    # -------------------------------------------------
    # ORIGIN
    # -------------------------------------------------

    print("Selecting origin...")

    origin = page.get_by_label("Where from?")

    origin.click()

    page.keyboard.press("Meta+A")
    page.keyboard.press("Backspace")

    page.keyboard.type("RUH")

    page.wait_for_timeout(1500)

    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    page.wait_for_timeout(2000)

    # -------------------------------------------------
    # DESTINATION
    # -------------------------------------------------

    print("Selecting destination...")

    destination = page.get_by_label("Where to?")

    destination.click()

    page.keyboard.type("LIS")

    page.wait_for_timeout(1500)

    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    page.wait_for_timeout(2000)

    # -------------------------------------------------
    # DEPARTURE
    # -------------------------------------------------

    print("Entering departure date...")

    departure = page.get_by_role(
        "textbox",
        name="Departure"
    ).first

    departure.click()

    page.keyboard.press("Meta+A")

    page.keyboard.type("09/01/2026")

    page.keyboard.press("Enter")

    page.wait_for_timeout(1500)

    # -------------------------------------------------
    # RETURN
    # -------------------------------------------------

    print("Entering return date...")

    return_box = page.get_by_role(
        "textbox",
        name="Return"
    ).first

    return_box.click()

    page.keyboard.press("Meta+A")

    page.keyboard.type("09/15/2026")

    page.keyboard.press("Enter")

    page.wait_for_timeout(3000)

    print("\n============================")
    print("CURRENT FORM VALUES")
    print("============================")

    print("Origin      :", origin.input_value())
    print("Destination :", destination.input_value())
    print("Departure   :", departure.input_value())
    print("Return      :", return_box.input_value())

    print("============================\n")

    page.screenshot(path="debug_form.png", full_page=True)

    print("Screenshot saved as debug_form.png")

    page.wait_for_timeout(15000)

    browser.close()