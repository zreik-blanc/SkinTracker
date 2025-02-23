from playwright.sync_api import sync_playwright
import time
import subprocess
import os
import json
from tkinter import messagebox
import webbrowser

def start_arc_browser():
    """Start Arc browser with remote debugging enabled"""
    try:
        arc_path = "/Applications/Arc.app/Contents/MacOS/Arc"
        debug_cmd = f"{arc_path} --no-startup-window --remote-debugging-port=9222 &"
        os.system(debug_cmd)
        time.sleep(2)  # Reduced from 3
        return True
    except Exception as e:
        print(f"Error starting Arc: {e}")
        return False

def snipe_skin(url, listing_no):
    """Use Playwright to add skin to cart"""
    webbrowser.open(url)
    
    with sync_playwright() as p:
        browser = None
        try:
            try:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            except:
                start_arc_browser()
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            context = browser.contexts[0]
            
            # Quick page finding with shorter timeout
            max_retries = 3  # Reduced from 5
            target_page = None
            
            for _ in range(max_retries):
                for page in context.pages:
                    if listing_no in page.url:
                        target_page = page
                        break
                if target_page:
                    break
                time.sleep(0.1)  # Reduced from 0.2
            
            if not target_page:
                return False, "Could not find product page"
            
            # Simplified viewport setup - only essential parts
            target_page.set_viewport_size({"width": 1200, "height": 1080})
            target_page.bring_to_front()
            
            # Direct button click attempt with minimal retries
            try:
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
                if clicked:
                    webbrowser.open("https://www.bynogame.com/en/cart")
                    return True, "Please check your cart in the browser"
            except:
                pass
            
            # Single fallback attempt with exact selector
            try:
                button = target_page.wait_for_selector(
                    "button.btn.btn-bng-white.btn-lg.font-weight-bold.w-100",
                    timeout=2000,
                    state='visible'
                )
                if button and button.is_enabled():
                    button.click(timeout=1000)
                    webbrowser.open("https://www.bynogame.com/en/cart")
                    return True, "Please check your cart in the browser"
            except:
                return False, "Could not find or click add to cart button"
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return False, f"Error: {str(e)}"
        finally:
            if browser:
                browser.close()

def setup_browser():
    """Ensure browser is properly configured"""
    return os.path.exists("/Applications/Arc.app")
