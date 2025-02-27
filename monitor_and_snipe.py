#!/usr/bin/env python3
import argparse
import time
import os
import signal
import sys
from datetime import datetime
import random

from playwright_sniper import monitor_product, logger, DEFAULT_TIMEOUT, DEFAULT_DEBUG_PORT
from snipe_auto import snipe_auto, DEFAULT_TARGET_OPTION, save_steam_username

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nStopping monitoring. Exiting...")
    sys.exit(0)

def auto_snipe_callback(url, listing_no, target_option, quantity, headless=False, browser_name="arc", debug_port=DEFAULT_DEBUG_PORT):
    """Callback function when product becomes available"""
    logger.info(f"Product {listing_no} available! Attempting to snipe...")
    
    start_time = time.time()
    max_attempts = 2  # Maximum number of snipe attempts
    
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            logger.info(f"Attempt {attempt}/{max_attempts} to snipe product...")
            time.sleep(2)  # Wait before retry
            
        success, message = snipe_auto(
            url, 
            listing_no, 
            target_option=target_option,
            quantity=quantity,
            headless=headless,
            browser_name=browser_name,
            debug_port=debug_port
        )
        
        if success:
            # Record successful snipe details
            duration = time.time() - start_time
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success_log = f"✅ SNIPE SUCCESSFUL at {timestamp} (took {duration:.2f}s)"
            
            if quantity is not None:
                success_log += f" - {quantity} remaining"
                
            logger.info(success_log)
            
            # Write to success log file
            with open("successful_snipes.log", "a") as f:
                f.write(f"{timestamp} - {listing_no} - {message}\n")
                
            # Play notification sound
            play_notification_sound()
            
            return True
        
        logger.error(f"SNIPE FAILED (Attempt {attempt}/{max_attempts}): {message}")
        
        # Only show retry message if we're not on the last attempt
        if attempt < max_attempts:
            logger.info(f"Retrying snipe in 2 seconds...")
    
    # All attempts have failed
    logger.error(f"❌ ALL SNIPE ATTEMPTS FAILED for {listing_no}")
    return False

def play_notification_sound():
    """Play a notification sound based on the platform"""
    try:
        if sys.platform == "darwin":  # macOS
            os.system("afplay /System/Library/Sounds/Glass.aiff")
        elif sys.platform == "win32":  # Windows
            import winsound
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        elif sys.platform == "linux":  # Linux
            os.system("aplay -q /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null")
    except Exception as e:
        logger.warning(f"Could not play notification sound: {e}")
        pass

def main():
    """Main function to run the monitor and sniper"""
    parser = argparse.ArgumentParser(description='Monitor a product and automatically snipe when available')
    parser.add_argument('url', type=str, help='URL of the product page')
    parser.add_argument('listing_no', type=str, help='Listing number to identify the product page')
    parser.add_argument('--target', '-t', dest='target_option', type=str, default=None,
                        help=f'Target option to select in cart (default: {DEFAULT_TARGET_OPTION})')
    parser.add_argument('--quantity', '-q', type=int, help='Track quantity of items purchased')
    parser.add_argument('--min-interval', type=int, default=5, help='Minimum seconds between checks (default: 5)')
    parser.add_argument('--max-interval', type=int, default=15, help='Maximum seconds between checks (default: 15)')
    parser.add_argument('--duration', type=int, help='Maximum monitoring duration in seconds')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode without opening browser windows')
    parser.add_argument('--browser', '-b', type=str, default="arc", 
                        choices=["arc", "chrome", "edge"], help='Browser to use (default: arc)')
    parser.add_argument('--recovery', action='store_true', 
                        help='Enable recovery mode - if monitoring fails, it will automatically restart')
    parser.add_argument('--debug-port', type=int, default=DEFAULT_DEBUG_PORT,
                        help=f'Port to use for browser debugging (default: {DEFAULT_DEBUG_PORT})')
    parser.add_argument('--random-port', action='store_true',
                        help='Use a random debugging port (9000-9999) to avoid conflicts')
    
    args = parser.parse_args()
    
    # Get Steam username (either from args or by prompting the user)
    target_option = args.target_option
    if target_option is None:
        try:
            target_option = input(f"Enter Steam username for Seçiniz menu (default: {DEFAULT_TARGET_OPTION}): ").strip()
            if not target_option:
                target_option = DEFAULT_TARGET_OPTION
            else:
                # Save the custom username for future use
                save_steam_username(target_option)
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(0)
        except Exception as e:
            logger.warning(f"Error getting username input: {e}")
            target_option = DEFAULT_TARGET_OPTION
    
    # Set a random debug port if requested
    debug_port = args.debug_port
    if args.random_port:
        debug_port = random.randint(9000, 9999)
        print(f"Using random debug port: {debug_port}")
    
    # Initialize signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"\n=== SKIN MONITOR AND SNIPER ===")
    print(f"Starting to monitor: {args.url}")
    print(f"Target option: {target_option}")
    print(f"Browser: {args.browser}")
    print(f"Debug port: {debug_port}")
    print(f"Check interval: {args.min_interval}-{args.max_interval} seconds")
    if args.duration:
        print(f"Maximum duration: {args.duration} seconds")
    print(f"Monitoring started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Press Ctrl+C to stop monitoring\n")
    
    # Create a callback function with the configured parameters
    def callback(url, listing_no):
        return auto_snipe_callback(
            url, 
            listing_no, 
            target_option, 
            args.quantity, 
            args.headless,
            args.browser,
            debug_port
        )
    
    # Monitoring with recovery if enabled
    while True:
        try:
            # Start monitoring
            result = monitor_product(
                args.url,
                args.listing_no,
                check_interval=(args.min_interval, args.max_interval),
                max_duration=args.duration,
                callback=callback,
                browser_name=args.browser,
                debug_port=debug_port
            )
            
            if not result:
                print("\nMonitoring ended without successful snipe.")
            else:
                print("\nMonitoring ended with successful snipe!")
            
            # If recovery not enabled or if successful, break out of the loop
            if not args.recovery or result:
                break
            
            # Otherwise restart monitoring
            print("\nRecovery mode enabled. Restarting monitoring in 5 seconds...")
            time.sleep(5)
            print("Restarting monitoring...")
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            if not args.recovery:
                print(f"\nError during monitoring: {e}")
                break
            
            # With recovery enabled, wait and restart
            print(f"\nError during monitoring: {e}")
            print("Recovery mode enabled. Restarting monitoring in 10 seconds...")
            time.sleep(10)
            print("Restarting monitoring...")

if __name__ == "__main__":
    main() 