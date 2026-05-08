FROM node:22-bullseye AS builder
WORKDIR /app/frontend-draft

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL:-/api}

COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

FROM caddy:2-alpine
COPY --from=builder /app/frontend-draft/dist /usr/share/caddy
COPY Caddyfile /etc/caddy/Caddyfile