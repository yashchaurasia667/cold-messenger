import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
prompt = "Find the phone number for 'The Ancestry - A Cafe and Eatery' in Lucknow. Return ONLY the phone number."
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[{"google_search": {}}]
    )
)
print(response.text)
