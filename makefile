FILE ?= 08a6902f-56f4-4408-aa78-d5af37894ce3.pdf

run-agent-platform:
	uv run cmd/agent_platform/main.py $(FILE)

run-document-ai:
	uv run cmd/document_ai/main.py $(FILE)

run-genai-studio:
	uv run cmd/genai_studio/main.py $(FILE)

run-opendataloader-server:
	uv run opendataloader-pdf-hybrid --port 5002 --force-ocr

run-opendataloader:
	 uv run cmd/opendataloader/main.py $(FILE)

run-glm-ocr:
	uv run cmd/glm-ocr/main.py $(FILE)

run-all: run-agent-platform run-document-ai run-genai-studio run-opendataloader run-glm-ocr

