# apps/frontend/Dockerfile
# Multi-stage build: builder compiles the Vite app, nginx serves the result.

# ---------------------------------------------------------------------------
# Stage 1: builder – compile the React/Vite application
# ---------------------------------------------------------------------------
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies first (layer cache-friendly)
COPY package.json package-lock.json ./
RUN npm ci

# Build-time env vars baked into the JS bundle.
# VITE_API_BASE_URL="" → API calls go to the same origin (/api/...), nginx proxies them.
ARG VITE_API_BASE_URL=""
ARG REACT_APP_TILE_LAYER_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV REACT_APP_TILE_LAYER_URL=$REACT_APP_TILE_LAYER_URL

# Vite reads .env from envDir ("../../" relative to apps/frontend), but in
# Docker there is no repo root above /app. We place a minimal .env here so
# Vite does not error, and the ARGs above override the real values.
RUN touch ../../.env 2>/dev/null || true

COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: runtime – nginx serves the built static files
# ---------------------------------------------------------------------------
FROM nginx:alpine AS runtime

# Remove default nginx site
RUN rm /etc/nginx/conf.d/default.conf

# Our custom config (SPA fallback + /api/ proxy)
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
