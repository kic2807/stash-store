# Wisp relay for things-sideimpactor; see server.mjs.
# Built by .github/workflows/build-wisp-relay.yml.
FROM node:22.23.3-alpine3.24
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY server.mjs ./
USER node
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
CMD ["node", "server.mjs"]
