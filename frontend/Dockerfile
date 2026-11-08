# =============================================================================
# EcoMind Frontend - Multi-Stage Production Dockerfile
# Stage 1: Build production assets using Node.js 20 Alpine
# Stage 2: Serve static assets via lightweight Nginx Alpine
# =============================================================================

# --- Stage 1: Build ---
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests for deterministic dependency caching
COPY package.json package-lock.json ./

# Install clean dependencies using package-lock.json
RUN npm ci

# Copy application source code
COPY . .

# Optional build argument to configure the API base URL (empty defaults to relative / reverse-proxy)
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build production assets (TypeScript validation + Vite bundle)
RUN npm run build

# --- Stage 2: Production Server ---
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled SPA static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with SPA fallback and API reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port 80
EXPOSE 80

# Health check to ensure Nginx is serving the frontend
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]

