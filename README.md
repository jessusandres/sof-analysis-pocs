# PDF AI OCR

Herramienta para procesamiento y extracción de texto de archivos PDF utilizando diferentes servicios de IA y OCR.

## Requisitos Previos

Para el correcto funcionamiento del proyecto, asegúrate de tener instaladas las siguientes dependencias:

- **Global**: `uv` para la gestión de dependencias.
- **opendataloader**: `brew install openjdk`
- **glm-ocr**: `brew install poppler`

## Instalación

Sincroniza las dependencias del proyecto:

```bash
uv sync
```

## Autenticación

Para autenticar los servicios de Google Cloud (recomendado):

```bash
bash <(curl -sSL https://storage.googleapis.com/cloud-samples-data/adc/setup_adc.sh)
```

## Uso y Comandos (Makefile)

El proyecto incluye un `makefile` para facilitar la ejecución de los diferentes módulos. Puedes especificar el archivo a procesar usando la variable `FILE`.

### Ejecución de módulos individuales

| Comando | Descripción |
|---------|-------------|
| `make run-agent-platform` | Ejecuta el OCR mediante Agent Platform. |
| `make run-document-ai` | Ejecuta el OCR mediante Google Document AI. |
| `make run-genai-studio` | Ejecuta el OCR mediante GenAI Studio. |
| `make run-glm-ocr` | Ejecuta el OCR mediante GLM. |
| `make run-opendataloader` | Ejecuta el OCR mediante OpenDataLoader. |

### Otros comandos

| Comando | Descripción |
|---------|-------------|
| `make run-opendataloader-server` | Inicia el servidor de OpenDataLoader en el puerto 5002. |
| `make run-all` | Ejecuta secuencialmente Agent Platform, Document AI, GenAI Studio y OpenDataLoader. |

### Ejemplo de uso con un archivo específico

```bash
make run-glm-ocr FILE=tu_archivo.pdf
```

Si no se especifica `FILE`, se utilizará el archivo por defecto definido en el Makefile.
