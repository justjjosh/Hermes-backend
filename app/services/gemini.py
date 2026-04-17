import google.generativeai as genai_old  # OLD SDK - for pitch generation
from google import genai                # NEW SDK - for brand discovery (supports search grounding)
from google.genai import types          # Types for configuring the new SDK
import json
import time
import re
import logging
from typing import Dict, List
from app.services.ai_provider import AIProvider
from app.config import settings

logger = logging.getLogger(__name__)


#Pitch generation
class GeminiProvider(AIProvider):
    def __init__(self):
        """Initialize Gemini provider with API key from settings."""
        # Configure the OLD SDK for pitch generation (this still works fine)
        genai_old.configure(api_key=settings.gemini_api_key)
        self.model = genai_old.GenerativeModel("gemini-2.5-flash")

        # Create the NEW SDK client for brand discovery (supports search grounding)
        self.discovery_client = genai.Client(api_key=settings.gemini_api_key)

    def generate_pitch(self, brand_data: dict, profile_data: dict) -> Dict[str, str]:
        """
        Generate a personalized pitch using Gemini.

        Args:
            brand_data: Dictionary with brand info (name, website, category, etc.)
            profile_data: Dictionary with creator info (name, niches, bio, etc.)

        Returns:
            Dictionary with 'subject' and 'body' keys
        """
        # Build the prompt
        prompt = f"""
You are {profile_data.get('name', 'a content creator')} writing a pitch email directly to a brand. Write in FIRST PERSON - you are the creator, not a manager or agent.

BRAND INFORMATION:
- Name: {brand_data.get('name', 'Unknown')}
- Website: {brand_data.get('website', 'Not provided')}
- Category: {brand_data.get('category', 'Not provided')}
- Instagram: {brand_data.get('instagram', 'Not provided')}
- Notes: {brand_data.get('notes', 'Not provided')}

YOUR CREATOR PROFILE:
- Name: {profile_data.get('name', 'Unknown')}
- Email: {profile_data.get('sender_email', 'Not provided')}
- Niches: {', '.join(profile_data.get('niches', []))}
- Interests: {', '.join(profile_data.get('interests', []))}
- Bio: {profile_data.get('bio', 'Not provided')}
- Content Style: {profile_data.get('content_style', 'Not provided')}
- Unique Angle: {profile_data.get('unique_angle', 'Not provided')}
- Top Performing Content: {profile_data.get('top_performing_content', 'Not provided')}
- TikTok: {profile_data.get('tiktok_url', 'Not provided')}
- Portfolio: {profile_data.get('portfolio_url', 'Not provided')}
- Follower Count: {profile_data.get('follower_count', 0)}
- Average Views: {profile_data.get('avg_views', 0)}
- Engagement Rate: {profile_data.get('engagement_rate', 0)}%

INSTRUCTIONS:
Write a concise, professional pitch email FROM the creator's perspective (first person - "I'm...", "My content...", "I'd love...").

SUBJECT LINE:
- Professional and direct (e.g., "Collaboration Inquiry – [Content Type] Content")
- Under 60 characters
- No emojis or overly casual language

EMAIL BODY (KEEP IT CONCISE - max 4-5 short paragraphs):
1. Brief greeting and one-sentence introduction (name, location, content focus)
2. One paragraph explaining why the brand aligns with your audience (mention specific brand values/products)
3. Mention ONE key performance metric to show credibility
4. List 3-4 collaboration ideas as bullet points (short, specific)
5. Simple call-to-action offering to share analytics/discuss deliverables
6. Professional sign-off with name, TikTok URL, and portfolio URL (if available) - NO EMAIL

TONE: Professional, direct, confident but not salesy. Business inquiry, not fan mail.
FORMAT: HTML with <p> tags. Use bullet points (<ul><li>) for ideas only.

FOOTER/SIGNATURE:
- Always include: Name, TikTok username, and TikTok URL as clickable link
- If portfolio URL exists, include it as clickable link too
- Format TikTok username: "TikTok: @username" (extract from {profile_data.get('tiktok_url')})
- Format TikTok URL: <a href="{profile_data.get('tiktok_url')}">https://www.tiktok.com/@username</a>
- Include BOTH the @username and the clickable URL on separate lines
- Format Portfolio: <a href="{profile_data.get('portfolio_url')}">View Portfolio</a>
- DO NOT INCLUDE EMAIL ADDRESS - the email is already in the FROM field

Return ONLY valid JSON in this exact format:
{{
  "subject": "Your subject line here",
  "body": "<p>Your HTML email body here</p>"
}}
"""

        # Call Gemini API with JSON output
        # Retry up to 4 times for rate limits — autopilot runs in the background
        # so we can afford to wait longer than interactive requests.
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai_old.GenerationConfig(
                        response_mime_type="application/json"
                    )
                )
                break  # Success — exit the retry loop
            except Exception as e:
                error_str = str(e).lower()
                # Only retry on rate limit errors (429 / RESOURCE_EXHAUSTED)
                if "429" in error_str or "resource_exhausted" in error_str or "rate" in error_str:
                    if attempt == max_retries - 1:
                        raise Exception(
                            "Gemini rate limit reached. "
                            "You've made too many AI requests recently. "
                            "Wait 1-2 minutes and try again."
                        )
                    
                    # Try to extract the wait time from the error message
                    match = re.search(r'retry\s*(?:in|after)\s*(\d+\.?\d*)', error_str)
                    if match:
                        wait_time = float(match.group(1)) + 1  # Add 1s buffer
                    else:
                        wait_time = 15 * (attempt + 1)  # Escalating: 15s, 30s, 45s

                    # Cap at 60s — autopilot can wait, but not forever
                    if wait_time > 60:
                        raise Exception(
                            "Gemini rate limit reached. "
                            "You've made too many AI requests recently. "
                            "Wait 1-2 minutes and try again."
                        )

                    logger.warning(
                        f"Rate limited on pitch generation (attempt {attempt + 1}/{max_retries}). "
                        f"Waiting {wait_time:.1f}s before retry..."
                    )
                    time.sleep(wait_time)
                else:
                    raise  # Non-rate-limit error — don't retry, raise immediately

        # Parse JSON response
        pitch = json.loads(response.text)

        return pitch

    def discover_brands(self, niches: List[str], limit: int = 5) -> List[dict]:
        """
        Discover multiple brands in a SINGLE Gemini call (token-efficient).
        
        Instead of calling the API once per brand (expensive), this sends ONE
        prompt asking for N brands matching the given niches, complete with
        contact emails. This is the core autopilot discovery method.
        
        Token efficiency:
        - Single prompt, single response (vs N calls for N brands)
        - Lean prompt — only asks for name + email + category
        - Low temperature for factual accuracy
        - No unnecessary metadata (website, description, etc.)
        
        Args:
            niches: List of niche keywords (e.g., ["skincare", "wellness"])
            limit: Maximum brands to discover (default 5, max 10)

        Returns:
            List of dicts: [{name, email, category, confidence}, ...]
        """
        limit = min(limit, 10)  # Cap at 10 to keep response manageable
        
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        niches_str = ", ".join(niches)
        
        # Lean prompt — request ONLY what we need (name + email + category)
        prompt = f"""You are a brand outreach researcher. Find {limit} real brands in the following niches 
that actively work with content creators and influencers: {niches_str}

For each brand, find their REAL partnership or PR contact email address.

RULES:
1. Only include brands you can verify exist via web search
2. Only include emails you actually found — do NOT guess or construct emails
3. Focus on brands that have creator/influencer programs or PR contacts
4. Avoid massive corporations (e.g., Apple, Google) — focus on mid-size brands
5. Each brand must have a working email address

Return ONLY valid JSON, no other text:
{{
    "brands": [
        {{
            "name": "Brand Name",
            "email": "partnerships@brand.com",
            "category": "skincare",
            "confidence": "high"
        }}
    ]
}}

If you cannot find {limit} brands with verified emails, return fewer. Quality over quantity.
"""

        max_retries = 3
        raw_text = None
        
        for attempt in range(max_retries):
            try:
                response = self.discovery_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[google_search_tool],
                        temperature=0.1  # Very low temp for factual discovery
                    )
                )
                
                if hasattr(response, 'text') and response.text:
                    raw_text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    raw_text = response.candidates[0].content.parts[0].text
                else:
                    raise Exception(f"Unexpected response structure: {response}")
                
                break
                
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "resource_exhausted" in error_str or "rate" in error_str:
                    if attempt == max_retries - 1:
                        raise Exception(
                            "Gemini rate limit reached during brand discovery. "
                            "Wait 1-2 minutes and try again."
                        )
                    
                    match = re.search(r'retry\s*(?:in|after)\s*(\d+\.?\d*)', error_str)
                    wait_time = float(match.group(1)) + 1 if match else 15 * (attempt + 1)
                    
                    if wait_time > 60:
                        raise Exception(
                            "Gemini rate limit reached. Wait 1-2 minutes and try again."
                        )
                    
                    logger.warning(
                        f"Rate limited on batch discovery (attempt {attempt + 1}/{max_retries}). "
                        f"Waiting {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise
        
        # Parse response
        try:
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            result = json.loads(cleaned)
            brands = result.get("brands", [])
            
            # Validate each brand has required fields
            valid_brands = []
            for b in brands:
                if isinstance(b, dict) and b.get("name") and b.get("email") and "@" in b.get("email", ""):
                    valid_brands.append({
                        "name": b["name"],
                        "email": b["email"],
                        "category": b.get("category", niches[0] if niches else "general"),
                        "confidence": b.get("confidence", "medium"),
                    })
            
            return valid_brands
            
        except json.JSONDecodeError as e:
            raise Exception(
                f"Failed to parse batch discovery response. "
                f"Response: {raw_text[:200]}... Error: {str(e)}"
            )
    
    def discover_brand_contacts(self, brand_name: str) -> dict:
        """
        Use Gemini with Google Search grounding to find real partnership/PR
        contact emails for a brand. Only fetches emails — nothing else.

        How it works:
        1. We create a Google Search grounding tool so Gemini can search the web in real-time
        2. We send a focused prompt asking ONLY for contact emails
        3. Gemini searches the web, finds real emails, and returns structured JSON
        4. We parse and return the JSON with just the discovered contacts

        Args:
            brand_name: The name of the brand to research (e.g., "CeraVe", "The Ordinary")

        Returns:
            dict with keys: brand_name, contacts (list of email dicts)
        """

        # Step 1: Create the Google Search grounding tool
        # This gives Gemini the ability to search Google in real-time
        # Without this, Gemini can only use its training data (which may be outdated)
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        # Step 2: Build the focused email-only research prompt
        # We keep this narrow on purpose — we only need emails, not full brand metadata.
        # Asking for less = fewer tokens burned, faster response.
        prompt = f"""
You are a brand outreach researcher. Your ONLY job is to find real contact email addresses
for the brand "{brand_name}" that a content creator can use to pitch collaborations.

Search for:
- PR / press contact emails
- Partnership or collaboration emails
- Influencer / creator program emails
- Marketing department emails
- General contact emails (only if nothing more specific exists)

IMPORTANT RULES:
1. Only include emails you actually found on their website, social media, or press pages.
2. Do NOT make up, guess, or construct email addresses.
3. Do NOT include social media links, websites, or any other metadata — emails ONLY.
4. For each email, classify its type as one of: "pr", "partnerships", "marketing", "general", "influencer"
5. Rate your confidence as "high", "medium", or "low".

Return ONLY valid JSON in this exact format, no other text:
{{
    "brand_name": "{brand_name}",
    "contacts": [
        {{
            "email": "press@example.com",
            "type": "pr",
            "confidence": "high",
            "source": "Found on their website contact page"
        }}
    ]
}}

If you cannot find any real contact emails, return an empty contacts list.
"""

        # Step 3: Send the request to Gemini using the NEW SDK
        # We use self.discovery_client (initialized in __init__) with search grounding
        # Discovery gets 3 retries (heavier operation, user expects it to take a moment)
        max_retries = 3
        raw_text = None

        for attempt in range(max_retries):
            try:
                response = self.discovery_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[google_search_tool],
                        temperature=0.2  # Low temperature = more factual, less creative
                    )
                )
                
                # Step 4: Extract the text from response
                if hasattr(response, 'text') and response.text:
                    raw_text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    raw_text = response.candidates[0].content.parts[0].text
                else:
                    raise Exception(f"Unexpected response structure: {response}")
                
                break  # Success — exit the retry loop

            except Exception as e:
                error_str = str(e).lower()
                # Only retry on rate limit errors (429 / RESOURCE_EXHAUSTED)
                if "429" in error_str or "resource_exhausted" in error_str or "rate" in error_str:
                    if attempt == max_retries - 1:
                        raise Exception(
                            "Gemini rate limit reached. "
                            "You've made too many AI requests recently. "
                            "Wait 1-2 minutes and try again."
                        )

                    match = re.search(r'retry\s*(?:in|after)\s*(\d+\.?\d*)', error_str)
                    if match:
                        wait_time = float(match.group(1)) + 1
                    else:
                        wait_time = 15 * (attempt + 1)  # Fallback: 15s, 30s, 45s

                    # If Gemini wants us to wait more than 60s, fail fast
                    if wait_time > 60:
                        raise Exception(
                            "Gemini rate limit reached. "
                            "You've made too many AI requests recently. "
                            "Wait 1-2 minutes and try again."
                        )

                    logger.warning(
                        f"Rate limited on brand discovery (attempt {attempt + 1}/{max_retries}). "
                        f"Waiting {wait_time:.1f}s before retry..."
                    )
                    time.sleep(wait_time)
                else:
                    raise  # Non-rate-limit error — don't retry

        # Step 5: Clean up markdown code blocks and parse JSON
        try:
            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Step 6: Parse JSON
            result = json.loads(cleaned_text)
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Gemini response as JSON. Response was: {cleaned_text[:200]}... Error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to discover brand contacts: {str(e)}")
    