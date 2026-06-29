import argparse
import urllib.parse
import urllib.request
import re
import os
import sys
import time

def resolve_url(url):
    """
    Resolves short Google Maps URLs to their full path.
    """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        return response.geturl()
    except Exception as e:
        print(f"Warning: Could not resolve URL {url}: {e}")
        return url

def fetch_and_clean_html(url):
    """
    Fetches the HTML of the URL and returns a cleaned text version
    to save tokens when passing to Gemini.
    """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
        
        # Remove scripts and styles
        html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<.*?>', ' ', html, flags=re.DOTALL)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text
    except Exception as e:
        print(f"Warning: Could not fetch HTML for phone number extraction: {e}")
        return ""

def extract_name_from_url(url):
    """
    Extracts the business name from a Google Maps URL.
    """
    if "maps.app.goo.gl" in url or "goo.gl" in url:
        url = resolve_url(url)
        
    # e.g., https://www.google.com/maps/place/The+Ancestry+-+A+Cafe+and+Eatery/@...
    match = re.search(r'/place/([^/?]+)', url)
    if match:
        encoded_name = match.group(1)
        # Handle + as space and url decode
        name = urllib.parse.unquote_plus(encoded_name)
        return name, url
    return None, url

def extract_phone_number(text, api_key):
    """
    Uses Gemini to extract a phone number from the cleaned page text.
    """
    try:
        from google import genai
    except ImportError:
        return None

    client = genai.Client(api_key=api_key)
    
    # Truncate text to ensure we don't exceed token limits, though 1M is plenty.
    # 100k characters is more than enough for a Google Maps page text dump.
    truncated_text = text[:100000]
    
    prompt = (
        "You are an expert data extractor. I am providing you with the text extracted from a Google Maps page. "
        "Find the phone number of the business. If you find one, return ONLY the phone number in international format "
        "(e.g., +919876543210 or +1234567890). If you cannot find a phone number, return ONLY the exact word 'None'. "
        "Do not include any explanation or other text.\n\n"
        f"TEXT:\n{truncated_text}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        result = response.text.strip()
        if result.lower() == 'none' or not any(char.isdigit() for char in result):
            return None
        return result
    except Exception as e:
        print(f"Error extracting phone number with Gemini: {e}")
        return None

def draft_message(place_name, context, api_key):
    """
    Uses the Gemini API to draft a cold message.
    """
    try:
        from google import genai
    except ImportError:
        print("Error: google-genai is not installed. Please run 'pip install -r requirements.txt'")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    prompt = f"Draft a concise and polite cold outreach message for a business named '{place_name}'."
    if context:
        prompt += f" The purpose of this message is: {context}."
    else:
        prompt += " The purpose is a general inquiry about their services or potential collaboration."
        
    prompt += "\nKeep it professional, engaging, and under 150 words."

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating message with Gemini API: {e}")
        return "Failed to generate message."

def main():
    parser = argparse.ArgumentParser(description="Draft cold messages for businesses from Google Maps links.")
    parser.add_argument('-f', '--file', type=str, help='Path to a txt file containing Google Maps links separated by newlines.')
    parser.add_argument('-u', '--url', type=str, help='A single Google Maps URL.')
    parser.add_argument('-c', '--context', type=str, help='Context or offer to include in the message.', default="")
    parser.add_argument('-C', '--context-file', type=str, help='Path to a txt file containing the context/offer.')
    parser.add_argument('-w', '--whatsapp', action='store_true', help='Automatically open WhatsApp Web and send the message if a phone number is found.')
    
    args = parser.parse_args()
    
    if not args.file and not args.url:
        print("Error: Please provide either a file (-f) or a URL (-u).")
        parser.print_help()
        sys.exit(1)

    if args.whatsapp:
        try:
            import pywhatkit
        except ImportError:
            print("Error: pywhatkit is not installed. Required for sending WhatsApp messages.")
            print("Please run: pip install pywhatkit")
            sys.exit(1)

    # Read context from file if provided
    context_str = args.context
    if args.context_file:
        try:
            with open(args.context_file, 'r') as f:
                context_str = f.read().strip()
        except Exception as e:
            print(f"Error reading context file {args.context_file}: {e}")
            sys.exit(1)
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set it using: export GEMINI_API_KEY='your_api_key'")
        sys.exit(1)

    urls = []
    if args.url:
        urls.append(args.url.strip())
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                # Filter out empty lines
                urls.extend([line.strip() for line in f if line.strip()])
        except Exception as e:
            print(f"Error reading file {args.file}: {e}")
            sys.exit(1)
            
    if not urls:
        print("No valid URLs provided.")
        sys.exit(0)

    # Create output directory
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}/")
            
    for url in urls:
        print(f"\nProcessing URL: {url}")
        
        place_name, resolved_url = extract_name_from_url(url)
        if not place_name:
            print(f"Warning: Could not extract place name from URL: {url}")
            place_name = "the business"
            
        print(f"Drafting message for: {place_name}...")
        message = draft_message(place_name, context_str, api_key)
        
        # Phone number extraction
        phone_number = None
        if args.whatsapp:
            print("Extracting phone number from Maps page...")
            page_text = fetch_and_clean_html(resolved_url)
            if page_text:
                phone_number = extract_phone_number(page_text, api_key)
                if phone_number:
                    print(f"Found phone number: {phone_number}")
                else:
                    print("No phone number could be extracted.")
        
        # Sanitize place_name for use as a filename
        safe_filename = re.sub(r'[^\w\s-]', '', place_name).strip().replace(' ', '_')
        if not safe_filename:
            safe_filename = "business_message"
            
        file_path = os.path.join(output_dir, f"{safe_filename}.txt")
        
        try:
            with open(file_path, 'w') as f:
                f.write(message)
            print(f"Saved message to: {file_path}")
        except Exception as e:
            print(f"Error saving to {file_path}: {e}")
            
        if args.whatsapp and phone_number:
            print(f"Opening WhatsApp Web to message {phone_number}...")
            import pywhatkit
            try:
                # wait_time is 15 seconds to allow WhatsApp web to load
                pywhatkit.sendwhatmsg_instantly(phone_number, message, wait_time=15, tab_close=True, close_time=3)
                print("Message sent/queued successfully in WhatsApp Web.")
                # Add a small delay before processing the next one to avoid issues with multiple tabs
                time.sleep(5)
            except Exception as e:
                print(f"Failed to send WhatsApp message: {e}")

if __name__ == "__main__":
    main()
