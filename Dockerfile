# Multi-stage Docker build for production optimization
FROM node:18-alpine AS base

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    git \
    curl

WORKDIR /app

# Copy package files
COPY package*.json ./

FROM base AS deps

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Development stage
FROM base AS dev
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Build stage
FROM base AS builder
RUN npm ci
COPY . .

# Run build if script exists
RUN if npm run build &>/dev/null; then npm run build; else echo "No build script found"; fi

# Production stage
FROM node:18-alpine AS production

# Create app user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodeuser -u 1001

WORKDIR /app

# Install production dependencies
COPY --from=deps --chown=nodeuser:nodejs /app/node_modules ./node_modules
COPY --chown=nodeuser:nodejs package*.json ./

# Copy built application
COPY --from=builder --chown=nodeuser:nodejs /app/dist ./dist 2>/dev/null || true
COPY --from=builder --chown=nodeuser:nodejs /app/build ./build 2>/dev/null || true
COPY --from=builder --chown=nodeuser:nodejs /app/src ./src 2>/dev/null || true
COPY --chown=nodeuser:nodejs server.js . 2>/dev/null || true

# Set up health check
COPY --chown=nodeuser:nodejs <<EOF /app/healthcheck.js
const http = require('http');
const options = {
  host: 'localhost',
  port: process.env.PORT || 3000,
  path: '/health',
  timeout: 2000,
};

const request = http.request(options, (res) => {
  console.log('Health check status:', res.statusCode);
  process.exit(res.statusCode === 200 ? 0 : 1);
});

request.on('error', (err) => {
  console.log('Health check failed:', err.message);
  process.exit(1);
});

request.end();
EOF

# Switch to non-root user
USER nodeuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node /app/healthcheck.js

# Start the application
CMD ["node", "server.js"]