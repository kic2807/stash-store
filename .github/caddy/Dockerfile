# Caddy with the Cloudflare DNS module (caddy-dns/cloudflare) for ACME DNS
# challenges. Built by .github/workflows/build-caddy.yml from the official
# caddy images; versions come from build args.
ARG CADDY_VERSION
FROM caddy:${CADDY_VERSION}-builder AS builder
ARG CLOUDFLARE_VERSION
RUN xcaddy build --with github.com/caddy-dns/cloudflare@v${CLOUDFLARE_VERSION}

FROM caddy:${CADDY_VERSION}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
