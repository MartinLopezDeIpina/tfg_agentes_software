docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e WEBUI_AUTH=False \
  -e OPENAI_API_BASE_URL=http://172.17.0.1:5000/api \
  -e OPENAI_API_KEY=none \
  -e ENABLE_OLLAMA_API="False" \
  -e TASK_MODEL_EXTERNAL="agente_dummy" \
  -e RAG_EMBEDDING_MODEL="" \
  -e GLOBAL_LOG_LEVEL="DEBUG" \
  -e ENABLE_TITLE_GENERATION="True" \
  -e ENABLE_FOLLOW_UP_GENERATION="False" \
  -e ENABLE_TAGS_GENERATION="False" \
  -e ENABLE_AUTOCOMPLETE_GENERATION="False" \
  -e ENABLE_RETRIEVAL_QUERY_GENERATION="False" \
  -e ENABLE_IMAGE_PROMPT_GENERATION="False" \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
