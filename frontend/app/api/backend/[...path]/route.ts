import { NextRequest } from "next/server";

const BACKEND_BASE =
  process.env.BACKEND_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8012";
const BACKEND_API_KEY = process.env.GEMMALENS_API_KEY ?? process.env.NEXT_PUBLIC_GEMMALENS_API_KEY;

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

function backendUrl(path: string[], requestUrl: string) {
  const incoming = new URL(requestUrl);
  const target = new URL(path.join("/"), `${BACKEND_BASE.replace(/\/$/, "")}/`);
  target.search = incoming.search;
  return target;
}

function forwardedHeaders(request: NextRequest) {
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const accept = request.headers.get("accept");
  const range = request.headers.get("range");
  if (contentType) headers.set("content-type", contentType);
  if (accept) headers.set("accept", accept);
  if (range) headers.set("range", range);
  if (BACKEND_API_KEY) headers.set("x-gemmalens-api-key", BACKEND_API_KEY);
  return headers;
}

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const method = request.method;
  const response = await fetch(backendUrl(path, request.url), {
    method,
    headers: forwardedHeaders(request),
    body: method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer(),
    cache: "no-store"
  });

  const headers = new Headers();
  for (const key of ["content-type", "content-disposition", "content-length", "content-range", "accept-ranges"]) {
    const value = response.headers.get(key);
    if (value) headers.set(key, value);
  }
  return new Response(response.body, { status: response.status, headers });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
