import json
import re
import sys
import os
import requests
import tempfile
from ddgs import DDGS
import google.generativeai as genai
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER_TYPE
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN

genai.configure(api_key="AIzaSyCkhRoJqD0EJXtW28-JKoKBuIQdS_f_IfI")

TEMPLATE_PATH = "template.pptx"
TITLE_SLIDE_LAYOUT_NAME = "My Title Slide"
CONTENT_SLIDE_LAYOUT_NAME = "My Content Slide"

TEMP_DIR = tempfile.mkdtemp()

def cleanup_temp_dir():
    try:
        if os.path.exists(TEMP_DIR):
            for f in os.listdir(TEMP_DIR):
                full_path = os.path.join(TEMP_DIR, f)
                if os.path.isfile(full_path) and (f.startswith('slide_') or f.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))):
                    os.remove(full_path)
            if not os.listdir(TEMP_DIR):
                os.rmdir(TEMP_DIR)
    except OSError as e:
        pass

def search_snippets(query, max_results=5):
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(query, max_results=max_results)]
        return [r["body"] for r in results if "body" in r]

def search_images(query, max_results=5):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.images(query=query, max_results=max_results, safesearch='Off')]
            if not results:
                return None
            for res in results:
                if 'image' in res and res['image'].startswith('http'):
                    if not any(ad_keyword in res['image'].lower() for ad_keyword in ['vectorstock', 'shutterstock', 'istockphoto', 'gettyimages', 'depositphotos', 'dreamstime', 'unsplash.com']):
                        return res['image']
            if results and 'image' in results[0] and results[0]['image'].startswith('http'):
                return results[0]['image']
            return None
    except Exception as e:
        return None

def download_image(url, filename_prefix="image"):
    if not url: return None
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '').lower()
        ext = '.png'
        if 'jpeg' in content_type or 'jpg' in content_type: ext = '.jpg'
        elif 'gif' in content_type: ext = '.gif'
        elif 'webp' in content_type: ext = '.webp'
        temp_filepath = os.path.join(TEMP_DIR, f"{filename_prefix}_{os.urandom(4).hex()}{ext}")
        with open(temp_filepath, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        return temp_filepath
    except requests.exceptions.RequestException as e:
        return None

def generate_slides(topic, snippets):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    Create a structured JSON for a PowerPoint presentation about: "{topic}".
    The presentation must have exactly 7 slides.
    Each slide needs:
    - "Title": A concise title for the slide.
    - "Content": An array of 3-6 detailed and informative bullet points.
    - "ImageQuery": A suggested, concise search query (1-5 words) to find a relevant image for the slide.

    Here's the required slide structure and content guidelines:

    Slide 1: Title Slide (Title: "{topic}", Content: [1-2 bullet points as subtitle], ImageQuery: "...")
    Slide 2: Overview (Content: [3-5 bullet points], ImageQuery: "...")
    Slide 3: Key Aspect 1 (Content: [4-6 bullet points], ImageQuery: "...")
    Slide 4: Key Aspect 2 (Content: [4-6 bullet points], ImageQuery: "...")
    Slide 5: Key Aspect 3 (Content: [4-6 bullet points], ImageQuery: "...")
    Slide 6: Impact/Challenges/Future (Content: [3-5 bullet points], ImageQuery: "...")
    Slide 7: Conclusion (Content: [3-4 bullet points], ImageQuery: "...")

    Use the provided web snippets ({snippets}) and your general knowledge.

    Ensure your output is ONLY the JSON object, formatted exactly as requested. Do not include any introductory text, closing text, or markdown code block delimiters like ```json.
    Example JSON structure:
    {{
      "Slide 1": {{
        "Title": "The Topic",
        "Content": ["An intro sentence.", "By Your Name."],
        "ImageQuery": "topic abstract art"
      }},
      "Slide 2": {{
        "Title": "Overview of The Topic",
        "Content": ["Bullet point one.", "Bullet point two.", "Bullet point three."],
        "ImageQuery": "overview diagram topic"
      }}
      // ... and so on for all 7 slides ...
    }}
    """
    try:
        response = model.generate_content(prompt)
        text_output = response.text.strip()
    except Exception as e:
        return {"Slide 1": {"Title": f"Error Generating Slides for {topic}", "Content": [f"Could not generate content: {e}"]}}
    text_output = re.sub(r"```json\s*|\s*```", "", text_output, flags=re.DOTALL).strip()
    try:
        slides = json.loads(text_output)
        if not isinstance(slides, dict) or len(slides) != 7:
            raise ValueError(f"Incorrect number of slides ({len(slides)}) or not a dictionary.")
        return slides
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "Slide 1": {
                "Title": f"JSON Parsing Error for {topic}",
                "Content": [f"Could not parse Gemini's output. Error: {e}", "The raw, unparsed text from the AI was:", text_output]
            }
        }

def create_ppt(slides, filename="output.pptx"):
    if not os.path.exists(TEMPLATE_PATH):
        return
    prs = Presentation(TEMPLATE_PATH)
    try:
        title_slide_layout = prs.slide_layouts.get_by_name(TITLE_SLIDE_LAYOUT_NAME)
        content_slide_layout = prs.slide_layouts.get_by_name(CONTENT_SLIDE_LAYOUT_NAME)
    except KeyError as e:
        return
    MEDIA_WIDTH = Inches(4.5)
    MEDIA_HEIGHT = Inches(3.0)
    DEFAULT_BODY_FONT_SIZE = Pt(18)
    for i, (slide_key, slide_data) in enumerate(slides.items()):
        if i == 0:
            slide = prs.slides.add_slide(title_slide_layout)    
            title_placeholder = None
            for shape in slide.placeholders:
                if shape.placeholder_format.type == PP_PLACEHOLDER_TYPE.TITLE:
                    title_placeholder = shape
                    break
            if title_placeholder:
                title_placeholder.text = slide_data.get("Title", slide_key)
            subtitle_placeholder = None
            for shape in slide.placeholders:
                if shape.placeholder_format.type in (PP_PLACEHOLDER_TYPE.SUBTITLE, PP_PLACEHOLDER_TYPE.BODY):
                    subtitle_placeholder = shape
                    break
            if slide_data.get("Content") and subtitle_placeholder:
                subtitle_placeholder.text = "\n".join(slide_data["Content"])
            image_path = None
            if slide_data.get("ImageQuery"):
                image_url = search_images(slide_data["ImageQuery"])
                if image_url:
                    image_path = download_image(image_url, f"slide_{i}_img")
            if image_path:
                picture_placeholder = None
                for shape in slide.placeholders:
                    if shape.placeholder_format.type == PP_PLACEHOLDER_TYPE.PICTURE:
                        picture_placeholder = shape
                        break
                if picture_placeholder:
                    try:
                        picture_placeholder.insert_picture(image_path)
                    except Exception as e:
                        pass
                else:
                    img_left = (prs.slide_width - MEDIA_WIDTH) / 2
                    img_top = prs.slide_height - MEDIA_HEIGHT - Inches(0.75)
                    try:
                        slide.shapes.add_picture(image_path, img_left, img_top, MEDIA_WIDTH, MEDIA_HEIGHT)
                    except Exception as e:
                        pass
        else:
            slide = prs.slides.add_slide(content_slide_layout)
            title_shape = slide.shapes.title
            if title_shape:
                title_shape.text = slide_data.get("Title", slide_key)
            body_placeholder = None
            for shape in slide.placeholders:
                if shape.placeholder_format.type == PP_PLACEHOLDER_TYPE.BODY:
                    body_placeholder = shape
                    break
            if body_placeholder:
                tf = body_placeholder.text_frame
                tf.clear()
                content_points = slide_data.get("Content", [])
                if not content_points:
                    tf.text = "No content provided."
                else:
                    tf.text = content_points[0]
                    p = tf.paragraphs[0]
                    p.font.size = DEFAULT_BODY_FONT_SIZE
                    p.level = 0
                    for point_text in content_points[1:]:
                        p = tf.add_paragraph()
                        p.text = point_text
                        p.level = 0
                        p.font.size = DEFAULT_BODY_FONT_SIZE
            image_path = None
            if slide_data.get("ImageQuery"):
                image_url = search_images(slide_data["ImageQuery"])
                if image_url:
                    image_path = download_image(image_url, f"slide_{i}_img")
            if image_path:
                media_area_left = (body_placeholder.left + body_placeholder.width + Inches(0.25)) if body_placeholder else (prs.slide_width * 0.55)
                media_top_centered = (prs.slide_height - MEDIA_HEIGHT) / 2
                if media_area_left + MEDIA_WIDTH > prs.slide_width:
                    media_area_left = prs.slide_width - MEDIA_WIDTH - Inches(0.25)
                try:
                    slide.shapes.add_picture(image_path, media_area_left, media_top_centered, MEDIA_WIDTH, MEDIA_HEIGHT)
                except Exception as e:
                    pass
    prs.save(filename)

if __name__ == "__main__":
    try:
        topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Enter a topic: ")
        snippets = search_snippets(topic)
        slides_json = generate_slides(topic, snippets)
        safe_topic_filename = re.sub(r'[\\/:*?"<>|]', '', topic).replace(' ', '_')
        output_filename = f"{safe_topic_filename}.pptx"
        create_ppt(slides_json, output_filename)
    except Exception as main_e:
        pass
    finally:
        cleanup_temp_dir()