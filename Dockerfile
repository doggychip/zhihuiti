FROM node:20-alpine AS builder
WORKDIR /app
COPY zhihuiti/ ./
RUN npm ci
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 8080
ENV NODE_ENV=production
ENV PORT=8080
CMD ["node", "dist/index.cjs"]
