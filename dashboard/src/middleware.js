import { NextResponse } from 'next/server.js';

export function constantTimeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

// In-memory sliding-window rate limiter (per-instance / per-isolate memory;
// does not share state across horizontally scaled serverless instances — see SECURITY.md §5).
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 60 seconds
const MAX_REQUESTS_PER_WINDOW = 60; // 60 requests per minute
const ipBuckets = new Map();

export function checkRateLimit(ip, maxRequests = MAX_REQUESTS_PER_WINDOW, windowMs = RATE_LIMIT_WINDOW_MS) {
  const now = Date.now();
  let bucket = ipBuckets.get(ip);

  // Periodic pruning if map gets large
  if (ipBuckets.size > 2000) {
    for (const [k, v] of ipBuckets.entries()) {
      if (now > v.resetTime) ipBuckets.delete(k);
    }
  }

  if (!bucket || now > bucket.resetTime) {
    bucket = { count: 1, resetTime: now + windowMs };
    ipBuckets.set(ip, bucket);
    return {
      allowed: true,
      remaining: maxRequests - 1,
      reset: Math.ceil(windowMs / 1000),
    };
  }

  if (bucket.count >= maxRequests) {
    const secondsRemaining = Math.max(1, Math.ceil((bucket.resetTime - now) / 1000));
    return {
      allowed: false,
      remaining: 0,
      reset: secondsRemaining,
    };
  }

  bucket.count += 1;
  const secondsRemaining = Math.max(1, Math.ceil((bucket.resetTime - now) / 1000));
  return {
    allowed: true,
    remaining: maxRequests - bucket.count,
    reset: secondsRemaining,
  };
}

export function middleware(request) {
  const pathname = request.nextUrl?.pathname || '';
  const isApiRoute = pathname.startsWith('/api/');

  // The web dashboard static assets & pages stay accessible for outside viewers
  if (!isApiRoute) {
    return NextResponse.next();
  }

  // Determine client IP
  const forwardedFor = request.headers.get('x-forwarded-for');
  const realIp = request.headers.get('x-real-ip');
  const clientIp = forwardedFor ? forwardedFor.split(',')[0].trim() : (realIp || '127.0.0.1');

  // Enforce Real Rate Limiting
  const rateLimit = checkRateLimit(clientIp);
  if (!rateLimit.allowed) {
    return NextResponse.json(
      {
        success: false,
        error: 'Too Many Requests: API rate limit exceeded.',
      },
      {
        status: 429,
        headers: {
          'Retry-After': String(rateLimit.reset),
          'X-RateLimit-Limit': String(MAX_REQUESTS_PER_WINDOW),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': String(rateLimit.reset),
        },
      }
    );
  }

  const isPublicMode = process.env.NEXUS_PUBLIC_MODE === 'true';
  const accessKey = process.env.DASHBOARD_ACCESS_KEY;

  // In Public Mode, outside viewers can freely view read-only APIs without access key gate
  if (!isPublicMode && accessKey && accessKey.trim() !== '') {
    // Only accept authorization via header or cookie.
    // Query string parameter (?access_key=) is explicitly disallowed to prevent leaking keys into server access logs.
    const headerKey = request.headers.get('x-nexus-access-key');
    const cookieKey = request.cookies.get('nexus_access_token')?.value;
    const providedKey = headerKey || cookieKey || '';

    const isAuthorized = constantTimeEqual(providedKey, accessKey.trim());

    if (!isAuthorized) {
      return NextResponse.json(
        {
          success: false,
          error: 'Unauthorized: Valid DASHBOARD_ACCESS_KEY required.',
        },
        { status: 401 }
      );
    }
  }

  const response = NextResponse.next();
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-RateLimit-Limit', String(MAX_REQUESTS_PER_WINDOW));
  response.headers.set('X-RateLimit-Remaining', String(rateLimit.remaining));
  response.headers.set('X-RateLimit-Reset', String(rateLimit.reset));
  return response;
}

export const config = {
  matcher: ['/api/:path*'],
};
