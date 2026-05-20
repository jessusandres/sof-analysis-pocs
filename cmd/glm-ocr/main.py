import base64
import json
import os
import sys

from pdf2image import convert_from_path
from io import BytesIO

from ollama import chat

project_folder = os.path.abspath(os.curdir)
print("Project Folder:", project_folder)

docs_path = os.path.join(project_folder, "docs")
out_path = os.path.join(project_folder, "output", "glm-ocr")

VISION_MODEL = "glm-ocr"
TEXT_MODEL = "mistral"


def run():
    filename = sys.argv[1] if len(sys.argv) > 1 else sys.exit("No filename provided.")

    print(f"Filename: {filename}")

    image = convert_from_path(os.path.join(docs_path, filename))[0]

    print("Image loaded.")

    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    print("Image converted to base64.")

    print("Sending request to Ollama...")

    vision_response = chat(
        model=VISION_MODEL,
        messages=[{'role': 'user', 'content': 'Extract all text from this image exactly as it appears.',
                   'images': [img_base64]}],
    )

    raw_text = vision_response.message.content
    print("--- Raw Text Extracted ---")
    print(raw_text)
    print("--------------------------")

    structuring_prompt = f"""
        Convert the following shipping timesheet text into a valid JSON object. 
        Use this exact structure:
        {{
          "STATEMENT_OF_FACTS": {{
            "REPORT": "",
            "VESSEL": "",
            "DATE": "",
            "WORKING_TIME": "",
            "CRANES": {{
              "CRANE_1": [
                 {{"Start": "", "End": "", "Used": "", "Remarks": ""}}
              ]
            }}
          }}
        }}

        Raw Text to parse:
        {raw_text}
        """

    text_response = chat(
        model=TEXT_MODEL,
        format='json',  # Text models handle this parameter much better than VLMs
        messages=[{'role': 'user', 'content': structuring_prompt}],
    )

    json_string = text_response.message.content

    print("JSON String:")
    print(json_string)
    print("-" * 8)

    clean_content = json_string.strip()

    if clean_content.startswith("```json"):
        clean_content = clean_content[7:]
    elif clean_content.startswith("```"):
        clean_content = clean_content[3:]

    if clean_content.endswith("```"):
        clean_content = clean_content[:-3]

    clean_content = clean_content.strip()

    try:
        json_content = json.loads(clean_content)

        if not os.path.exists(out_path):
            os.makedirs(out_path)

        # Save successfully parsed JSON
        output_file = os.path.join(out_path, f"{filename}.json")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2, ensure_ascii=False)

        print(f"Successfully saved structured JSON to {output_file}")

    except json.JSONDecodeError as e:
        print(f"CRITICAL: Failed to parse JSON. The model still hallucinated malformed brackets. Error: {e}")

    print("Done.")


run()
