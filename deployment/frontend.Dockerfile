FROM node:20.17.0-bookworm-slim AS build
WORKDIR /src
COPY upstream/jshERP-web/package.json .
COPY deployment/package-lock.json ./package-lock.json
RUN npm ci --legacy-peer-deps
COPY upstream/jshERP-web/ .
ENV NODE_OPTIONS=--openssl-legacy-provider
RUN npm run build
FROM nginx:1.28.0-alpine
COPY deployment/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
