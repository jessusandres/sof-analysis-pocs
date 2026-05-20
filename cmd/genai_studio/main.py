# 1. Instalación de librerías
# !pip install -q google-genai pydantic

import os
import json
import sys
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# from google.colab import userdata

load_dotenv()

ROOT_DIR = os.path.abspath(os.curdir)
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output", "genai_studio")
MODEL = "gemini-2.5-flash"

print(f"Using model: {MODEL}")


# --- ESQUEMA JERÁRQUICO UNIFICADO ---
class DetalleOperacion(BaseModel):
    recurso: str = Field(description="Ej: CRANE 1, GANG 2. Heredar del anterior si está vacío.")
    inicio: str = Field(description="Formato YYYY-MM-DD HH:MM")
    fin: str = Field(description="Formato YYYY-MM-DD HH:MM")
    evento: str = Field(description="Descripción de la actividad")
    bodega: Optional[str] = Field(None, description="Bodega/Hold si aplica")


class ReporteSOF(BaseModel):
    nro_reporte: str = Field(description="N° de reporte o Turno")
    vessel: str = Field(description="Nombre del buque")
    fecha: str = Field(description="Fecha del turno")
    shipper: str = Field(description="Exportador detectado")
    operaciones: List[DetalleOperacion]


class DocumentoFinal(BaseModel):
    empresa_emisora: str = Field(description="Terminal o Agencia detectada")
    barco_principal: str
    reportes: List[ReporteSOF]


# --- MOTOR DE EXTRACCIÓN CON CONTADOR DE COSTOS ---

def procesar_sofs_masivo(lista_archivos):
    # client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    client = genai.Client(vertexai=True, api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"))

    resultados_totales = []

    # Variables para el conteo de tokens global
    total_in = 0
    total_out = 0

    # Precio del dólar hoy (puedes ajustarlo)
    VALOR_DOLAR_CLP = 950

    print(f"🚀 Iniciando procesamiento de {len(lista_archivos)} archivos...")

    for archivo in lista_archivos:
        if not os.path.exists(archivo):
            print(f"⚠️ Saltando {archivo}: No encontrado.")
            continue

        print(f"📄 Analizando: {archivo}...")

        try:
            # file_up = client.files.upload(file=archivo)
            # prompt = "Extrae la información jerárquica de este SOF. Agrupa por número de reporte y normaliza las tablas."

            with open(archivo, "rb") as f:
                pdf_bytes = f.read()

            document_part = types.Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf",
            )

            prompt_part = types.Part.from_text(
                text="Extrae la información jerárquica de este SOF. Agrupa por número de reporte y normaliza las tablas.")

            response = client.models.generate_content(
                model=MODEL,
                # contents=[file_up, prompt],
                contents=[document_part, prompt_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DocumentoFinal,
                    temperature=0.0
                ),
            )

            # Acumular tokens
            if response.usage_metadata:
                total_in += response.usage_metadata.prompt_token_count
                total_out += response.usage_metadata.candidates_token_count

            resultados_totales.append(json.loads(response.text))
            # client.files.delete(name=file_up.name)

            # Pausa para no saturar la cuota gratuita (Rate Limit)
            time.sleep(3)

        except Exception as e:
            print(f"❌ Error en {archivo}: {e}")

    # --- CÁLCULO DE COSTOS FINALES ---
    costo_usd = ((total_in / 1_000_000) * 0.075) + ((total_out / 1_000_000) * 0.30)
    costo_clp = costo_usd * VALOR_DOLAR_CLP

    print("\n" + "=" * 50)
    print("🎉 ¡PROCESAMIENTO COMPLETO!")
    print("-" * 50)
    print(f"📊 REPORTES PROCESADOS: {len(resultados_totales)}")
    print(f"📥 TOKENS ENTRADA TOTALES: {total_in:,}")
    print(f"📤 TOKENS SALIDA TOTALES: {total_out:,}")
    print("-" * 50)
    print(f"💰 COSTO TOTAL USD: ${costo_usd:.6f} USD")
    print(f"🇨🇱 COSTO TOTAL CLP: ${costo_clp:.2f} Pesos")
    print("=" * 50)

    return resultados_totales


filename = sys.argv[1] if len(sys.argv) > 1 else sys.exit("No filename provided.")
sof_files = [
    os.path.join(DOCS_DIR, filename)
]

# Ejecutar
data_final = procesar_sofs_masivo(sof_files)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Guardar Consolidado
with open(os.path.join(OUTPUT_DIR, f"{filename}_consolidado_total.json"), "w", encoding="utf-8") as f:
    json.dump(data_final, f, ensure_ascii=False, indent=2)
