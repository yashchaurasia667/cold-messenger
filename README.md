# Cold Message Drafter

A command-line tool that extracts business names from Google Maps URLs and uses the Gemini API to automatically draft personalized cold outreach messages. It can also extract phone numbers and automatically message them on WhatsApp Web.

## Features
- **URL Resolution**: Extracts accurate business names even from shortened Google Maps links.
- **Smart Phone Extraction**: Uses local Regex and Gemini to pull valid phone numbers from the business's Maps page, optimizing heavily for tokens.
- **WhatsApp Integration**: Can automatically open WhatsApp Web to send your custom drafted message.
- **API Optimized**: Merges AI requests into structured JSON calls and includes a built-in delay to avoid hitting Gemini's free tier rate limits (5 RPM).
- **Auto-Saving**: Automatically saves each drafted message locally in an `output/` directory.

## Setup

1. **Install Dependencies:**
   Make sure you have Python 3 installed. Then, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
   *(If you are on Linux, you may need to use `python3 -m pip install -r requirements.txt`)*

2. **Set your API Key:**
   You need a Google Gemini API key to generate the messages. Get one from Google AI Studio.
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

## Usage

### Basic Usage (Single URL)
You can draft a message for a single Google Maps link:
```bash
python3 cold_messenger.py -u "https://www.google.com/maps/place/The+Ancestry+-+A+Cafe+and+Eatery/..."
```

### Multiple URLs from a File
Create a `.txt` file containing Google Maps URLs separated by newlines, then run:
```bash
python3 cold_messenger.py -f links.txt
```

### Adding Context (Your Pitch)
You can provide specific context on what your message is about (e.g., offering web design, social media marketing, etc.).
**Inline:**
```bash
python3 cold_messenger.py -f links.txt -c "I am offering a free social media audit"
```
**From a file (Recommended):**
This avoids shell string parsing errors when using multiple words/newlines.
```bash
python3 cold_messenger.py -f links.txt -C context.txt
```

### WhatsApp Auto-Messaging
To automatically scrape the business's phone number and send the drafted message via WhatsApp Web, add the `--whatsapp` (or `-w`) flag:
```bash
python3 cold_messenger.py -f links.txt -C context.txt --whatsapp
```
*Note: Make sure your default browser is open and already logged into WhatsApp Web before running this.*

### Rate Limits
To respect Gemini API's free tier rate limits (5 requests per minute), the script waits 12 seconds between processing each URL by default. You can change this using `--delay`:
```bash
python3 cold_messenger.py -f links.txt --delay 15
```

### Output
The script will automatically create an `output/` directory and save each generated message to a separate `.txt` file named after the business.

## Help
Run `python3 cold_messenger.py -h` for all available options.
