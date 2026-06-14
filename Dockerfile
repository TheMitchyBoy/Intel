FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./

ARG VITE_API_KEY=dev-api-key
ENV VITE_API_KEY=$VITE_API_KEY
ENV VITE_API_URL=

RUN npm run build

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY . .
COPY --from=frontend-build /frontend/dist /app/static

RUN chmod +x /app/start.sh

ENV PYTHONPATH=/app

CMD ["/app/start.sh"]
