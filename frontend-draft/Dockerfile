FROM node:22-bullseye AS builder
WORKDIR /app/frontend-draft
COPY frontend-draft/package*.json ./
RUN npm install
COPY frontend-draft/ ./
RUN npm run build

FROM caddy:2-alpine
COPY --from=builder /app/frontend-draft/dist /var/www/html
COPY frontend-draft/Caddyfile /etc/Caddyfile