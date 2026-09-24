# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
ARG NODE_IMAGE=node:24.19.0-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df
FROM ${NODE_IMAGE} AS build
WORKDIR /app
COPY package.json package-lock.json tsconfig.json ./
COPY scripts/prepare-ws.mjs scripts/prepare-ws.mjs
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY packages packages
RUN ./node_modules/.bin/tsc -p tsconfig.json

FROM ${NODE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-websocket && rm -rf /var/lib/apt/lists/*
WORKDIR /app/apps/home
COPY apps/home/package.json apps/home/package-lock.json ./
RUN npm ci --ignore-scripts --omit=dev --no-audit --no-fund && npm cache clean --force
COPY apps/home/*.mjs ./
COPY adapters/dsh-home /app/adapters/dsh-home
COPY adapters/dsh-execution /app/adapters/dsh-execution
COPY services /app/services
COPY release/product.json /app/release/product.json
COPY --from=build /app/dist /app/dist
COPY LICENSE /app/LICENSE
ENV NODE_ENV=production PYTHONDONTWRITEBYTECODE=1
USER node
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD ["node", "healthcheck.mjs"]
CMD ["node", "server.mjs"]
