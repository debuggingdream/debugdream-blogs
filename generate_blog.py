import os
import json
import requests
import datetime
import re
import hashlib
from PIL import Image
from io import BytesIO

# --- Configuration ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
BASE_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]

# --- Audience Segments (rotated weekly) ---
AUDIENCES = [
    "Nepal business owners and SMEs in Kathmandu and other cities",
    "Nepal startups and entrepreneurs",
    "NGOs and nonprofits operating in Nepal",
    "International businesses looking to outsource web design, development, or digital marketing to Nepal",
    "Australian businesses looking for affordable digital services",
    "Businesses in other countries considering Nepal as an outsourcing destination",
    "Tech teams and developers looking for agency partnerships",
    "Hospitality and tourism businesses in Nepal",
    "E-commerce businesses in Nepal",
    "Educational institutions in Nepal"
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

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')

def get_existing_slugs():
    slugs = []
    for file in os.listdir('.'):
        if file.endswith('.md'):
            slugs.append(file[:-3])
    return slugs

def get_weekly_audience():
    """Rotate through audiences based on ISO week number."""
    week_number = datetime.date.today().isocalendar()[1]
    return AUDIENCES[week_number % len(AUDIENCES)]

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

def select_topic():
    """Use Gemini to dynamically research and pick a blog topic."""
    existing_slugs = get_existing_slugs()
    audience = get_weekly_audience()
    slugs_list = ", ".join(existing_slugs) if existing_slugs else "(none yet)"

    prompt = f"""You are a content strategist for DebugDream, a full-service digital agency based in Kathmandu, Nepal.

Your job is to pick ONE blog topic that will perform well on Google and attract the right audience.

THIS WEEK'S PRIMARY TARGET AUDIENCE:
{audience}

ALL AUDIENCES WE SERVE (consider overlap and cross-appeal):
1. Nepal business owners and SMEs in Kathmandu and other cities
2. Nepal startups and entrepreneurs
3. NGOs and nonprofits operating in Nepal
4. International businesses looking to outsource web design, development, or digital marketing to Nepal
5. Australian businesses looking for affordable digital services
6. Businesses in other countries considering Nepal as an outsourcing destination
7. Tech teams and developers looking for agency partnerships
8. Hospitality and tourism businesses in Nepal
9. E-commerce businesses in Nepal
10. Educational institutions in Nepal

DEBUGDREAM'S SERVICES:
- Web design and UI/UX
- Website and app development
- Digital marketing and paid advertising
- SEO services
- Branding and brand identity
- Video production and podcast production
- Content creation
- Custom brand assets
- Technology consulting

TOPIC SELECTION RULES:
- The topic MUST be relevant to the primary target audience above.
- Research current trends and pick something that would rank on Google for searches made by this audience type.
- Vary the style: sometimes a comparison post (e.g. "Outsourcing to Nepal vs India — cost comparison"), sometimes an educational post about Nepal's tech industry for international audiences, sometimes a practical guide for local Nepal businesses.
- The topic should naturally relate to at least one of DebugDream's services.
- Make the title SEO-friendly, specific, and compelling.

ALREADY WRITTEN TOPICS (avoid these and anything too similar):
{slugs_list}

Return ONLY the blog post title. Nothing else — no quotes, no explanation, no numbering."""

    print(f"Selecting topic for audience: {audience}")
    topic = call_gemini(prompt)
    # Clean any accidental quotes or whitespace
    topic = topic.strip('"\' \n')
    slug = slugify(topic)

    # Safety check: if slug already exists, append date
    if slug in existing_slugs:
        slug = slug + "-" + datetime.date.today().strftime("%Y%m%d")

    print(f"Selected topic: {topic}")
    return topic, slug

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
    category = category.strip('"\' \n')
    return category if category else "Business Strategy"

def generate_content(topic):
    audience = get_weekly_audience()
    prompt = f"""Write a complete, professional, and approachable blog post.

Topic: {topic}

Instructions:
- Primary Target Audience: {audience}
- Tone: Professional, authoritative, yet easy to understand. Adapt the language and examples to the target audience.
- Context:
    - If the audience is Nepal-based: use Nepal/Kathmandu-specific examples, currency (NPR), and local business scenarios.
    - If the audience is international: explain Nepal's tech landscape, talent pool, cost advantages, and timezone benefits. Use USD/AUD where relevant.
    - If the audience is Australian: reference AU market costs for comparison and emphasize Nepal as a quality outsourcing partner.
- Length: Minimum 1500 words.
- Structure:
    - Use H2 and H3 headings for clear organization.
    - Include a detailed "Practical Tips" section relevant to the audience.
    - Use bullet points and lists for readability.
    - Include real-world examples or scenarios the audience would relate to.
- Call to Action (CTA): End with a strong CTA mentioning DebugDream, a full-service digital agency based in Kathmandu, Nepal, and link to https://debugdream.com.
- Output Format: Return ONLY the raw markdown body content. No title, no frontmatter, no introductory text, and no markdown code blocks.
"""

    print(f"Generating content for: {topic} (audience: {audience})")
    content = call_gemini(prompt)
    return content

def download_image(topic, slug):
    keywords = "+".join(topic.split()[:3])
    primary_url = f"https://source.unsplash.com/1200x630/?{keywords}"
    fallback_url = "https://picsum.photos/1200/630"
    
    if not os.path.exists('images'):
        os.makedirs('images')
        
    image_path = f"images/{slug}.jpeg"
    
    # Try Unsplash first
    try:
        print(f"Attempting image download from Unsplash: {primary_url}")
        response = requests.get(primary_url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.convert('RGB').save(image_path, "JPEG", quality=85)
            print(f"Image saved from Unsplash: {image_path}")
            return f"/images/{slug}.jpeg"
    except Exception as e:
        print(f"Unsplash download failed: {e}")

    # Fallback to Picsum
    try:
        print(f"Falling back to Picsum: {fallback_url}")
        response = requests.get(fallback_url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.convert('RGB').save(image_path, "JPEG", quality=85)
            print(f"Image saved from Picsum: {image_path}")
            return f"/images/{slug}.jpeg"
    except Exception as e:
        print(f"Picsum download failed: {e}")
    
    return "/images/placeholder.jpeg"

def main():
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY environment variable is not set.")
        exit(1)

    topic, slug = select_topic()
    if not topic:
        print("No new topics could be generated.")
        return

    print(f"Targeting Topic: {topic}")
    content = generate_content(topic)
    category = suggest_category(topic)
    
    # Programmatic Frontmatter
    word_count = len(content.split())
    read_time = max(1, word_count // 200)
    date = datetime.date.today().strftime("%Y-%m-%d")
    
    # Clean excerpt: remove markdown symbols and normalize whitespace
    clean_text = re.sub(r'[#*`>]', '', content).strip()
    clean_text = re.sub(r'\s+', ' ', clean_text)
    excerpt = clean_text[:157] + "..." if len(clean_text) > 160 else clean_text
    
    image_path = download_image(topic, slug)
    
    seo_title = topic[:57] + "..." if len(topic) > 60 else topic
    seo_description = clean_text[:157] + "..." if len(clean_text) > 160 else clean_text

    frontmatter = f"""---
slug: {slug}
title: "{topic}"
date: {date}
author: "DebugDream Team"
readTime: {read_time} min
category: "{category}"
excerpt: "{excerpt}"
image: "{image_path}"
imageAlt: "Digital marketing and business growth in Nepal - {topic}"
seoTitle: "{seo_title}"
seoDescription: "{seo_description}"
---

"""
    
    full_post = frontmatter + content
    
    with open(f"{slug}.md", "w") as f:
        f.write(full_post)
        
    print(f"Blog post generated successfully: {slug}.md")

if __name__ == "__main__":
    main()
