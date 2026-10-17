// Wisp relay for SideImpactor (things-sideimpactor).
//
// SideImpactor's browser code reaches Apple's servers through a Wisp
// WebSocket at /wisp/ on the page's own origin; TLS to Apple runs inside the
// browser, so this relay only forwards encrypted bytes. It is restricted the
// same way as upstream's Cloudflare Worker (backend/src/index.ts): only the
// Apple hosts SideImpactor needs, port 443, no direct IPs, no private or
// loopback addresses, no UDP.
import http from "node:http";
import { server as wisp, logging } from "@mercuryworkshop/wisp-js/server";

wisp.options.hostname_whitelist = [
  /^auth\.itunes\.apple\.com$/,
  /^buy\.itunes\.apple\.com$/,
  /^init\.itunes\.apple\.com$/,
  /^p\d+-buy\.itunes\.apple\.com$/,
  /^gsa\.apple\.com$/,
  /^developerservices2\.apple\.com$/,
];
wisp.options.port_whitelist = [443];
wisp.options.allow_direct_ip = false;
wisp.options.allow_private_ips = false;
wisp.options.allow_loopback_ips = false;
wisp.options.allow_udp_streams = false;
wisp.options.allow_tcp_streams = true;
wisp.options.wisp_version = 1;
// Client IPs only matter for logs; the relay sits behind Caddy.
wisp.options.parse_real_ip = false;
logging.set_level(logging[process.env.LOG_LEVEL || "INFO"] ?? logging.INFO);

const port = parseInt(process.env.PORT || "8080", 10);

const server = http.createServer((req, res) => {
  if (req.url === "/healthz") {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("ok");
    return;
  }
  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("only /wisp/ (WebSocket) is served here");
});

server.on("upgrade", (req, socket, head) => {
  if (req.url.startsWith("/wisp/")) {
    wisp.routeRequest(req, socket, head);
  } else {
    socket.destroy();
  }
});

server.listen(port, "0.0.0.0", () => {
  logging.info(`wisp relay listening on :${port}`);
});

for (const sig of ["SIGTERM", "SIGINT"]) {
  process.on(sig, () => server.close(() => process.exit(0)));
}
