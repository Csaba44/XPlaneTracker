FROM node:20-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm install

COPY worker.js .
COPY wrangler.toml .

EXPOSE 8787

# workerd reads this env var for its CA bundle
ENV WORKERD_TLS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

CMD ["npx", "wrangler", "dev", "worker.js", "--port", "8787", "--ip", "0.0.0.0", "--local"]