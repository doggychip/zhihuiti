FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npx vite build --outDir dist/public 2>&1; echo "VITE EXIT: $?"
RUN npx esbuild server/index.ts --platform=node --bundle --format=cjs --outfile=dist/index.cjs --minify --external:pg --external:ws --external:express --external:cors 2>&1; echo "ESBUILD EXIT: $?"

FROM node:20-alpine AS production
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 8080
ENV NODE_ENV=production
ENV PORT=8080
CMD ["node", "dist/index.cjs"]
