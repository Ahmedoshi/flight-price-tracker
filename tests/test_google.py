from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        slow_mo=500
    )

    page = browser.new_page()

    print("Opening Google Flights...")
    page.goto("https://www.google.com/travel/flights")

    page.wait_for_timeout(5000)

    # ----------------------------
    # Origin
    # ----------------------------
    print("Selecting origin...")
    page.get_by_label("Where from?").click()
    page.wait_for_timeout(1000)

    page.keyboard.press("Meta+A")
    page.keyboard.press("Backspace")

    page.keyboard.type("RUH")
    page.wait_for_timeout(2000)

    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    page.wait_for_timeout(1500)

    # ----------------------------
    # Destination
    # ----------------------------
    print("Selecting destination...")
    page.get_by_label("Where to?").click()
    page.wait_for_timeout(1000)

    page.keyboard.type("LIS")
    page.wait_for_timeout(2000)

    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    page.wait_for_timeout(5000)

    print("SUCCESS!")

    page.wait_for_timeout(10000)

    browser.close()