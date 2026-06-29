import argparse
import urllib.parse
import urllib.request
import re
import os
import sys

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
        return name
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
        return response.text
    except Exception as e:
        print(f"Error generating message with Gemini API: {e}")
        return "Failed to generate message."

def main():
    parser = argparse.ArgumentParser(description="Draft cold messages for businesses from Google Maps links.")
    parser.add_argument('-f', '--file', type=str, help='Path to a txt file containing Google Maps links separated by newlines.')
    parser.add_argument('-u', '--url', type=str, help='A single Google Maps URL.')
    parser.add_argument('-c', '--context', type=str, help='Context or offer to include in the message (e.g., "offering social media management").', default="")
    parser.add_argument('-C', '--context-file', type=str, help='Path to a txt file containing the context/offer.')
    
    args = parser.parse_args()
    
    if not args.file and not args.url:
        print("Error: Please provide either a file (-f) or a URL (-u).")
        parser.print_help()
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
    
    if not args.file and not args.url:
        print("Error: Please provide either a file (-f) or a URL (-u).")
        parser.print_help()
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
        place_name = extract_name_from_url(url)
        if not place_name:
            print(f"Warning: Could not extract place name from URL: {url}")
            place_name = "the business"
            
        print(f"Drafting message for: {place_name}...")
        message = draft_message(place_name, context_str, api_key)
        
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

if __name__ == "__main__":
    main()
