# SkinTracker

A Python-based tool for monitoring and automatically purchasing CS2 skins from ByNoGame marketplace.

## Features

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

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/SkinTracker.git
cd SkinTracker
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Required Packages

Create a `requirements.txt` file with the following dependencies:
```
playwright==1.41.0
requests==2.31.0
```

After creating the file, run:
```bash
pip install -r requirements.txt
```

Then install Playwright browsers:
```bash
playwright install
```

## Usage

### Basic Monitoring

To start monitoring a specific skin:

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
