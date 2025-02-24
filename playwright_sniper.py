from playwright.sync_api import sync_playwright
import time
import subprocess
import os
import webbrowser
import urllib.request, urllib.error

def start_arc_browser():
    """Start Arc browser with remote debugging enabled"""
    try:
        # Check if Arc is already running by using pgrep
        proc = subprocess.run(["pgrep", "-f", "Arc.app/Contents/MacOS/Arc"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.stdout.strip():
            print("[DEBUG] Arc browser is already running.")
            if wait_for_debug_endpoint(10):
                print("[DEBUG] Remote debugging endpoint is available on the running instance.")
                return True
            else:
                print("[DEBUG] Remote debugging endpoint not available on the running instance. Please start Arc with remote debugging enabled.")
                return False
        else:
            arc_path = "/Applications/Arc.app/Contents/MacOS/Arc"
            debug_cmd = f"{arc_path} --no-startup-window --remote-debugging-port=9223 --remote-debugging-address=127.0.0.1 &"
            os.system(debug_cmd)
            time.sleep(1)  # wait for browser to start with remote debugging (optimized)
            return True
    except Exception as e:
        print(f"Error starting Arc: {e}")
        return False

def wait_for_debug_endpoint(timeout=10):
    """Wait until the remote debugging endpoint is available."""
    endpoint = "http://127.0.0.1:9223/json/version"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(endpoint, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False

def snipe_skin(url, listing_no):
    """Use Playwright to add skin to cart"""
    webbrowser.open(url)
    
    with sync_playwright() as p:
        browser = None
        try:
            try:
                print("[DEBUG] Attempting initial connection to port 9223...")
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9223")
                print("[DEBUG] Connected successfully to port 9223.")
            except Exception as e:
                print(f"[DEBUG] Initial connection to port 9223 failed with error: {e}")
                print("[DEBUG] Starting Arc browser...")
                if start_arc_browser():
                    print("[DEBUG] Arc browser started successfully. Waiting for remote debugging endpoint...")
                    if wait_for_debug_endpoint(10):
                        print("[DEBUG] Remote debugging endpoint is ready. Retrying connection to port 9223...")
                    else:
                        print("[DEBUG] Timeout waiting for remote debugging endpoint.")
                        return False, "Connection failed: remote debugging endpoint not ready."
                else:
                    print("[DEBUG] Arc browser failed to start.")
                    return False, "Arc browser failed to start"

                retry_count = 0
                connected = False
                while retry_count < 5 and not connected:
                    try:
                        time.sleep(0.5)  # optimized wait before retrying
                        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9223")
                        print("[DEBUG] Connection established on retry to port 9223.")
                        connected = True
                    except Exception as ex:
                        print(f"[DEBUG] Retry attempt {retry_count+1} failed with error: {ex}")
                        retry_count += 1
                if not connected:
                    print("[DEBUG] Could not establish connection after multiple retries.")
                    return False, "Connection failed after multiple retries"
            
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
