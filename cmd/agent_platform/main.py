import base64
import os
import sys

from pathlib import Path
from google import genai
from google.genai import types

project_folder = os.path.abspath(os.curdir)

print("Project Folder:", project_folder)

docs_path = os.path.join(project_folder, "docs")
out_path = os.path.join(project_folder, "output", "agent_platform")
MODEL = "gemini-2.5-pro"

print("Docs Path:", docs_path)
print("Output Path:", out_path)

filename = sys.argv[1] if len(sys.argv) > 1 else sys.exit("No filename provided.")

def decode_pdf_to_base64(file_path):
    with open(os.path.join(docs_path, file_path), "rb") as pdf_file:
        pdf_bytes = pdf_file.read()
        base64_string = base64.b64encode(pdf_bytes).decode("utf-8")
    
    return base64_string

def save_text_to_file(text, file_name):
    
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    if not os.path.exists(os.path.join(out_path, file_name)):
        Path(os.path.join(out_path, file_name)).touch()

    with open(os.path.join(out_path, file_name), "w") as text_file:
        text_file.write(text)

def generate():
  client = genai.Client(
      vertexai=True,
      api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
  )

  pdf_base64_string = decode_pdf_to_base64(filename)

  document1 = types.Part.from_bytes(
      data=base64.b64decode(pdf_base64_string),
      mime_type="application/pdf",
  )
  si_text1 = """Eres un sistema automatizado de Procesamiento Inteligente de Documentos (IDP). Tu función exclusiva es analizar, corregir y extraer información de documentos escaneados (PDF o imágenes) cuyo concepto es SOF (Statement of Facts), devolviendo los resultados ESTRICTAMENTE en formato JSON.

Reglas de Procesamiento:

Deducción de contexto: Los documentos son escaneos y pueden contener errores tipográficos o caracteres mal reconocidos. Debes analizar el contexto de la frase o tabla para deducir y corregir automáticamente la palabra o valor correcto.

Normalización de Tablas: Si el documento contiene tablas, extrae su contenido y represéntalo como un arreglo (array) de objetos JSON, donde las claves (keys) sean los encabezados de las columnas en formato camelCase.

Restricción de Formato: Eres una API backend. Tu respuesta no debe contener saludos, explicaciones, ni formato Markdown (NO envuelvas la respuesta en ```json ```). Responde ÚNICA y EXCLUSIVAMENTE con el objeto JSON puro.

Estructura de Respuesta Esperada:

Si el análisis es exitoso:
{
\"status\": \"success\",
\"message\": \"Información extraída y estructurada correctamente\",
\"data\": {
\"tituloDocumento\": \"...\",
\"fecha\": \"...\",
\"tablas\": [
{ \"columnaA\": \"valor\", \"columnaB\": \"valor\" }
],
\"otrosCamposRelevantes\": \"...\"
}
}

Si ocurre un error (no se recibe PDF, documento ilegible, etc.) NO incluyas el nodo \"data\":
{
\"status\": \"error\",
\"message\": \"Por favor bríndame un archivo PDF válido para analizar.\"
}"""

  model = MODEL
  contents = [
    types.Content(
      role="user",
      parts=[
        types.Part.from_text(text="""Analiza y extrae la información de este documento SOF."""),
        document1
      ]
    )
  ]

  tools = [
    types.Tool(google_search=types.GoogleSearch()),
  ]

  generate_content_config = types.GenerateContentConfig(
    temperature = 0.8,
    top_p = 1,
    max_output_tokens = 65535,
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    tools = tools,
    system_instruction=[types.Part.from_text(text=si_text1)],
    thinking_config=types.ThinkingConfig(
      thinking_budget=-1,
    ),
  )

  text = ""

  total_input_tokens = 0
  total_output_tokens = 0

  for chunk in client.models.generate_content_stream(model = model, contents = contents, config = generate_content_config,):
    if chunk.usage_metadata:
        total_input_tokens = chunk.usage_metadata.prompt_token_count
        total_output_tokens = chunk.usage_metadata.candidates_token_count
        
    if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
        continue
    
    text += chunk.text
  
  print("Final Output:", text)

  precio_input = (total_input_tokens / 1_000_000) * 1.25
  precio_output = (total_output_tokens / 1_000_000) * 10.00
  precio_total = precio_input + precio_output

  print(f"Input tokens: {total_input_tokens}")
  print(f"Output tokens (including thinking): {total_output_tokens}")
  print(f"Estimated cost: ${precio_total:.6f} USD")

  # Replace ```json and ``` if they exist in the text, since we want pure JSON output without markdown formatting.
  final_text = text.replace("```json", "").replace("```", "").strip()

  save_text_to_file(final_text, filename.replace(".pdf", ".json"))


generate()