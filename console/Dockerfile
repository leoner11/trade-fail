FROM node:22-alpine AS build
WORKDIR /app
COPY console/package.json console/package-lock.json ./
RUN npm ci
COPY console/ .
RUN npm run build

FROM caddy:2-alpine
COPY console/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
