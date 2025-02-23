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
    webbrowser.open(url)
    
    with sync_playwright() as p:
        browser = None
        try:
            try:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            except:
                start_arc_browser()
                time.sleep(1)
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            context = browser.contexts[0]
            
            # Quick page finding
            max_retries = 5
            target_page = None
            
            for _ in range(max_retries):
                for page in context.pages:
                    if listing_no in page.url:
                        target_page = page
                        break
                if target_page:
                    break
                time.sleep(0.2)
            
            if not target_page:
                return False, "Could not find product page"
            
            # Set wider viewport for better visibility of right-side content
            target_page.set_viewport_size({"width": 1200, "height": 1080})
            target_page.evaluate("""
                () => {
                    // Scroll to show right side of page content
                    const pageWidth = document.documentElement.scrollWidth;
                    window.scrollTo(Math.max(0, pageWidth - 1200), 0);
                    // Position window on right side of screen
                    const screenWidth = window.screen.availWidth;
                    window.moveTo(screenWidth - 1200, 0);
                    window.resizeTo(1200, window.outerHeight);
                }
            """)
            target_page.bring_to_front()
            
            # Rapid polling for button with timeout
            start_time = time.time()
            timeout = 10  # 10 seconds total timeout
            poll_interval = 0.3  # Check every 0.3 seconds
            
            while time.time() - start_time < timeout:
                # Try direct JavaScript click first (fastest method)
                try:
                    clicked = target_page.evaluate("""
                    () => {
                        // Try exact button match first
                        const exactButton = document.querySelector('button.btn.btn-bng-white.btn-lg.font-weight-bold.w-100');
                        if (exactButton && !exactButton.disabled) {
                            exactButton.click();
                            return true;
                        }
                        
                        // Fallback to other common patterns
                        const patterns = [
                            '.btn-bng-white',
                            'button[style*="height:50px"]',
                            'button.btn.btn-lg.w-100',
                            'button.font-weight-bold'
                        ];
                        
                        for (const pattern of patterns) {
                            const btn = document.querySelector(pattern);
                            if (btn && !btn.disabled && 
                                btn.textContent.includes('Add To Cart') || 
                                btn.textContent.includes('Sepete Ekle')) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    """)
                    if clicked:
                        time.sleep(0.2)
                        webbrowser.open("https://www.bynogame.com/en/cart")
                        return True, "Please check your cart in the browser"
                except:
                    pass
                
                # Fallback to Playwright selectors
                selectors = [
                    "button.btn-bng-white",
                    "button.btn.btn-lg.w-100",
                    'button:has-text("Add To Cart")',
                    'button:has-text("Sepete Ekle")',
                    'button[style*="height:50px"]'
                ]
                
                for selector in selectors:
                    try:
                        button = target_page.wait_for_selector(selector, timeout=300, state='visible')
                        if button and button.is_enabled():
                            button.click(timeout=1000)
                            time.sleep(0.2)  # Minimal wait
                            webbrowser.open("https://www.bynogame.com/en/cart")
                            return True, "Please check your cart in the browser"
                    except:
                        continue
                
                time.sleep(poll_interval)
            
            return False, "Timeout: Could not find or click add to cart button within 10 seconds"
            
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
