from playwright.sync_api import sync_playwright
import time
import subprocess
import os
import webbrowser
import urllib.request, urllib.error
import platform
import re
import random
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sniper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sniper")

# Browser detection and configuration
SUPPORTED_BROWSERS = {
    "arc": {
        "darwin": "/Applications/Arc.app/Contents/MacOS/Arc",
        "linux": None,  # Arc is not available on Linux
        "win32": os.path.expanduser("~\\AppData\\Local\\Arc\\app-*\\Arc.exe"),
    },
    "chrome": {
        "darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "linux": "/usr/bin/google-chrome",
        "win32": os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
    },
    "edge": {
        "darwin": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "linux": "/usr/bin/microsoft-edge",
        "win32": os.path.expanduser("~\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"),
    }
}

DEFAULT_DEBUG_PORT = 9223
# Reduce default connection timeout from 30s to 5s to prevent long hangs
DEFAULT_TIMEOUT = 5000  # milliseconds

def detect_platform():
    """Detect the current operating system platform"""
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "win32"
    else:
        raise SystemError(f"Unsupported operating system: {system}")

def get_browser_path(browser_name):
    """Get the path to the browser executable for the current platform"""
    current_platform = detect_platform()
    
    if browser_name not in SUPPORTED_BROWSERS:
        raise ValueError(f"Unsupported browser: {browser_name}. Supported browsers: {list(SUPPORTED_BROWSERS.keys())}")
    
    browser_path = SUPPORTED_BROWSERS[browser_name].get(current_platform)
    if not browser_path:
        raise ValueError(f"{browser_name} is not supported on {current_platform}")
    
    # Handle wildcard paths (mainly for Windows)
    if "*" in browser_path:
        import glob
        matches = glob.glob(browser_path)
        if matches:
            # Sort to get the latest version
            matches.sort(reverse=True)
            return matches[0]
        else:
            raise FileNotFoundError(f"Could not find {browser_name} at path: {browser_path}")
    
    # Check if the browser exists
    if not os.path.exists(browser_path):
        raise FileNotFoundError(f"Could not find {browser_name} at path: {browser_path}")
    
    return browser_path

def is_browser_running(browser_name):
    """Check if the browser is already running"""
    platform_name = detect_platform()
    
    if platform_name == "darwin":
        # For macOS
        try:
            if browser_name == "arc":
                proc = subprocess.run(["pgrep", "-f", "Arc.app/Contents/MacOS/Arc"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elif browser_name == "chrome":
                proc = subprocess.run(["pgrep", "-f", "Google Chrome.app/Contents/MacOS/Google Chrome"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elif browser_name == "edge":
                proc = subprocess.run(["pgrep", "-f", "Microsoft Edge.app/Contents/MacOS/Microsoft Edge"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return bool(proc.stdout.strip())
        except Exception:
            return False
    elif platform_name == "linux":
        # For Linux
        try:
            if browser_name == "chrome":
                proc = subprocess.run(["pgrep", "-f", "google-chrome"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elif browser_name == "edge":
                proc = subprocess.run(["pgrep", "-f", "microsoft-edge"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return bool(proc.stdout.strip())
        except Exception:
            return False
    elif platform_name == "win32":
        # For Windows
        try:
            # Using tasklist to check running processes
            if browser_name == "arc":
                proc = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Arc.exe"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elif browser_name == "chrome":
                proc = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elif browser_name == "edge":
                proc = subprocess.run(["tasklist", "/FI", "IMAGENAME eq msedge.exe"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return "No tasks are running" not in proc.stdout
        except Exception:
            return False
    
    return False

def start_browser(browser_name="arc", debug_port=DEFAULT_DEBUG_PORT):
    """Start a browser with remote debugging enabled"""
    try:
        browser_path = get_browser_path(browser_name)
        platform_name = detect_platform()
        
        # Check if debug endpoint is available first
        if wait_for_debug_endpoint(timeout=2, port=debug_port):
            logger.info(f"Debug endpoint is available on port {debug_port}.")
            return True
        
        # Check if the browser is already running
        if is_browser_running(browser_name):
            logger.info(f"{browser_name} is already running, but debug endpoint is not available.")
            # If browser is running but debug endpoint isn't available, we need to restart it
            # First try to close existing instance to avoid duplicate processes
            if platform_name == "darwin":
                os.system(f"pkill -f '{browser_name}'")
            elif platform_name == "linux":
                os.system(f"pkill -f '{browser_name}'")
            elif platform_name == "win32":
                os.system(f"taskkill /F /IM {browser_name}.exe")
            
            time.sleep(1)  # Brief pause to ensure it closes
        
        # Build the command to start the browser with debugging
        if platform_name == "darwin":
            # For macOS
            if browser_name == "arc":
                cmd = f"{browser_path} --no-startup-window --remote-debugging-port={debug_port} --remote-debugging-address=127.0.0.1 &"
            else:
                cmd = f"{browser_path} --remote-debugging-port={debug_port} --remote-debugging-address=127.0.0.1 --no-first-run --no-default-browser-check &"
        elif platform_name == "linux":
            # For Linux
            cmd = f"{browser_path} --remote-debugging-port={debug_port} --remote-debugging-address=127.0.0.1 --no-first-run --no-default-browser-check &"
        elif platform_name == "win32":
            # For Windows
            cmd = f'start "" "{browser_path}" --remote-debugging-port={debug_port} --remote-debugging-address=127.0.0.1 --no-first-run --no-default-browser-check'
        
        # Execute the command
        logger.info(f"Starting {browser_name} with debugging on port {debug_port}")
        os.system(cmd)
        
        # Wait for the browser to start with shorter timeout
        wait_time = 5  # seconds
        if wait_for_debug_endpoint(timeout=wait_time, port=debug_port):
            logger.info(f"{browser_name} started successfully with debugging enabled.")
            return True
        else:
            logger.error(f"Timeout waiting for {browser_name} to start with debugging.")
            return False
            
    except Exception as e:
        logger.error(f"Error starting {browser_name}: {e}")
        return False

def wait_for_debug_endpoint(timeout=10, port=DEFAULT_DEBUG_PORT):
    """Wait until the remote debugging endpoint is available."""
    endpoint = f"http://127.0.0.1:{port}/json/version"
    start_time = time.time()
    
    # Use shorter intervals for faster checking
    interval = 0.05  # 50ms between checks
    
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(endpoint, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(interval)
    return False

def connect_to_browser(p, browser_name="arc", debug_port=DEFAULT_DEBUG_PORT, max_retries=3):
    """Connect to a browser using the Playwright CDP protocol with improved performance"""
    browser = None
    last_exception = None
    
    # First verify the debug endpoint is available before attempting connection
    if not wait_for_debug_endpoint(timeout=2, port=debug_port):
        logger.warning(f"Debug endpoint not available on port {debug_port}")
        
        # Try to start or restart the browser
        if not restart_browser_forcefully(browser_name, debug_port):
            logger.error(f"Failed to start {browser_name} with debugging enabled")
            return None
        
        # Wait a bit longer for browser to fully initialize
        time.sleep(2)
        
        # Verify endpoint again after restart
        if not wait_for_debug_endpoint(timeout=3, port=debug_port):
            logger.error(f"Debug endpoint still not available after browser restart")
            return None
    else:
        # Even if debug endpoint is available, try a browser restart if we've had recent connection issues
        # This helps when the browser is in a zombie state (port open but not responding properly)
        logger.info(f"Debug endpoint is available on port {debug_port}, checking browser health...")
        
        # Try a quick connection first to see if it's healthy
        try:
            browser = p.chromium.connect_over_cdp(
                f"http://127.0.0.1:{debug_port}",
                timeout=3000  # Very short timeout for quick health check
            )
            logger.info(f"Browser connection is healthy.")
            return browser
        except Exception as e:
            logger.warning(f"Browser seems to be in a bad state despite open port: {e}")
            # Force restart the browser to clear the zombie state
            if not restart_browser_forcefully(browser_name, debug_port):
                logger.error(f"Failed to restart {browser_name}")
                return None
            
            time.sleep(2)  # Wait longer after a forceful restart
    
    # Now try connecting with shorter timeout
    for retry in range(max_retries):
        try:
            logger.info(f"Connection attempt {retry+1}...")
            # Reduced timeout to avoid long waits when connection fails
            browser = p.chromium.connect_over_cdp(
                f"http://127.0.0.1:{debug_port}",
                timeout=DEFAULT_TIMEOUT
            )
            logger.info(f"Connected successfully to {browser_name}.")
            return browser
        except Exception as e:
            last_exception = e
            logger.warning(f"Connection attempt {retry+1} failed: {e}")
            
            if retry < max_retries - 1:
                # If connection is failing despite endpoint being available, 
                # the browser might be in a bad state - restart it
                if retry >= 1:  # Only force restart after the first retry
                    logger.info(f"Forcing browser restart after failed connection...")
                    restart_browser_forcefully(browser_name, debug_port)
                    time.sleep(2)  # Longer wait after forceful restart
                else:
                    # Brief pause between regular retries
                    time.sleep(1)
    
    logger.error(f"Failed to connect to {browser_name} after {max_retries} attempts. Last error: {last_exception}")
    return None

def restart_browser_forcefully(browser_name, debug_port=DEFAULT_DEBUG_PORT):
    """More aggressive browser restart, kills any processes and starts fresh"""
    platform_name = detect_platform()
    logger.info(f"Forcefully restarting {browser_name}...")
    
    # Step 1: Kill all related processes
    try:
        if platform_name == "darwin":
            # For macOS - more aggressive process killing
            if browser_name == "arc":
                os.system("pkill -9 -f 'Arc'")
            elif browser_name == "chrome":
                os.system("pkill -9 -f 'Google Chrome'")
            elif browser_name == "edge":
                os.system("pkill -9 -f 'Microsoft Edge'")
        elif platform_name == "linux":
            # For Linux
            if browser_name == "chrome":
                os.system("pkill -9 -f 'chrome'")
            elif browser_name == "edge":
                os.system("pkill -9 -f 'edge'")
        elif platform_name == "win32":
            # For Windows - use /F for forceful termination
            if browser_name == "arc":
                os.system("taskkill /F /IM Arc.exe")
            elif browser_name == "chrome":
                os.system("taskkill /F /IM chrome.exe")
            elif browser_name == "edge":
                os.system("taskkill /F /IM msedge.exe")
    except Exception as e:
        logger.warning(f"Error killing processes: {e}")
    
    # Step 2: Make sure the debug port is cleared by killing any process using it
    try:
        if platform_name in ["darwin", "linux"]:
            os.system(f"lsof -ti tcp:{debug_port} | xargs kill -9 2>/dev/null || true")
    except Exception:
        pass
    
    # Step 3: Wait for processes to fully terminate
    time.sleep(2)
    
    # Step 4: Start a fresh browser instance
    return start_browser(browser_name, debug_port)

def monitor_product(url, listing_no, check_interval=(5, 15), max_duration=None, callback=None, browser_name="arc", debug_port=DEFAULT_DEBUG_PORT):
    """
    Monitor a product page for availability
    
    Args:
        url (str): The product URL to monitor
        listing_no (str): The listing number to identify the product
        check_interval (tuple): Random interval range in seconds between checks
        max_duration (int, optional): Maximum monitoring duration in seconds
        callback (function, optional): Function to call when product becomes available
                 Should take (url, listing_no) as arguments
        browser_name (str): Name of the browser to use
        debug_port (int): Port to use for browser debugging
    
    Returns:
        bool: True if product became available, False if timeout or error
    """
    logger.info(f"Starting to monitor product {listing_no} at {url} using {browser_name} on port {debug_port}")
    
    start_time = time.time()
    
    with sync_playwright() as p:
        browser = None
        try:
            # Connect to browser with shorter timeout
            browser = connect_to_browser(p, browser_name, debug_port)
            if not browser:
                logger.error(f"Failed to connect to {browser_name}. Please restart your browser manually.")
                return False
            
            context = browser.contexts[0]
            monitor_page = context.new_page()
            
            # Function to check availability
            def check_availability():
                try:
                    # Use networkidle2 instead of networkidle for faster loading
                    monitor_page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
                    
                    # Set the default timeout for all operations
                    monitor_page.set_default_timeout(DEFAULT_TIMEOUT)
                    
                    # Check if the add-to-cart button is available and enabled
                    button_available = monitor_page.evaluate("""
                    () => {
                        const btn = document.querySelector('button.btn.btn-bng-white.btn-lg.font-weight-bold.w-100');
                        return btn && !btn.disabled;
                    }
                    """)
                    
                    if button_available:
                        logger.info(f"Product {listing_no} is AVAILABLE!")
                        return True
                    else:
                        logger.info(f"Product {listing_no} is not available yet...")
                        return False
                except Exception as e:
                    logger.error(f"Error checking availability: {e}")
                    # If page navigation fails, try to reconnect to the browser
                    try:
                        browser = connect_to_browser(p, browser_name, debug_port)
                        if browser:
                            context = browser.contexts[0]
                            monitor_page = context.new_page()
                            logger.info("Successfully reconnected to browser after error")
                    except Exception:
                        pass
                    return False
            
            # Main monitoring loop
            while True:
                # Check if we've reached max duration
                if max_duration and (time.time() - start_time) > max_duration:
                    logger.info(f"Reached maximum monitoring duration of {max_duration} seconds")
                    return False
                
                # Check availability
                if check_availability():
                    # Product is available!
                    if callback:
                        logger.info("Calling the callback function")
                        callback(url, listing_no)
                    return True
                
                # Wait a random interval before next check to avoid detection
                wait_time = random.uniform(check_interval[0], check_interval[1])
                logger.info(f"Waiting {wait_time:.2f} seconds before next check")
                time.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            return False
        finally:
            # Don't close the browser as it might be used by other processes
            pass

def snipe_skin(url, listing_no, browser_name="arc", debug_port=DEFAULT_DEBUG_PORT):
    """Use Playwright to add skin to cart"""
    # Open in default browser for visual feedback
    webbrowser.open(url)
    
    with sync_playwright() as p:
        browser = None
        try:
            # Connect with improved connection logic and shorter timeout
            browser = connect_to_browser(p, browser_name, debug_port)
            if not browser:
                return False, "Failed to connect to browser"
            
            context = browser.contexts[0]
            
            # Try to find the product page in existing tabs
            max_retries = 3
            target_page = None
            
            for _ in range(max_retries):
                for page in context.pages:
                    if listing_no in page.url:
                        target_page = page
                        break
                if target_page:
                    break
                time.sleep(0.1)
            
            # If not found, open a new page
            if not target_page:
                logger.info("Product page not found in existing tabs, opening new page")
                target_page = context.new_page()
                # Use faster page load strategy
                target_page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
            
            # Setup viewport and focus
            target_page.set_viewport_size({"width": 1200, "height": 1080})
            target_page.bring_to_front()
            
            # Try to click the add-to-cart button with shorter timeout
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
                logger.info("Add-to-cart button clicked via JavaScript")
                webbrowser.open("https://www.bynogame.com/en/cart")
                return True, "Item added to cart. Please check your cart in the browser"
            
            # Fallback to Playwright clicking with shorter timeout
            try:
                button = target_page.wait_for_selector(
                    "button.btn.btn-bng-white.btn-lg.font-weight-bold.w-100",
                    timeout=DEFAULT_TIMEOUT,
                    state='visible'
                )
                if button and button.is_enabled():
                    button.click(timeout=DEFAULT_TIMEOUT)
                    logger.info("Add-to-cart button clicked via Playwright")
                    webbrowser.open("https://www.bynogame.com/en/cart")
                    return True, "Item added to cart. Please check your cart in the browser"
                else:
                    return False, "Add-to-cart button found but not clickable"
            except Exception as e:
                return False, f"Could not find or click add-to-cart button: {e}"
            
        except Exception as e:
            logger.error(f"Error in snipe_skin: {e}")
            return False, f"Error: {e}"
        finally:
            # Don't close the browser if we didn't create it
            pass

def setup_browser(browser_name="arc"):
    """Check if the selected browser is properly installed"""
    try:
        browser_path = get_browser_path(browser_name)
        return os.path.exists(browser_path)
    except Exception as e:
        logger.error(f"Error checking browser setup: {e}")
        return False

# Backward compatibility for legacy code
start_arc_browser = lambda: start_browser("arc")
