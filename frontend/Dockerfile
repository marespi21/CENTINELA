# =============================================================================
# CENTINELA — Consola del analista (Next.js) · imagen multi-stage
# =============================================================================
# Tres etapas: dependencias, build y runtime. El runtime recibe SOLO la salida
# autónoma que produce `output: "standalone"` — un server.js con las
# dependencias justas — en vez de todo node_modules.
#
# Secretos: CERO. `ANALYST_API_KEY` y la URL de la API se leen en EJECUCIÓN
# (`src/lib/api/server.ts` prioriza `API_BASE_URL`), así que no hay nada que
# hornear en el build. `.env.local` está excluido en .dockerignore.
#
# Build:  docker build -f frontend/Dockerfile -t centinela-console:dev frontend
# =============================================================================

# --- Etapa 1: dependencias ---------------------------------------------------
FROM node:22-alpine AS deps
WORKDIR /app
# Solo los manifiestos: esta capa se reutiliza mientras no cambien las
# dependencias, aunque cambie el código.
COPY package.json package-lock.json ./
RUN npm ci

# --- Etapa 2: build ----------------------------------------------------------
FROM node:22-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Valor de relleno: lo que gobierna en producción es `API_BASE_URL`, inyectada
# por Container Apps en ejecución. No se hornea ninguna URL real.
ENV NEXT_PUBLIC_API_BASE=http://localhost:8000
RUN npm run build

# --- Etapa 3: runtime --------------------------------------------------------
FROM node:22-alpine AS runtime

LABEL org.opencontainers.image.title="centinela-console" \
      org.opencontainers.image.description="Consola del analista de CENTINELA" \
      org.opencontainers.image.source="https://github.com/marespi21/CENTINELA" \
      org.opencontainers.image.licenses="MIT"

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Usuario sin privilegios, mismo UID que las imágenes del backend.
RUN addgroup -g 10001 centinela && \
    adduser -u 10001 -G centinela -S -H centinela

WORKDIR /app
# `standalone` trae el servidor y sus dependencias; `static` y `public` van
# aparte porque Next los sirve como ficheros estáticos.
COPY --from=builder --chown=10001:10001 /app/.next/standalone ./
COPY --from=builder --chown=10001:10001 /app/.next/static ./.next/static
COPY --from=builder --chown=10001:10001 /app/public ./public

USER 10001:10001
EXPOSE 3000

# Sonda con el propio Node: instalar curl solo para esto añadiría superficie de
# ataque a cambio de nada.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:'+(process.env.PORT||3000)+'/',r=>process.exit(r.statusCode<500?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
