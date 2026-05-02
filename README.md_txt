# DebugDream Automated Blog System

This repository handles the automated generation and storage of high-converting, SEO-optimized blog posts for [DebugDream](https://debugdream.com).

## 🚀 How it Works

The system uses a custom Python generator (`generate_blog.py`) powered by **Google Gemini AI** and the **Pexels API** to create professional content and source relevant imagery. 

There are two primary content streams managed via GitHub Actions:

1.  **Weekly SEO Blogs**: Generates one blog post every Sunday focused on technical growth, web development, and localized Nepali business case studies.
2.  **Monthly CEO Insights**: Generates one strategic, first-person letter from the CEO on the 1st of every month to build personal authority and company credibility.

## 📁 Repository Structure

- `posts/`: Contains all published blog posts in Markdown (`.md`) format.
- `images/`: Stores the high-resolution images sourced from Pexels for each post.
- `.github/workflows/`:
    - `auto-blog.yml`: The weekly automation schedule.
    - `ceo-blog.yml`: The monthly CEO-series schedule.
- `generate_blog.py`: The core generation engine.

## 🛠️ Local Development

### Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install requests pillow pyyaml
   ```
3. Set your environment variables:
   ```bash
   export GEMINI_API_KEY='your_key_here'
   export PEXELS_API_KEY='your_key_here'
   ```

### Manual Generation
To generate a standard blog post manually:
```bash
python generate_blog.py
```

To generate a **CEO Insight** post manually:
```bash
python generate_blog.py --ceo
```

## 🔗 Website Integration

The DebugDream website (Next.js) fetches content directly from the `posts/` directory of this repository using the GitHub API. 
After every generation, a **revalidation trigger** is sent to the website to instantly clear the cache and show the new post without a full rebuild.

---
*Built with ❤️ by DebugDream Team*
