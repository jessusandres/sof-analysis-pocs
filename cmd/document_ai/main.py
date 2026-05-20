import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

from google.cloud import documentai
from google.api_core.client_options import ClientOptions

"""
============================================================
Document AI PDF Analyzer
============================================================

OBJETIVO
--------

Este script permite probar Google Document AI utilizando
un PDF operacional portuario (SOF) y obtener información
detallada para evaluar:

- Calidad OCR
- Precisión
- Estructura documental
- Tablas detectadas
- Layout
- Confidence scores
- Entities
- Texto extraído
- Bounding boxes
- Calidad de parsing

Además genera múltiples archivos de salida para análisis.

============================================================
REQUISITOS
============================================================

1. Instalar dependencias:

pip install google-cloud-documentai

2. Configurar credenciales:

export GOOGLE_APPLICATION_CREDENTIALS="/ruta/service-account.json"

3. Habilitar API:

https://console.cloud.google.com/apis/library/documentai.googleapis.com

4. Crear processor OCR:

https://console.cloud.google.com/ai/document-ai

Processor recomendado:
- Enterprise Document OCR

============================================================
CONFIGURACIÓN
============================================================
"""

# ============================================
# CONFIG
# ============================================

PROJECT_ID = "looker-dev-cloud"
LOCATION = "us"  # us o eu
PROCESSOR_ID = "8c807078292b5f17"

ROOT_DIR = os.path.abspath(os.curdir)

print("Root Directory:", ROOT_DIR)

# Obtener filename de argumentos o usar por defecto
FILENAME = sys.argv[1] if len(sys.argv) > 1 else sys.exit("No filename provided.")
PDF_PATH = os.path.join(ROOT_DIR, "docs", FILENAME)

# Directorio outputs
OUTPUT_DIR = os.path.join(ROOT_DIR, "output", "document_ai")


# ============================================
# HELPERS
# ============================================


def ensure_output_dir():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def save_json(filename: str, data: Dict[str, Any]):
    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] JSON saved: {path}")


def save_text(filename: str, content: str):
    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Text saved: {path}")


def layout_to_text(layout, text: str) -> str:
    """
    Extrae texto usando textAnchor.
    """

    response = ""

    if not layout.text_anchor.text_segments:
        return response

    for segment in layout.text_anchor.text_segments:
        start_index = int(segment.start_index) if segment.start_index else 0
        end_index = int(segment.end_index)
        response += text[start_index:end_index]

    return response


# ============================================
# MAIN DOCUMENT AI PROCESSOR
# ============================================


def process_document():
    print("=" * 80)
    print("DOCUMENT AI ANALYZER")
    print("=" * 80)

    ensure_output_dir()

    opts = ClientOptions(
        api_endpoint=f"{LOCATION}-documentai.googleapis.com"
    )

    client = documentai.DocumentProcessorServiceClient(
        client_options=opts
    )

    processor_name = client.processor_path(
        PROJECT_ID,
        LOCATION,
        PROCESSOR_ID
    )

    print(f"Processor: {processor_name}")

    # ============================================
    # READ PDF
    # ============================================

    with open(PDF_PATH, "rb") as f:
        pdf_content = f.read()

    raw_document = documentai.RawDocument(
        content=pdf_content,
        mime_type="application/pdf"
    )

    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=raw_document
    )

    print("\n[INFO] Sending document to Document AI...")

    result = client.process_document(request=request)

    document = result.document

    print("[OK] Processing completed")

    # ============================================
    # SAVE FULL RAW RESPONSE
    # ============================================

    raw_response = documentai.Document.to_dict(document)

    save_json(
        "01_full_document_ai_response.json",
        raw_response
    )

    # ============================================
    # SAVE FULL OCR TEXT
    # ============================================

    save_text(
        "02_full_ocr_text.txt",
        document.text
    )

    # ============================================
    # GENERAL METRICS
    # ============================================

    print("\n" + "=" * 80)
    print("GENERAL DOCUMENT METRICS")
    print("=" * 80)

    metrics = {
        "total_pages": len(document.pages),
        "total_characters": len(document.text),
        "document_text_preview": document.text[:1000]
    }

    print(json.dumps(metrics, indent=2, ensure_ascii=False))

    save_json(
        "03_general_metrics.json",
        metrics
    )

    # ============================================
    # PAGE ANALYSIS
    # ============================================

    pages_analysis = []

    print("\n" + "=" * 80)
    print("PAGE ANALYSIS")
    print("=" * 80)

    for page_index, page in enumerate(document.pages):

        page_data = {
            "page_number": page_index + 1,
            "dimension": {
                "width": page.dimension.width,
                "height": page.dimension.height,
                "unit": page.dimension.unit
            },
            "detected_languages": [],
            "blocks_count": len(page.blocks),
            "paragraphs_count": len(page.paragraphs),
            "lines_count": len(page.lines),
            "tokens_count": len(page.tokens),
            "tables_count": len(page.tables),
            "form_fields_count": len(page.form_fields),
            "image_quality_scores": {}
        }

        # ============================================
        # DETECTED LANGUAGES
        # ============================================

        for lang in page.detected_languages:
            page_data["detected_languages"].append({
                "language_code": lang.language_code,
                "confidence": lang.confidence
            })

        # ============================================
        # IMAGE QUALITY
        # ============================================

        if page.image_quality_scores:
            quality = page.image_quality_scores

            page_data["image_quality_scores"] = {
                "quality_score": quality.quality_score,
                "detected_defects": [
                    {
                        "type": defect.type_,
                        "confidence": defect.confidence
                    }
                    for defect in quality.detected_defects
                ]
            }

        pages_analysis.append(page_data)

        print(f"\nPAGE {page_index + 1}")
        print("-" * 40)
        print(f"Blocks: {len(page.blocks)}")
        print(f"Paragraphs: {len(page.paragraphs)}")
        print(f"Lines: {len(page.lines)}")
        print(f"Tokens: {len(page.tokens)}")
        print(f"Tables: {len(page.tables)}")
        print(f"Form fields: {len(page.form_fields)}")

    save_json(
        "04_pages_analysis.json",
        {"pages": pages_analysis}
    )

    # ============================================
    # TABLE ANALYSIS
    # ============================================

    print("\n" + "=" * 80)
    print("TABLE ANALYSIS")
    print("=" * 80)

    all_tables = []

    for page_index, page in enumerate(document.pages):

        for table_index, table in enumerate(page.tables):

            table_data = {
                "page": page_index + 1,
                "table_index": table_index,
                "header_rows": [],
                "body_rows": []
            }

            print(f"\nTABLE {table_index + 1} - PAGE {page_index + 1}")
            print("-" * 40)

            # ============================================
            # HEADER ROWS
            # ============================================

            for row in table.header_rows:
                row_data = []

                for cell in row.cells:
                    cell_text = layout_to_text(cell.layout, document.text)
                    row_data.append(cell_text)

                table_data["header_rows"].append(row_data)

                print(f"HEADER: {row_data}")

            # ============================================
            # BODY ROWS
            # ============================================

            for row in table.body_rows:
                row_data = []

                for cell in row.cells:
                    cell_text = layout_to_text(cell.layout, document.text)
                    row_data.append(cell_text)

                table_data["body_rows"].append(row_data)

                print(f"ROW: {row_data}")

            all_tables.append(table_data)

    save_json(
        "05_tables_analysis.json",
        {"tables": all_tables}
    )

    # ============================================
    # TOKEN CONFIDENCE ANALYSIS
    # ============================================

    print("\n" + "=" * 80)
    print("OCR CONFIDENCE ANALYSIS")
    print("=" * 80)

    token_confidences = []

    for page in document.pages:
        for token in page.tokens:
            token_confidences.append(token.layout.confidence)

    if token_confidences:
        avg_confidence = sum(token_confidences) / len(token_confidences)
        min_confidence = min(token_confidences)
        max_confidence = max(token_confidences)
    else:
        avg_confidence = 0
        min_confidence = 0
        max_confidence = 0

    confidence_metrics = {
        "average_token_confidence": avg_confidence,
        "minimum_token_confidence": min_confidence,
        "maximum_token_confidence": max_confidence,
        "total_tokens": len(token_confidences)
    }

    print(json.dumps(confidence_metrics, indent=2))

    save_json(
        "06_confidence_analysis.json",
        confidence_metrics
    )

    # ============================================
    # PARAGRAPH EXTRACTION
    # ============================================

    print("\n" + "=" * 80)
    print("PARAGRAPH EXTRACTION")
    print("=" * 80)

    paragraphs = []

    for page_index, page in enumerate(document.pages):

        for paragraph_index, paragraph in enumerate(page.paragraphs):
            paragraph_text = layout_to_text(
                paragraph.layout,
                document.text
            )

            paragraph_data = {
                "page": page_index + 1,
                "paragraph_index": paragraph_index,
                "confidence": paragraph.layout.confidence,
                "text": paragraph_text
            }

            paragraphs.append(paragraph_data)

    save_json(
        "07_paragraphs.json",
        {"paragraphs": paragraphs}
    )

    # ============================================
    # DETECT POSSIBLE SOF EVENTS
    # ============================================

    print("\n" + "=" * 80)
    print("POSSIBLE OPERATIONAL EVENTS")
    print("=" * 80)

    possible_events = []

    event_keywords = [
        "LOADING",
        "DISCHARGING",
        "COMMENCED",
        "COMPLETED",
        "STOPPED",
        "RESUMED",
        "WAITING",
        "BERTH",
        "NOR",
        "ARRIVED",
        "DEPARTED",
        "RAIN",
        "HOLD"
    ]

    lines = document.text.splitlines()

    for line in lines:

        upper_line = line.upper()

        if any(keyword in upper_line for keyword in event_keywords):
            possible_events.append(line)

    for event in possible_events[:50]:
        print(event)

    save_json(
        "08_possible_events.json",
        {"events": possible_events}
    )

    # ============================================
    # FINAL SUMMARY
    # ============================================

    print("\n" + "=" * 80)
    print("FINAL EVALUATION SUMMARY")
    print("=" * 80)

    summary = {
        "document_name": PDF_PATH,
        "pages": len(document.pages),
        "tables_detected": len(all_tables),
        "avg_ocr_confidence": avg_confidence,
        "possible_operational_events": len(possible_events),
        "recommendations": []
    }

    # ============================================
    # RECOMMENDATIONS
    # ============================================

    if avg_confidence >= 0.90:
        summary["recommendations"].append(
            "OCR quality is excellent"
        )
    elif avg_confidence >= 0.80:
        summary["recommendations"].append(
            "OCR quality is acceptable"
        )
    else:
        summary["recommendations"].append(
            "OCR quality may require human review"
        )

    if len(all_tables) > 0:
        summary["recommendations"].append(
            "Document AI successfully detected tables"
        )
    else:
        summary["recommendations"].append(
            "No tables detected - review layout quality"
        )

    if len(possible_events) > 0:
        summary["recommendations"].append(
            "Operational events detected successfully"
        )

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    save_json(
        "09_final_summary.json",
        summary
    )

    print("\n" + "=" * 80)
    print("FILES GENERATED")
    print("=" * 80)

    generated_files = [
        "01_full_document_ai_response.json",
        "02_full_ocr_text.txt",
        "03_general_metrics.json",
        "04_pages_analysis.json",
        "05_tables_analysis.json",
        "06_confidence_analysis.json",
        "07_paragraphs.json",
        "08_possible_events.json",
        "09_final_summary.json"
    ]

    for file in generated_files:
        print(f"- {file}")

    print("\nAnalysis completed successfully")


# ============================================
# DOCUMENT RECONSTRUCTION FROM JSON
# ============================================


def reconstruct_from_saved_json(json_path: str):
    """
    Permite analizar posteriormente un JSON ya generado
    por Document AI sin volver a consumir la API.

    Ideal para:
    - debugging
    - pruebas parsing
    - validaciones
    - reconstrucción tablas
    - normalización negocio
    """

    print("=" * 80)
    print("RECONSTRUCTING DOCUMENT AI JSON")
    print("=" * 80)

    ensure_output_dir()

    with open(json_path, "r", encoding="utf-8") as f:
        raw_json = json.load(f)

    document = documentai.Document.from_json(
        json.dumps(raw_json)
    )

    print("[OK] JSON loaded successfully")

    # ============================================
    # FULL TEXT
    # ============================================

    print("\n" + "=" * 80)
    print("FULL OCR TEXT")
    print("=" * 80)

    print(document.text[:3000])

    save_text(
        "10_reconstructed_full_text.txt",
        document.text
    )

    # ============================================
    # LINES RECONSTRUCTION
    # ============================================

    print("\n" + "=" * 80)
    print("LINES RECONSTRUCTION")
    print("=" * 80)

    reconstructed_lines = []

    for page_index, page in enumerate(document.pages):

        print(f"\nPAGE {page_index + 1}")
        print("-" * 40)

        for line_index, line in enumerate(page.lines):
            line_text = layout_to_text(
                line.layout,
                document.text
            )

            line_data = {
                "page": page_index + 1,
                "line_index": line_index,
                "confidence": line.layout.confidence,
                "text": line_text
            }

            reconstructed_lines.append(line_data)

            print(line_text)

    save_json(
        "11_reconstructed_lines.json",
        {"lines": reconstructed_lines}
    )

    # ============================================
    # TABLE RECONSTRUCTION
    # ============================================

    print("\n" + "=" * 80)
    print("TABLE RECONSTRUCTION")
    print("=" * 80)

    reconstructed_tables = []

    for page_index, page in enumerate(document.pages):

        for table_index, table in enumerate(page.tables):

            table_data = {
                "page": page_index + 1,
                "table_index": table_index,
                "headers": [],
                "rows": []
            }

            print(f"\nTABLE {table_index + 1}")
            print("-" * 40)

            # ============================================
            # HEADERS
            # ============================================

            for header_row in table.header_rows:

                header_values = []

                for cell in header_row.cells:
                    text = layout_to_text(cell.layout, document.text)
                    header_values.append(text.strip())

                table_data["headers"].append(header_values)

                print(f"HEADER: {header_values}")

            # ============================================
            # BODY ROWS
            # ============================================

            for body_row in table.body_rows:

                row_values = []

                for cell in body_row.cells:
                    text = layout_to_text(cell.layout, document.text)
                    row_values.append(text.strip())

                table_data["rows"].append(row_values)

                print(f"ROW: {row_values}")

            reconstructed_tables.append(table_data)

    save_json(
        "12_reconstructed_tables.json",
        {"tables": reconstructed_tables}
    )

    # ============================================
    # POSSIBLE OPERATIONAL EVENTS
    # ============================================

    print("\n" + "=" * 80)
    print("POSSIBLE SOF EVENTS")
    print("=" * 80)

    event_patterns = [
        "COMMENCED",
        "COMPLETED",
        "STOPPED",
        "RESUMED",
        "WAITING",
        "LOADING",
        "DISCHARGING",
        "RAIN",
        "NOR",
        "ARRIVED",
        "DEPARTED",
        "SHIFTING",
        "BERTH"
    ]

    detected_events = []

    for line in reconstructed_lines:

        upper_text = line["text"].upper()

        if any(pattern in upper_text for pattern in event_patterns):
            event_data = {
                "page": line["page"],
                "text": line["text"],
                "confidence": line["confidence"]
            }

            detected_events.append(event_data)

            print(f"EVENT: {line['text']}")

    save_json(
        "13_detected_operational_events.json",
        {"events": detected_events}
    )

    # ============================================
    # COLUMN DETECTION TEST
    # ============================================

    print("\n" + "=" * 80)
    print("COLUMN DETECTION TEST")
    print("=" * 80)

    possible_structured_rows = []

    for line in reconstructed_lines:

        text = line["text"]

        # Heurística simple para detectar columnas
        separators = ["  ", "\t"]

        detected = False

        for sep in separators:

            if sep in text:

                columns = [
                    col.strip()
                    for col in text.split(sep)
                    if col.strip()
                ]

                if len(columns) >= 3:
                    row_data = {
                        "raw_text": text,
                        "columns": columns,
                        "columns_count": len(columns)
                    }

                    possible_structured_rows.append(row_data)

                    print(columns)

                    detected = True
                    break

        if detected:
            continue

    save_json(
        "14_possible_structured_rows.json",
        {"rows": possible_structured_rows}
    )

    # ============================================
    # NORMALIZATION EXAMPLE
    # ============================================

    print("\n" + "=" * 80)
    print("NORMALIZATION EXAMPLE")
    print("=" * 80)

    normalized_events = []

    for event in detected_events:

        normalized = {
            "event_description": event["text"],
            "source_page": event["page"],
            "confidence": event["confidence"]
        }

        upper_text = event["text"].upper()

        if "COMMENCED" in upper_text:
            normalized["event_type"] = "COMMENCED_OPERATION"

        elif "COMPLETED" in upper_text:
            normalized["event_type"] = "COMPLETED_OPERATION"

        elif "STOPPED" in upper_text:
            normalized["event_type"] = "STOPPED_OPERATION"

        elif "RAIN" in upper_text:
            normalized["event_type"] = "WEATHER_DELAY"

        else:
            normalized["event_type"] = "OTHER"

        normalized_events.append(normalized)

    save_json(
        "15_normalized_events_example.json",
        {"normalized_events": normalized_events}
    )

    print(json.dumps(normalized_events[:10], indent=2))

    # ============================================
    # RECOMMENDATIONS
    # ============================================

    print("\n" + "=" * 80)
    print("RECONSTRUCTION RECOMMENDATIONS")
    print("=" * 80)

    recommendations = {
        "tables_detected": len(reconstructed_tables),
        "lines_detected": len(reconstructed_lines),
        "events_detected": len(detected_events),
        "recommendations": []
    }

    if len(reconstructed_tables) > 0:
        recommendations["recommendations"].append(
            "Use tables[] as primary source for structured data"
        )

    if len(detected_events) > 0:
        recommendations["recommendations"].append(
            "Use lines[] + NLP/Gemini for operational events"
        )

    if len(possible_structured_rows) == 0:
        recommendations["recommendations"].append(
            "Document layout may require Gemini contextual extraction"
        )

    recommendations["recommendations"].append(
        "Do not use document.text as primary relational source"
    )

    save_json(
        "16_reconstruction_recommendations.json",
        recommendations
    )

    print(json.dumps(recommendations, indent=2))

    print("\n[OK] Reconstruction completed successfully")


# ============================================
# ENTRYPOINT
# ============================================

if __name__ == "__main__":
    # ============================================
    # OPTION 1
    # Process PDF directly from Document AI
    # ============================================

    process_document()

    # ============================================
    # OPTION 2
    # Reconstruct previously saved JSON
    # ============================================

    # reconstruct_from_saved_json(
    #     "document_ai_outputs/01_full_document_ai_response.json"
    # )
