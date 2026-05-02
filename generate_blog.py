import os
import sys
import json
import requests
import datetime
import re
import hashlib
import yaml
from PIL import Image
from io import BytesIO

# --- Configuration ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
BASE_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]

# --- Audience Segments ---
AUDIENCES = [
    "Primary: Nepal businesses (localized case studies for credibility), Secondary: Global founders, startups, SaaS, e-commerce (high-ticket clients)"
]

DEBUGDREAM_SERVICES = [
    "Web design and UI/UX",
    "Website and app development",
    "Digital marketing and paid advertising",
    "SEO services",
    "Branding and brand identity",
    "Video production and podcast production",
    "Content creation",
    "Custom brand assets",
    "Technology consulting"
]

# --- Utility Functions ---

def safe_yaml_string(text):
    """Sanitize string fields to be bulletproof against YAML parsing errors."""
    if not text:
        return ""
    # Replace any double quotes with escaped version
    text = text.replace('"', '\\"')
    # Remove any newlines
    text = text.replace('\n', ' ').replace('\r', ' ')
    # Specific fix for colons followed by space (breaks YAML block mapping)
    text = text.replace(': ', ' - ')
    return text.strip()

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')

def get_existing_slugs():
    slugs = []
    if os.path.exists('posts'):
        for file in os.listdir('posts'):
            if file.endswith('.md'):
                slugs.append(file[:-3])
    return slugs

def get_weekly_audience():
    """Rotate through audiences based on ISO week number."""
    week_number = datetime.date.today().isocalendar()[1]
    return AUDIENCES[week_number % len(AUDIENCES)]

def validate_frontmatter(frontmatter_text):
    """Validate that YAML frontmatter parses correctly before writing."""
    try:
        # Extract the YAML between --- delimiters
        parts = frontmatter_text.split('---')
        if len(parts) >= 3:
            yaml_content = parts[1]
            yaml.safe_load(yaml_content)
            print("Frontmatter validation: PASSED")
            return True
    except yaml.YAMLError as e:
        print(f"Frontmatter validation: FAILED — {e}")
        return False
    return False

# --- Gemini API ---

def call_gemini(prompt):
    """Helper to call Gemini API with fallback logic for different models."""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    for model in MODELS_TO_TRY:
        url = f"{BASE_GEMINI_URL}/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            # If 404, the model might be deprecated, try the next one
            if response.status_code == 404:
                print(f"Model {model} not found (404). Trying next model...")
                continue
                
            if response.status_code != 200:
                print(f"Error calling model {model} ({response.status_code}): {response.text}")
                continue

            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
            
        except Exception as e:
            print(f"Exception while calling {model}: {e}")
            continue

    print("ALL Gemini models failed. Check API key and internet connection.")
    exit(1)

# --- Topic Selection ---

def select_topic():
    """Use Gemini to dynamically research and pick a blog topic."""
    existing_slugs = get_existing_slugs()
    audience = get_weekly_audience()
    slugs_list = ", ".join(existing_slugs) if existing_slugs else "(none yet)"

    prompt = f"""You are a senior growth strategist and content director for DebugDream, a premium full-service digital agency.

Your job is to pick ONE high-converting, buyer-intent blog topic that brings "closer-to-money" traffic.

TARGET AUDIENCE:
{audience}
(Content tone should feel "global premium," not just local-first).

DEBUGDREAM'S SERVICES:
{", ".join(DEBUGDREAM_SERVICES)}

TOPIC SELECTION RULES:
1. Focus on high-converting angles that agitate pain points.
2. Use strong hooks. Examples of the style we want:
   - "Best Website Audit Service for Startups: What Actually Matters"
   - "How to Choose a Digital Agency Without Getting Burned"
   - "Why Your Website Isn't Generating Leads: Full Technical Breakdown"
   - "Next.js vs Shopify vs WordPress: Which One Actually Converts Better?"
   - "Landing Page vs Full Website: What Drives More Revenue?"
3. The topic MUST connect to revenue and business outcomes, not just generic education.
4. Make the title SEO-friendly but highly clickable.

ALREADY WRITTEN TOPICS (avoid these):
{slugs_list}

Return ONLY the blog post title. Nothing else — no quotes, no explanation, no numbering."""

    print(f"Selecting topic for audience: {audience}")
    topic = call_gemini(prompt)
    # Clean any accidental quotes or whitespace
    topic = topic.strip('"\'  \n')
    slug = slugify(topic)

    # Safety check: if slug already exists, append date
    if slug in existing_slugs:
        slug = slug + "-" + datetime.date.today().strftime("%Y%m%d")

    print(f"Selected topic: {topic}")
    return topic, slug

# --- Category ---

def suggest_category(topic):
    """Use Gemini to suggest a category for the given topic."""
    prompt = f"""Given this blog post title: "{topic}"

Suggest ONE short blog category label (2-3 words max) from options like:
- Web Design
- Web Development
- Digital Marketing
- SEO
- Branding
- Video Production
- Content Strategy
- E-Commerce
- Business Strategy
- Outsourcing
- Technology
- Tourism & Hospitality
- Education

Or suggest a new short category if none of these fit well.
Return ONLY the category name. Nothing else."""

    print(f"Suggesting category for: {topic}")
    category = call_gemini(prompt)
    category = category.strip('"\'  \n')
    return category if category else "Business Strategy"

# --- Content Generation (Humanized) ---

def generate_content(topic, is_ceo=False):
    """Generate blog content with strict anti-AI-tone instructions."""
    audience = get_weekly_audience()
    existing_slugs = get_existing_slugs()
    internal_links_context = f"Here are existing blog post slugs on our site: {', '.join(existing_slugs)}. You MUST naturally insert 2 markdown links to these existing posts where relevant." if existing_slugs else "No existing posts to link to."

    if is_ceo:
        persona = "You are Rikesh Karma, the CEO and Founder of DebugDream."
        additional_instructions = """
- WRITE IN THE FIRST PERSON ("I", "Me", "My").
- This is a 'CEO Letter' - it should feel strategic, vision-focused, and authoritative.
- Talk about the future of the industry, your personal philosophy on growth, and how DebugDream is leading the way.
- Mention your direct contact email naturally for high-level inquiries.
"""
    else:
        persona = "You are a senior growth strategist and digital marketing consultant who has 10+ years of hands-on experience."
        additional_instructions = ""

    prompt = f"""Write a complete blog post. 
{persona}
{additional_instructions}

Topic: {topic}

AUDIENCE: {audience}

WRITING STYLE & PSYCHOLOGY — THIS IS CRITICAL:
1. The Hook: Start with Problem + Pain + Promise. No generic intros like "In today's digital landscape."
2. Pattern Interrupts: Use phrases like "Here's what's actually happening:" followed by short, punchy bullets explaining the hidden problem.
3. Friction Triggers: Agitate the pain. Use phrases like "This is where 80% of stores fail" or "Most founders ignore this, and it costs them revenue."
4. Curiosity Headers: Don't use boring headers like "Step 1: Navigation". Use "Step 1: The Navigation Mistake That Kills Sales".
5. The Objection Killer: Before the final conclusion, add a section that destroys common objections (e.g., "Think your site is already optimized? Here's why even high-performing stores leak revenue...").
6. The End-of-Article Trap: End the article with "If this helped, read this next →" instead of just stopping.

BANNED PHRASES:
- "In today's digital landscape/world/era/age"
- "Whether you're a... or a..."
- "It's important to note that..."
- "In conclusion..."
- "Let's dive in" / "Let's explore"
- "Comprehensive guide"

INTERNAL LINKING & FUNNEL:
- {internal_links_context}
- Link to 1 conversion page naturally (e.g., /services or /contact).

STRUCTURE & LENGTH:
- Length: 1500-2000 words.
- Short paragraphs. Use visual breaks.
- Context: Blend "Global Premium" authority with specific, concrete examples. If relevant to Nepal, use high-ticket localized examples.

OUTPUT: Return ONLY the raw markdown body content. No title, no frontmatter, no introductory text, no markdown code block wrappers."""

    print(f"Generating content for: {topic} (audience: {audience})")
    content = call_gemini(prompt)
    return content

def humanize_content(content, topic):
    """Run a second pass to strip any remaining AI patterns and make content feel authentic."""
    prompt = f"""You are an editor reviewing a blog post about "{topic}". Your job is to make it sound like it was written by a real person, not AI.

Here is the draft:

{content}

EDITING RULES:
1. Remove any sentence that starts with "In today's..." or "In the ever-evolving..." or similar AI cliches
2. Replace generic filler sentences with specific, useful information
3. If you see "Whether you're a... or a..." — rewrite it as a direct statement
4. Shorten any paragraph that rambles. Cut the fluff.
5. Make sure the opening paragraph has a strong hook — a surprising fact, a direct question, or a bold statement
6. Keep all the factual content, headings, links, and structure intact
7. Don't add new sections or remove existing ones
8. Don't change any URLs, CTA text, or brand mentions
9. Keep the same markdown formatting

Return the edited markdown content only. No explanations, no wrapper."""

    print("Running humanization pass...")
    humanized = call_gemini(prompt)
    return humanized if humanized else content

def generate_excerpt(topic, content):
    """Generate a compelling 1-2 sentence excerpt using Gemini."""
    # Take first 500 chars of content for context
    content_preview = content[:500]
    prompt = f"""Write a compelling 1-2 sentence excerpt (max 160 characters) for a blog post.

Title: {topic}
Content preview: {content_preview}

Rules:
- Make it specific and intriguing — not generic
- It should make someone want to click and read more
- No cliches like "comprehensive guide" or "everything you need to know"
- Return ONLY the excerpt text. Nothing else."""

    print("Generating excerpt...")
    excerpt = call_gemini(prompt)
    excerpt = excerpt.strip('"\'  \n')
    # Ensure it's within 160 chars
    if len(excerpt) > 160:
        excerpt = excerpt[:157] + "..."
    return excerpt

# --- Image Handling (Pexels API) ---

def get_image_keywords(topic):
    """Ask Gemini to suggest 3 visual keywords for image search."""
    prompt = f"""For a blog post titled "{topic}", suggest exactly 3 simple English keywords for searching a relevant stock photo.
    Rules:
    - Keywords must be concrete visual concepts (things you can photograph)
    - No abstract words like "strategy" or "success"
    - No location words like "Nepal" or "Kathmandu"
    - Good examples: "laptop workspace", "shopping cart", "social media phone"
    - Return only the 3 keywords separated by commas, nothing else"""
    
    print(f"Getting image keywords for: {topic}")
    keywords = call_gemini(prompt).strip()
    return keywords if keywords else "technology, workspace, digital"

def download_image(topic, slug):
    """Download a relevant image using Pexels API, with Picsum fallback."""
    keywords = get_image_keywords(topic)
    keyword_query = " ".join(k.strip() for k in keywords.split(",")[:3])
    
    if not os.path.exists('images'):
        os.makedirs('images')
        
    image_path = f"images/{slug}.jpeg"
    photographer = ""
    
    # Try Pexels API first
    if PEXELS_API_KEY:
        try:
            print(f"Searching Pexels for: {keyword_query}")
            pexels_url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(keyword_query)}&per_page=1&orientation=landscape"
            pexels_headers = {"Authorization": PEXELS_API_KEY}
            response = requests.get(pexels_url, headers=pexels_headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    photo = data["photos"][0]
                    # Use large2x for good quality at reasonable size
                    image_url = photo["src"].get("large2x") or photo["src"].get("original")
                    photographer = photo.get("photographer", "")
                    
                    print(f"Downloading from Pexels: {image_url}")
                    img_response = requests.get(image_url, timeout=30)
                    if img_response.status_code == 200:
                        img = Image.open(BytesIO(img_response.content))
                        # Resize to target dimensions
                        img = img.convert('RGB')
                        img = img.resize((1200, 630), Image.LANCZOS)
                        img.save(image_path, "JPEG", quality=85)
                        print(f"Image saved from Pexels: {image_path} (by {photographer})")
                        return image_path, photographer
                else:
                    print("Pexels returned no results for query.")
            else:
                print(f"Pexels API error: {response.status_code}")
        except Exception as e:
            print(f"Pexels download failed: {e}")
    else:
        print("PEXELS_API_KEY not set, skipping Pexels.")

    # Fallback to Picsum
    try:
        fallback_url = "https://picsum.photos/1200/630"
        print(f"Falling back to Picsum: {fallback_url}")
        response = requests.get(fallback_url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.convert('RGB').save(image_path, "JPEG", quality=85)
            print(f"Image saved from Picsum: {image_path}")
            return image_path, "Picsum"
    except Exception as e:
        print(f"Picsum download failed: {e}")
    
    return "images/placeholder.jpeg", ""

def inject_ctas(content):
    """Programmatically inject CTAs at ~25%, 50%, and 75% scroll depths."""
    paragraphs = content.split('\n\n')
    total_p = len(paragraphs)
    
    if total_p < 8:
        return content # Too short to inject 3 CTAs
        
    p25 = int(total_p * 0.25)
    p50 = int(total_p * 0.50)
    p75 = int(total_p * 0.75)
    
    cta_25 = "\n\n> **Want a real breakdown of your digital presence?** We'll show you exactly where users drop off and how to fix it. → [Get a Free UX & SEO Audit](https://debugdream.com/contact)\n\n"
    cta_50 = "\n\n> **Stop guessing why your site isn't converting.** Download our *25-Point E-commerce UX Checklist* and find the friction points costing you sales. → [Download the Free Checklist](https://debugdream.com/contact)\n\n"
    cta_75 = "\n\n> **Ready to scale your revenue?** Book a 30-minute teardown call with our senior growth team today, and we'll hand you a prioritized list of fixes. → [Book a Discovery Call](https://debugdream.com/contact)\n\n"
    
    paragraphs.insert(p75, cta_75)
    paragraphs.insert(p50, cta_50)
    paragraphs.insert(p25, cta_25)
    
    return '\n\n'.join(paragraphs)

# --- Main Pipeline ---
def main():
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY environment variable is not set.")
        exit(1)

    is_ceo = "--ceo" in sys.argv
    
    topic, slug = select_topic()
    if not topic:
        print("No new topics could be generated.")
        return

    print(f"Targeting Topic: {topic} (CEO Mode: {is_ceo})")
    
    # Step 1: Generate raw content
    raw_content = generate_content(topic, is_ceo=is_ceo)
    
    # Step 2: Humanize the content
    content = humanize_content(raw_content, topic)
    
    # Step 2.5: Inject CTAs programmatically
    content = inject_ctas(content)
    
    # Step 3: Generate metadata
    category = suggest_category(topic)
    excerpt = generate_excerpt(topic, content)
    
    # Programmatic metadata
    word_count = len(content.split())
    read_time = max(1, word_count // 200)
    date = datetime.date.today().strftime("%Y-%m-%d")
    
    # Step 4: Download image
    image_result = download_image(topic, slug)
    image_path, photographer = image_result
    
    # Step 5: Build frontmatter with sanitized fields
    seo_title = safe_yaml_string(topic[:57] + ("..." if len(topic) > 60 else ""))
    seo_description = safe_yaml_string(excerpt)
    
    safe_topic = safe_yaml_string(topic)
    safe_excerpt = safe_yaml_string(excerpt)
    safe_category = safe_yaml_string(category)
    safe_image_alt = safe_yaml_string(f"{topic}")
    safe_photographer = safe_yaml_string(photographer) if photographer else ""

    author = "Rikesh Karma" if is_ceo else "DebugDream Team"
    post_type = "ceo_letter" if is_ceo else "regular"

    frontmatter = f"""---
slug: {slug}
title: "{safe_topic}"
date: {date}
author: "{author}"
type: {post_type}
readTime: {read_time} min
category: "{safe_category}"
excerpt: "{safe_excerpt}"
image: "{image_path}"
imageAlt: "{safe_image_alt}"
imageCredit: "{safe_photographer}"
seoTitle: "{seo_title}"
seoDescription: "{seo_description}"
---

"""
    
    # Step 6: Validate frontmatter before writing
    if not validate_frontmatter(frontmatter):
        print("WARNING: Frontmatter validation failed. Attempting to fix...")
        # Fallback: use minimal safe frontmatter
        frontmatter = f"""---
slug: {slug}
title: "{slug}"
date: {date}
author: "DebugDream Team"
readTime: {read_time} min
category: "Business Strategy"
excerpt: "Read this article on DebugDream."
image: "{image_path}"
imageAlt: "DebugDream blog post"
seoTitle: "{slug}"
seoDescription: "Read this article on DebugDream."
---

"""
        print("Using fallback frontmatter.")
    
    full_post = frontmatter + content
    
    # Ensure posts directory exists
    os.makedirs("posts", exist_ok=True)
    
    file_path = f"posts/{slug}.md"
    with open(file_path, "w") as f:
        f.write(full_post)
        
    print(f"Blog post generated successfully: {file_path}")

if __name__ == "__main__":
    main()
