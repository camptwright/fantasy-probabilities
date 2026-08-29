import { createRemoteJWKSet, jwtVerify } from "jose";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const team = process.env.CF_ACCESS_TEAM_DOMAIN;
  const audience = process.env.CF_ACCESS_AUD;
  // Without an ingress configuration the dashboard is bound to localhost and
  // accessed through SSH. Cloudflare Access becomes mandatory when configured.
  if (!team || !audience) return NextResponse.next();
  const token = request.headers.get("Cf-Access-Jwt-Assertion");
  if (!token) return new NextResponse("Cloudflare Access authentication required", { status: 401 });
  try {
    const jwks = createRemoteJWKSet(new URL(`https://${team}/cdn-cgi/access/certs`));
    await jwtVerify(token, jwks, { audience });
    return NextResponse.next();
  } catch {
    return new NextResponse("Invalid Cloudflare Access credential", { status: 401 });
  }
}

export const config = { matcher: ["/fantasy/:path*"] };
