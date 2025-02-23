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
        # Don't kill existing Arc sessions, just try to connect first
        arc_path = "/Applications/Arc.app/Contents/MacOS/Arc"
        
        # Start Arc with debugging using a more reliable method
        debug_cmd = f"""
        osascript -e 'tell application "Arc" to quit'
        sleep 1
        {arc_path} --no-startup-window --remote-debugging-port=9222 &
        """
        
        os.system(debug_cmd)
        print("Started Arc with debugging port")
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"Error starting Arc: {e}")
        return False

def snipe_skin(url, listing_no):
    """Use Playwright to add skin to cart"""
    # Open product page in default browser first
    webbrowser.open(url)
    time.sleep(3)  # Increased wait time
    
    with sync_playwright() as p:
        browser = None
        try:
            # Try to connect to existing session
            try:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            except:
                start_arc_browser()
                time.sleep(2)
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            # Get all pages
            context = browser.contexts[0]
            pages = context.pages
            
            # Wait for a page that matches our URL
            max_retries = 10
            target_page = None
            
            for _ in range(max_retries):
                for page in context.pages:
                    if listing_no in page.url:
                        target_page = page
                        break
                if target_page:
                    break
                time.sleep(0.5)
            
            if not target_page:
                return False, "Could not find product page"
                
            print(f"Found page: {target_page.url}")
            
            # Wait for the page to be fully loaded
            target_page.wait_for_load_state('networkidle')
            
            # Try multiple button finding strategies
            button_found = False
            
            # Strategy 1: Direct text match
            try:
                button = target_page.get_by_text("Sepete Ekle", exact=True)
                if button.is_visible():
                    button.click()
                    button_found = True
                    print("Clicked button using text match")
            except:
                pass
                
            # Strategy 2: Role and text content
            if not button_found:
                try:
                    button = target_page.get_by_role("button", name="Sepete Ekle")
                    if button.is_visible():
                        button.click()
                        button_found = True
                        print("Clicked button using role")
                except:
                    pass
            
            # Strategy 3: JavaScript click
            if not button_found:
                try:
                    target_page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const cartButton = buttons.find(btn => 
                            btn.textContent.includes('Sepete') || 
                            btn.textContent.includes('Cart')
                        );
                        if (cartButton) cartButton.click();
                    }
                    """)
                    button_found = True
                    print("Clicked button using JavaScript")
                except:
                    pass
            
            if not button_found:
                return False, "Could not find or click add to cart button"
            
            # Wait for potential cart update
            time.sleep(2)
            webbrowser.open("https://www.bynogame.com/en/cart")
            return True, "Please check your cart in the browser"
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return False, f"Error: {str(e)}"
        finally:
            if browser:
                browser.close()

def setup_browser():
    """Ensure browser is properly configured"""
    # Install browser if needed
    os.system("playwright install chromium")
    
    # Make sure Arc is installed
    if not os.path.exists("/Applications/Arc.app"):
        messagebox.showerror("Error", "Arc browser not found. Please install Arc browser.")
        return False
    
    return True
