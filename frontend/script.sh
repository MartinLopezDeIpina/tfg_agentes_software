docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e WEBUI_AUTH=False \
  -e OPENAI_API_BASE_URL=http://172.17.0.1:5000/api \
  -e OPENAI_API_KEY=none \
  -e TASK_MODEL_EXTERNAL="agente_dummy" \
  -e RAG_EMBEDDING_MODEL="" \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
