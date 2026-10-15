# Caddy with the Cloudflare DNS module (caddy-dns/cloudflare) for ACME DNS
# challenges. Built by .github/workflows/build-caddy.yml from the official
# caddy images; versions come from build args.
ARG CADDY_VERSION
FROM caddy:${CADDY_VERSION}-builder AS builder
ARG CLOUDFLARE_VERSION
# No file capability on the binary: stash-caddy runs with cap_drop: all, and
# the kernel refuses to exec a binary whose file capabilities are outside the
# bounding set ("exec /usr/bin/caddy: operation not permitted"). Binding 80/443
# as non-root uses the net.ipv4.ip_unprivileged_port_start sysctl instead.
ENV XCADDY_SETCAP=0
RUN xcaddy build --with github.com/caddy-dns/cloudflare@v${CLOUDFLARE_VERSION}

FROM caddy:${CADDY_VERSION}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
