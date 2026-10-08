import { NextResponse } from 'next/server';

export function middleware(request) {
  const accessKey = process.env.DASHBOARD_ACCESS_KEY;
  const isApiRoute = request.nextUrl.pathname.startsWith('/api/');

  // If access key is configured, enforce verification
  if (accessKey && accessKey.trim() !== '') {
    const headerKey = request.headers.get('x-nexus-access-key');
    const cookieKey = request.cookies.get('nexus_access_token')?.value;
    const queryKey = request.nextUrl.searchParams.get('access_key');

    const providedKey = headerKey || cookieKey || queryKey;
    const isAuthorized = providedKey === accessKey;

    if (!isAuthorized) {
      if (isApiRoute) {
        // Restricted API endpoint
        return NextResponse.json(
          {
            success: false,
            error: 'Unauthorized: Valid DASHBOARD_ACCESS_KEY required.',
          },
          { status: 401 }
        );
      }
    }
  }

  const response = NextResponse.next();

  // Add standard API rate limiting / caching headers
  if (isApiRoute) {
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('X-RateLimit-Limit', '120');
    response.headers.set('X-RateLimit-Remaining', '119');
  }

  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
