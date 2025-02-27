#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time
import webbrowser
import argparse
import random
import os

# Importing helper functions from playwright_sniper.py
from playwright_sniper import connect_to_browser, logger, DEFAULT_TIMEOUT, DEFAULT_DEBUG_PORT

# Default target option that can be overridden via command line or config file
DEFAULT_TARGET_OPTION = "zreik.blanc"

# Try to load saved Steam username if it exists
STEAM_USERNAME_FILE = "steam_username.txt"
if os.path.exists(STEAM_USERNAME_FILE):
    try:
        with open(STEAM_USERNAME_FILE, 'r') as f:
            saved_username = f.read().strip()
            if saved_username:
                DEFAULT_TARGET_OPTION = saved_username
                logger.info(f"Loaded saved Steam username: {DEFAULT_TARGET_OPTION}")
    except Exception as e:
        logger.warning(f"Could not load saved Steam username: {e}")

def save_steam_username(username):
    """Save the Steam username to a config file for future use"""
    try:
        with open(STEAM_USERNAME_FILE, 'w') as f:
            f.write(username)
        logger.info(f"Saved Steam username: {username}")
        return True
    except Exception as e:
        logger.error(f"Could not save Steam username: {e}")
        return False

def snipe_auto(url, listing_no, target_option=DEFAULT_TARGET_OPTION, quantity=None, max_retries=3, headless=False, browser_name="arc", debug_port=DEFAULT_DEBUG_PORT):
    """Opens the product page, adds item to cart, then in the cart page selects options and completes purchase.
    If quantity is provided, it subtracts 1 from it on a successful purchase and returns the updated quantity in the message.
    
    Args:
        url (str): The product URL
        listing_no (str): The listing number to identify the product page
        target_option (str): The option to select in the cart (e.g. "your steam username")
        quantity (int, optional): Number of items to track for purchase
        max_retries (int): Maximum number of retries for various operations
        headless (bool): Whether to run in headless mode
        browser_name (str): Name of the browser to use
        debug_port (int): Port to use for browser debugging
    
    Returns:
        tuple: (success_bool, message_str)
    """
    # Performance tracking
    performance = {
        "start_time": time.time(),
        "steps": {}
    }
    
    def track_step(step_name):
        performance["steps"][step_name] = {
            "start": time.time()
        }
        return step_name
    
    def complete_step(step_name):
        if step_name in performance["steps"]:
            step = performance["steps"][step_name]
            step["end"] = time.time()
            step["duration"] = step["end"] - step["start"]
            logger.info(f"Step '{step_name}' completed in {step['duration']:.2f}s")
        
    # Open product page in default browser (for user feedback) if not in headless mode
    if not headless:
        webbrowser.open(url)

    with sync_playwright() as p:
        browser = None
        try:
            # Use improved connection logic from playwright_sniper.py
            current_step = track_step("connect_to_browser")
            logger.info(f"Connecting to {browser_name} on port {debug_port} for auto-sniping...")
            browser = connect_to_browser(p, browser_name, debug_port)
            complete_step(current_step)
            
            if not browser:
                return False, f"Failed to connect to {browser_name}. Please restart it manually."

            current_step = track_step("find_product_page")
            context = browser.contexts[0]
            target_page = None
            
            # Locate the product page containing the listing_no
            for _ in range(max_retries):
                for page in context.pages:
                    if listing_no in page.url:
                        target_page = page
                        break
                if target_page:
                    break
                time.sleep(0.1)
            complete_step(current_step)
            
            # If page not found in existing tabs, open it directly
            if not target_page:
                current_step = track_step("open_new_page")
                logger.info("Product page not found in existing tabs, opening new page.")
                target_page = context.new_page()
                # Use faster page load strategy
                target_page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
                complete_step(current_step)

            target_page.set_viewport_size({"width": 1200, "height": 1080})
            target_page.bring_to_front()

            # Set default timeout for all operations on this page
            target_page.set_default_timeout(DEFAULT_TIMEOUT)

            # Attempt to click the add-to-cart button using evaluation with shorter timeout
            current_step = track_step("click_add_to_cart")
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
                    button = target_page.wait_for_selector(
                        "button.btn.btn-bng-white.btn-lg.font-weight-bold.w-100", 
                        timeout=DEFAULT_TIMEOUT, 
                        state='visible'
                    )
                    if button and button.is_enabled():
                        button.click(timeout=DEFAULT_TIMEOUT)
                        logger.info("Add-to-cart button clicked after waiting.")
                    else:
                        complete_step(current_step)
                        return False, "Add-to-cart button not clickable."
                except Exception as e:
                    complete_step(current_step)
                    return False, f"Could not click add-to-cart button: {e}"
            else:
                logger.info("Add-to-cart button clicked via JavaScript.")
            complete_step(current_step)

            # No longer closing the product page (keeping it open)
            logger.info("Product added to cart - keeping product page open")

            # Brief wait for cart to update
            time.sleep(0.5)
            
            # Open a new page for the cart
            current_step = track_step("open_cart_page")
            cart_page = context.new_page()
            # Use faster load strategy
            cart_page.goto("https://www.bynogame.com/en/cart", wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
            cart_page.set_viewport_size({"width": 1200, "height": 1080})
            complete_step(current_step)
            
            # Click the 'Seçiniz' element (a div containing the text 'Seçiniz')
            try:
                logger.info("Attempting to find and click 'Seçiniz' dropdown...")
                # Prioritize the selector that worked in logs
                selectors = [
                    ".dropdown-header span:has-text('Seçiniz')",
                    ".dropdown.cursor-pointer.bg-white",
                    "div.dropdown.cursor-pointer"
                ]
                
                seciniz = None
                for selector in selectors:
                    try:
                        seciniz = cart_page.wait_for_selector(selector, timeout=DEFAULT_TIMEOUT)
                        if seciniz:
                            logger.info(f"Found 'Seçiniz' using selector: {selector}")
                            break
                    except:
                        continue
                
                if not seciniz:
                    # JavaScript approach as a backup
                    logger.info("Trying JavaScript approach to find Seçiniz dropdown...")
                    seciniz_exists = cart_page.evaluate("""
                    () => {
                        const elements = Array.from(document.querySelectorAll('span')).filter(el => 
                            el.textContent.trim() === 'Seçiniz');
                        if (elements.length > 0) {
                            const clickTarget = elements[0].closest('.dropdown') || elements[0].parentElement;
                            if (clickTarget) {
                                clickTarget.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    """)
                    if seciniz_exists:
                        logger.info("'Seçiniz' found and clicked via JavaScript.")
                        seciniz = True
                    else:
                        return False, "Could not find 'Seçiniz' dropdown"
                
                # Only click if we found it via selectors (not JS)
                if seciniz and seciniz is not True:
                    # Log the HTML structure for debugging
                    cart_page.evaluate("""
                    () => {
                        const secinizEls = Array.from(document.querySelectorAll('span')).filter(
                            el => el.textContent.trim() === 'Seçiniz'
                        );
                        if (secinizEls.length > 0) {
                            console.log('Found Seçiniz element:', secinizEls[0]);
                        }
                    }
                    """)
                    
                    seciniz.click()
                    logger.info("'Seçiniz' dropdown clicked successfully.")
            except Exception as e:
                return False, f"Could not click 'Seçiniz': {e}"

            # Click the target option element using the successful JavaScript approach
            try:
                logger.info(f"Attempting to select option '{target_option}'...")
                
                # Give the dropdown menu time to fully appear
                time.sleep(0.5)
                
                # Use the JavaScript approach that worked in logs
                option_selected = cart_page.evaluate(f"""
                () => {{
                    const targetText = "{target_option}";
                    
                    // Try to find elements containing exact text
                    let elements = Array.from(document.querySelectorAll('li, span, div, a')).filter(el => 
                        el.textContent.trim() === targetText);
                        
                    // If not found, try less strict matching
                    if (elements.length === 0) {{
                        elements = Array.from(document.querySelectorAll('li, span, div, a')).filter(el => 
                            el.textContent.trim().includes(targetText));
                    }}
                    
                    // Click the first match found
                    if (elements.length > 0) {{
                        elements[0].click();
                        return true;
                    }}
                    
                    // Try dropdown items as backup
                    const dropdownItems = Array.from(document.querySelectorAll('.dropdown-item, li'));
                    for (const item of dropdownItems) {{
                        if (item.textContent.trim() === targetText || item.textContent.trim().includes(targetText)) {{
                            item.click();
                            return true;
                        }}
                    }}
                    
                    return false;
                }}
                """)
                
                if option_selected:
                    logger.info(f"'{target_option}' option selected successfully via JavaScript.")
                else:
                    # Only if JS approach fails, try a few selectors as backup
                    option_selectors = [
                        f"span:has-text('{target_option}')",
                        f"li:has-text('{target_option}')"
                    ]
                    
                    target_option_element = None
                    for selector in option_selectors:
                        try:
                            target_option_element = cart_page.wait_for_selector(
                                selector, 
                                timeout=DEFAULT_TIMEOUT
                            )
                            if target_option_element:
                                target_option_element.click()
                                logger.info(f"Found and clicked option '{target_option}' using selector.")
                                break
                        except:
                            continue
                    
                    if not target_option_element and not option_selected:
                        # Take a screenshot for debugging
                        screenshot_path = f"dropdown_screenshot_{int(time.time())}.png"
                        cart_page.screenshot(path=screenshot_path)
                        logger.info(f"Taking screenshot of dropdown to {screenshot_path}")
                        return False, f"Could not find option '{target_option}'"
            except Exception as e:
                return False, f"Error selecting '{target_option}': {e}"

            # Click the 'Checkout' button - focusing on the method that worked
            try:
                logger.info("Searching for 'Checkout' button...")
                # Prioritize the selector that worked in logs
                checkout_selectors = [
                    "button:has-text('Checkout')",
                    "button:has-text('Tamamla')",  # Turkish version
                    ".btn-checkout"
                ]
                
                checkout_button = None
                for selector in checkout_selectors:
                    try:
                        checkout_button = cart_page.wait_for_selector(selector, timeout=DEFAULT_TIMEOUT)
                        if checkout_button:
                            logger.info(f"Found 'Checkout' button using selector: {selector}")
                            break
                    except:
                        continue
                
                if not checkout_button:
                    screenshot_path = f"cart_screenshot_{int(time.time())}.png"
                    cart_page.screenshot(path=screenshot_path)
                    logger.info(f"Could not find checkout button, saved screenshot to {screenshot_path}")
                    return False, "Could not find 'Checkout' button"
                
                checkout_button.click()
                logger.info("'Checkout' button clicked successfully.")
                
                # Don't wait for navigation or try to verify - just consider it done
                logger.info("Checkout process complete. Waiting 5 seconds before closing pages...")
                
                # Wait 5 seconds before closing pages
                time.sleep(5)
                
                # Close both the product page and checkout page
                try:
                    target_page.close()
                    logger.info("Product page closed.")
                except Exception as page_err:
                    logger.warning(f"Could not close product page: {page_err}")
                    
                try:
                    cart_page.close()
                    logger.info("Checkout page closed.")
                except Exception as page_err:
                    logger.warning(f"Could not close checkout page: {page_err}")
                
            except Exception as e:
                # Take a screenshot to help with debugging
                try:
                    screenshot_path = f"error_screenshot_{int(time.time())}.png"
                    cart_page.screenshot(path=screenshot_path)
                    logger.error(f"Error during checkout, saved screenshot to {screenshot_path}")
                except:
                    pass
                return False, f"Could not click 'Checkout': {e}"

            # Log performance summary at the end
            total_duration = time.time() - performance["start_time"]
            logger.info(f"Total sniping process took {total_duration:.2f}s")
            
            # Include performance data in success message for debugging
            if quantity is not None:
                new_quantity = quantity - 1
                return True, f"Purchase complete. Remaining quantity: {new_quantity}"
            return True, "Purchase complete."
        except Exception as e:
            # Log performance data even on failure
            if "start_time" in performance:
                total_duration = time.time() - performance["start_time"]
                logger.error(f"Sniping process failed after {total_duration:.2f}s: {e}")
            
            logger.error(f"Error in snipe_auto: {e}")
            return False, f"Error: {e}"
        finally:
            # Don't close the browser as it might be used by other processes
            pass


if __name__ == "__main__":
    # Setup command line argument parsing
    parser = argparse.ArgumentParser(description='Auto-sniping tool for ByNoGame')
    parser.add_argument('url', type=str, help='URL of the product page')
    parser.add_argument('listing_no', type=str, help='Listing number to identify the product page')
    parser.add_argument('--target', '-t', dest='target_option', type=str, default=DEFAULT_TARGET_OPTION,
                        help=f'Target option to select in cart (default: {DEFAULT_TARGET_OPTION})')
    parser.add_argument('--quantity', '-q', type=int, help='Track quantity of items purchased')
    parser.add_argument('--retries', '-r', type=int, default=3, help='Maximum number of retries for operations')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode without opening browser windows')
    parser.add_argument('--browser', '-b', type=str, default="arc", 
                        choices=["arc", "chrome", "edge"], help='Browser to use (default: arc)')
    parser.add_argument('--debug-port', type=int, default=DEFAULT_DEBUG_PORT,
                        help=f'Port to use for browser debugging (default: {DEFAULT_DEBUG_PORT})')
    parser.add_argument('--random-port', action='store_true',
                        help='Use a random debugging port (9000-9999) to avoid conflicts')
    
    args = parser.parse_args()
    
    # Set a random debug port if requested
    debug_port = args.debug_port
    if args.random_port:
        debug_port = random.randint(9000, 9999)
        print(f"Using random debug port: {debug_port}")
    
    result, msg = snipe_auto(
        args.url, 
        args.listing_no, 
        target_option=args.target_option,
        quantity=args.quantity,
        max_retries=args.retries,
        headless=args.headless,
        browser_name=args.browser,
        debug_port=debug_port
    )
    print(msg) 