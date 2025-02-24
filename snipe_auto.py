#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time
import subprocess
import os
import webbrowser
import urllib.request

# Importing helper functions from playwright_sniper.py
from playwright_sniper import start_arc_browser, wait_for_debug_endpoint

# Configurable target option for purchasing. Change this value to target a different option. This name must be in the cart page.
TARGET_OPTION = "Shroud"


def snipe_auto(url, listing_no):
    """Opens the product page, adds item to cart, then in the cart page selects options and completes purchase."""
    # Open product page in default browser (for user feedback)
    webbrowser.open(url)

    with sync_playwright() as p:
        browser = None
        try:
            print("[DEBUG] Attempting initial connection to port 9223...")
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9223")
                print("[DEBUG] Connected successfully to port 9223.")
            except Exception as e:
                print(f"[DEBUG] Initial connection failed: {e}")
                print("[DEBUG] Starting Arc browser...")
                if start_arc_browser():
                    print("[DEBUG] Arc browser started. Waiting for remote debugging endpoint...")
                    if wait_for_debug_endpoint(10):
                        print("[DEBUG] Remote debugging endpoint is ready.")
                    else:
                        print("[DEBUG] Timeout waiting for remote debugging endpoint.")
                        return False, "Connection failed: remote debugging endpoint not ready."
                else:
                    print("[DEBUG] Arc browser failed to start.")
                    return False, "Arc browser failed to start"

                # Retry connecting over CDP
                retry_count = 0
                connected = False
                while retry_count < 5 and not connected:
                    try:
                        time.sleep(0.5)
                        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9223")
                        print("[DEBUG] Connection established on retry to port 9223.")
                        connected = True
                    except Exception as ex:
                        print(f"[DEBUG] Retry attempt {retry_count+1} failed: {ex}")
                        retry_count += 1
                if not connected:
                    print("[DEBUG] Could not establish connection after multiple retries.")
                    return False, "Connection failed after multiple retries"

            context = browser.contexts[0]
            target_page = None
            # Locate the product page containing the listing_no
            for _ in range(3):
                for page in context.pages:
                    if listing_no in page.url:
                        target_page = page
                        break
                if target_page:
                    break
                time.sleep(0.1)
            if not target_page:
                return False, "Could not find product page"

            target_page.set_viewport_size({"width": 1200, "height": 1080})
            target_page.bring_to_front()

            # Attempt to click the add-to-cart button using evaluation
            clicked = target_page.evaluate("""
            () => {
                const btn = document.querySelector('button.btn.btn-bng-white.btn-lg.font-weight-bold.w-100');
                if (btn && !btn.disabled) {
                    btn.click();
                    return true;
                }
                return false;
            }
            """)
            if not clicked:
                try:
                    button = target_page.wait_for_selector("button.btn.btn-bng-white.btn-lg.font-weight-bold.w-100", timeout=2000, state='visible')
                    if button and button.is_enabled():
                        button.click(timeout=1000)
                        print("[DEBUG] Add-to-cart button clicked after waiting.")
                    else:
                        return False, "Add-to-cart button not clickable."
                except Exception as e:
                    return False, f"Could not click add-to-cart button: {e}"
            else:
                print("[DEBUG] Add-to-cart button clicked.")

            # Short wait to allow the cart update
            time.sleep(1)
            
            # Open a new page for the cart
            cart_page = context.new_page()
            cart_page.goto("https://www.bynogame.com/en/cart")
            cart_page.set_viewport_size({"width": 1200, "height": 1080})
            time.sleep(1)  # allow time for the cart page to load

            # Click the 'Seçiniz' element (a div containing the text 'Seçiniz')
            try:
                seciniz = cart_page.wait_for_selector("div:has-text('Seçiniz')", timeout=5000)
                seciniz.click()
                print("[DEBUG] 'Seçiniz' clicked.")
            except Exception as e:
                return False, f"Could not click 'Seçiniz': {e}"

            # Click the target option element (a span with class 'font-weight-bold' and text equal to TARGET_OPTION)
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    target_option = cart_page.wait_for_selector(f"span.font-weight-bold:has-text('{TARGET_OPTION}')", timeout=5000)
                    target_option.click()
                    print(f"[DEBUG] '{TARGET_OPTION}' clicked.")
                    break
                except Exception as e:
                    if attempt < max_attempts - 1:
                        try:
                            seciniz = cart_page.wait_for_selector("div:has-text('Seçiniz')", timeout=5000)
                            seciniz.click()
                            print("[DEBUG] 'Seçiniz' re-clicked to refresh page.")
                        except Exception as ex:
                            print(f"[DEBUG] Re-clicking 'Seçiniz' failed: {ex}")
                    else:
                        return False, f"Could not click '{TARGET_OPTION}': {e}"

            # Click the 'Checkout' button
            try:
                tamamla = cart_page.wait_for_selector("button:has-text('Checkout')", timeout=5000)
                tamamla.click()
                print("[DEBUG] 'Checkout' clicked.")
            except Exception as e:
                return False, f"Could not click 'Checkout': {e}"

            return True, "Purchase complete."
        except Exception as e:
            print("Error:", e)
            return False, f"Error: {e}"
        finally:
            if browser:
                browser.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: snipe_auto.py <URL> <listing_no>")
        sys.exit(1)
    url = sys.argv[1]
    listing_no = sys.argv[2]
    result, msg = snipe_auto(url, listing_no)
    print(msg) 