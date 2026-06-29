# Cold Message Drafter

A command-line tool that extracts business names from Google Maps URLs and uses the Gemini API to automatically draft personalized cold outreach messages.

## Setup

1. **Install Dependencies:**
   Make sure you have Python 3 installed. Then, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API Key:**
   You need a Google Gemini API key to generate the messages. Get one from Google AI Studio.
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

## Usage

### Single URL
You can draft a message for a single Google Maps link:
```bash
python cold_messenger.py -u "https://www.google.com/maps/place/The+Ancestry+-+A+Cafe+and+Eatery/@26.8668645,80.8887922..."
```

### Multiple URLs from a File
Create a `.txt` file containing Google Maps URLs separated by newlines, then run:
```bash
python cold_messenger.py -f links.txt
```

### Adding Context (Your Pitch)
You can provide specific context on what your message is about (e.g., offering web design, social media marketing, etc.):
```bash
python cold_messenger.py -f links.txt -c "I am offering a free social media audit for their cafe"
```

### Output
The script will automatically create an `output/` directory and save each generated message to a separate `.txt` file named after the business.

## Help
Run `python cold_messenger.py -h` for all available options.
