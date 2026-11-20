# ---- 1. build the website -------------------------------------------------
FROM node:18-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. API + website ----------------------------------------------------
# Python 3.9 + the pinned packages in requirements.txt are the versions the models were exported with.
FROM python:3.9-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY models/ models/
COPY --from=web /web/dist frontend/dist
ENV PORT=8000 MODEL_DIR=/app/models FRONTEND_DIST=/app/frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
