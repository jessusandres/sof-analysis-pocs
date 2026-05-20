import json
import os
import sys

from langchain_opendataloader_pdf import OpenDataLoaderPDFLoader

ROOT_DIR = os.path.abspath(os.curdir)
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output", "opendataloader")


def run():
    # Obtener filename de argumentos o usar por defecto
    filename = sys.argv[1] if len(sys.argv) > 1 else sys.exit("No filename provided.")

    loader = OpenDataLoaderPDFLoader(
        file_path=[
            os.path.join(DOCS_DIR, filename),
        ],
        format="json",
        hybrid="docling-fast",
        hybrid_url="http://localhost:5002"
    )

    documents = loader.load()

    content = []

    for doc in documents:
        content.append({
            "metadata": doc.metadata,
            "content": json.loads(doc.page_content)
        })

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w") as f:
        f.write(json.dumps(content, indent=2))

    print("File saved successfully.")


run()
