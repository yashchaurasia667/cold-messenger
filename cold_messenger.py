import argparse
import urllib.parse
import urllib.request
import re
import os
import sys
import time
import json

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

def process_business_with_gemini(place_name, context, api_key, extract_phone=False, page_text=""):
    """
    Uses the Gemini API to draft a cold message and optionally extract a phone number in a single request.
    Outputs as JSON to guarantee structured extraction.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: google-genai is not installed. Please run 'pip install -r requirements.txt'")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    prompt = f"Draft a concise and polite cold outreach message for a business named '{place_name}'."
    if context:
        prompt += f" The purpose of this message is: {context}."
    else:
        prompt += " The purpose is a general inquiry about their services or potential collaboration."
        
    prompt += "\nKeep the message professional, engaging, and under 150 words."
    
    if extract_phone and page_text:
        # Pre-extract potential phone numbers to drastically save tokens and speed up API.
        # We look for strings that look like phone numbers (digits, spaces, hyphens, plus signs)
        phone_candidates = re.findall(r'[\+\(]?[0-9][0-9 .\-\(\)]{8,15}[0-9]', page_text)
        # Remove obvious coordinates or timestamps (long numbers without + or spaces if they are just pure digits)
        phone_candidates = [c for c in phone_candidates if len(re.sub(r'\D', '', c)) >= 8]
        candidates_str = ", ".join(phone_candidates[:50]) # limit to first 50 matches
        
        prompt += (
            "\n\nI am also providing you with a list of potential phone number strings extracted from their Google Maps page. "
            "Identify the correct business phone number from these. It should be formatted in international format (e.g., +919876543210). "
            f"\nCANDIDATES: {candidates_str}\n"
        )
    
    prompt += (
        "\n\nYou must return the result as a valid JSON object with two keys:\n"
        "1. 'message': The drafted cold message.\n"
        "2. 'phone_number': The extracted phone number (or null if none found / not requested)."
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text.strip())
        return result.get('message', "Failed to generate message."), result.get('phone_number')
    except Exception as e:
        print(f"Error generating content with Gemini API: {e}")
        return "Failed to generate message.", None

def main():
    parser = argparse.ArgumentParser(description="Draft cold messages for businesses from Google Maps links.")
    parser.add_argument('-f', '--file', type=str, help='Path to a txt file containing Google Maps links separated by newlines.')
    parser.add_argument('-u', '--url', type=str, help='A single Google Maps URL.')
    parser.add_argument('-c', '--context', type=str, help='Context or offer to include in the message.', default="")
    parser.add_argument('-C', '--context-file', type=str, help='Path to a txt file containing the context/offer.')
    parser.add_argument('-w', '--whatsapp', action='store_true', help='Automatically open WhatsApp Web and send the message if a phone number is found.')
    parser.add_argument('--delay', type=int, default=12, help='Delay in seconds between processing each business to avoid API rate limits (default: 12).')
    
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
            
    for i, url in enumerate(urls):
        print(f"\n[{i+1}/{len(urls)}] Processing URL: {url}")
        
        place_name, resolved_url = extract_name_from_url(url)
        if not place_name:
            print(f"Warning: Could not extract place name from URL: {url}")
            place_name = "the business"
            
        page_text = ""
        if args.whatsapp:
            print("Fetching Maps page for phone number extraction...")
            page_text = fetch_and_clean_html(resolved_url)
            
        print(f"Drafting message for: {place_name}...")
        
        message, phone_number = process_business_with_gemini(
            place_name, 
            context_str, 
            api_key, 
            extract_phone=args.whatsapp, 
            page_text=page_text
        )
        
        if args.whatsapp:
            if phone_number:
                print(f"Found phone number: {phone_number}")
            else:
                print("No phone number could be extracted.")
        
        # Sanitize place_name for use as a filename
        safe_filename = re.sub(r'[^\w\s-]', '', place_name).strip().replace(' ', '_')
        if not safe_filename:
            safe_filename = f"business_message_{i+1}"
            
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
            except Exception as e:
                print(f"Failed to send WhatsApp message: {e}")

        # Sleep to avoid rate limits, unless it's the last URL
        if i < len(urls) - 1:
            print(f"Sleeping for {args.delay} seconds to avoid Gemini API rate limits...")
            time.sleep(args.delay)

if __name__ == "__main__":
    main()
