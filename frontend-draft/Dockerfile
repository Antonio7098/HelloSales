FROM node:22-bullseye AS builder
WORKDIR /app/frontend-draft
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

FROM caddy:2-alpine
COPY --from=builder /app/frontend-draft/dist /var/www/html
COPY Caddyfile /etc/Caddyfile