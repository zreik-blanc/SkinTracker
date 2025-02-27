# SkinTracker

A Python-based tool for monitoring and automatically purchasing CS2 skins from ByNoGame marketplace. Features both a graphical user interface and command-line interface.

## Features

- Modern graphical user interface for easy skin tracking
- Real-time skin monitoring
- Automatic purchase when desired skins become available
- Multiple browser support (Arc, Chrome, Edge)
- Customizable monitoring intervals
- Support for tracking multiple skins
- Save favorite skins for later
- High discount tracking
- Recovery mode for continuous monitoring
- Notification sounds on successful snipes

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.7 or higher
- One of the supported browsers:
  - Arc Browser
  - Google Chrome
  - Microsoft Edge
- Git (for cloning the repository)
- System audio support (for notification sounds)

### System-Specific Requirements

#### Windows
- No additional requirements

#### macOS
- No additional requirements

#### Linux
- `aplay` or `paplay` for notification sounds:
  ```bash
  # For Ubuntu/Debian
  sudo apt-get install alsa-utils pulseaudio-utils
  ```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/SkinTracker.git
cd SkinTracker
```

2. Create and activate a virtual environment (recommended):
```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate

# Activate on macOS/Linux:
source .venv/bin/activate
```

3. Install dependencies and setup:
```bash
# Install Python packages
pip install -r requirements.txt

# Install required browsers for Playwright
playwright install
```

### Required Python Packages
The following packages will be automatically installed via requirements.txt:
- `playwright`: For browser automation and monitoring
- `requests`: For making HTTP requests to the marketplace
- `playsound`: For notification sounds on successful snipes

Additional built-in Python packages used:
- `tkinter`: For the graphical user interface (comes with Python)
- `json`: For data storage and manipulation
- `logging`: For debug and operation logging
- `webbrowser`: For opening links
- `datetime`, `time`: For timing and scheduling
- `os`, `sys`: For system operations

That's it! You're ready to start using SkinTracker.

## Usage

### Graphical Interface

To start the GUI application:

```bash
python Frontend.py
```

The GUI provides easy access to all features:
- Track multiple skins simultaneously
- Save favorite skins for later
- Monitor high-discount items
- Configure tracking settings
- View real-time monitoring status
- Manage tracked and saved skins
- Set up auto-buy preferences

#### Initial Setup
1. Close all instances of your preferred browser (Arc/Chrome/Edge)
2. Log into your ByNoGame account in your browser:
   - Open your browser manually
   - Go to https://www.bynogame.com
   - Log into your account
   - Make sure you stay logged in
3. Close the browser again
4. Launch the SkinTracker application:
   ```bash
   python Frontend.py
   ```
5. Click the "Config" button to set up your Steam username
6. Enter your Steam username in the dialog that appears
7. This username will be used for automatic checkout when sniping skins

#### Important Notes
- Always ensure you're logged into ByNoGame before starting the program
- The browser must be closed before starting SkinTracker
- Your login session will persist even after closing the browser
- If you get connection errors, try closing the browser and restarting the program

#### Main Features
- **Track Skins**: Add skins to monitor by entering their URL or listing number
- **Save Skins**: Save interesting skins for later monitoring
- **High Discount**: Monitor skins with significant price drops
- **Config**: Access settings including Steam username configuration
- **Recovery Mode**: Enable automatic recovery from monitoring errors
- **Browser Selection**: Choose between Arc, Chrome, or Edge

### Command Line Interface

Alternatively, you can use the command-line interface for direct monitoring:

```bash
python monitor_and_snipe.py <product_url> <listing_number> [options]
```

Example:
```bash
python monitor_and_snipe.py "https://www.bynogame.com/en/games/cs2/skin/123456" "123456"
```

### Command Line Options

- `--target` or `-t`: Specify Steam username for automatic checkout
- `--quantity` or `-q`: Track quantity of items to purchase
- `--min-interval`: Minimum seconds between checks (default: 5)
- `--max-interval`: Maximum seconds between checks (default: 15)
- `--duration`: Maximum monitoring duration in seconds
- `--headless`: Run in headless mode without opening browser windows
- `--browser` or `-b`: Choose browser (arc/chrome/edge, default: arc)
- `--recovery`: Enable recovery mode for continuous monitoring
- `--debug-port`: Port for browser debugging (default: 9223)
- `--random-port`: Use a random debugging port to avoid conflicts

Example with options:
```bash
python monitor_and_snipe.py "https://www.bynogame.com/en/games/cs2/skin/123456" "123456" --target "your_steam_username" --min-interval 3 --max-interval 10 --browser chrome --recovery
```

### Browser Setup

1. For Arc Browser:
   - Make sure Arc is installed in the default location
   - Close any existing Arc instances before running the script

2. For Chrome:
   - Ensure Google Chrome is installed
   - The script will automatically configure Chrome for automation

3. For Edge:
   - Ensure Microsoft Edge is installed
   - The script will automatically configure Edge for automation

## Troubleshooting

### Common Issues

1. **Browser Connection Issues**
   - Close all instances of the browser and try again
   - Use the `--random-port` option to avoid port conflicts
   - Try a different browser using the `--browser` option

2. **Monitoring Errors**
   - Enable recovery mode with `--recovery` flag
   - Adjust check intervals using `--min-interval` and `--max-interval`
   - Check your internet connection

3. **Purchase Failures**
   - Verify your Steam username is correct
   - Ensure you're logged into ByNoGame in your browser
   - Check if the item is still available

4. **Sound Notification Issues**
   - On Linux: Ensure `alsa-utils` or `pulseaudio-utils` is installed
   - On Windows/macOS: Ensure system audio is working
   - Check system volume and unmute if necessary

### Debug Logs

The script creates log files:
- `sniper.log`: Contains detailed operation logs
- `successful_snipes.log`: Records successful purchases

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Please use responsibly and in accordance with ByNoGame's terms of service.
