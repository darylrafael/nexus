import test from 'node:test';
import assert from 'node:assert/strict';
import { constantTimeEqual, checkRateLimit, middleware } from '../src/middleware.js';

test('constantTimeEqual verifies strings in constant time', () => {
  assert.equal(constantTimeEqual('secret123', 'secret123'), true);
  assert.equal(constantTimeEqual('secret123', 'secret124'), false);
  assert.equal(constantTimeEqual('secret123', 'secret12'), false);
  assert.equal(constantTimeEqual('secret123', 'secret1234'), false);
  assert.equal(constantTimeEqual('', ''), true);
  assert.equal(constantTimeEqual(null, 'secret'), false);
  assert.equal(constantTimeEqual(undefined, 'secret'), false);
  assert.equal(constantTimeEqual('secret', 12345), false);
});

test('checkRateLimit enforces sliding-window rate limit', () => {
  const testIp = '192.168.1.99';
  const max = 3;
  const windowMs = 5000;

  // First 3 requests allowed
  const r1 = checkRateLimit(testIp, max, windowMs);
  assert.equal(r1.allowed, true);
  assert.equal(r1.remaining, 2);

  const r2 = checkRateLimit(testIp, max, windowMs);
  assert.equal(r2.allowed, true);
  assert.equal(r2.remaining, 1);

  const r3 = checkRateLimit(testIp, max, windowMs);
  assert.equal(r3.allowed, true);
  assert.equal(r3.remaining, 0);

  // 4th request blocked
  const r4 = checkRateLimit(testIp, max, windowMs);
  assert.equal(r4.allowed, false);
  assert.equal(r4.remaining, 0);
  assert.ok(r4.reset > 0);
});

test('middleware checks header and cookie auth and rejects query-string key', async () => {
  const originalKey = process.env.DASHBOARD_ACCESS_KEY;
  const originalPublic = process.env.NEXUS_PUBLIC_MODE;

  try {
    process.env.DASHBOARD_ACCESS_KEY = 'buy_side_secret_token';
    delete process.env.NEXUS_PUBLIC_MODE;

    // Helper to simulate request
    const createReq = ({ pathname = '/api/stats', headers = {}, cookies = {}, search = '' }) => ({
      nextUrl: { pathname, search },
      headers: {
        get: (h) => headers[h.toLowerCase()] || null,
      },
      cookies: {
        get: (c) => (cookies[c] ? { value: cookies[c] } : null),
      },
    });

    // 1. No credentials -> 401
    const unauthReq = createReq({});
    const res1 = middleware(unauthReq);
    assert.equal(res1.status, 401);

    // 2. Query string key -> rejected with 401 (explicitly not allowed)
    const queryReq = createReq({ search: '?access_key=buy_side_secret_token' });
    const res2 = middleware(queryReq);
    assert.equal(res2.status, 401);

    // 3. Header key -> 200 / Next
    const headerReq = createReq({
      headers: { 'x-nexus-access-key': 'buy_side_secret_token' },
    });
    const res3 = middleware(headerReq);
    assert.equal(res3.status, 200);
    assert.equal(res3.headers.get('X-Content-Type-Options'), 'nosniff');

    // 4. Cookie key -> 200 / Next
    const cookieReq = createReq({
      cookies: { nexus_access_token: 'buy_side_secret_token' },
    });
    const res4 = middleware(cookieReq);
    assert.equal(res4.status, 200);

    // 5. Public mode enables access without key
    process.env.NEXUS_PUBLIC_MODE = 'true';
    const publicReq = createReq({});
    const res5 = middleware(publicReq);
    assert.equal(res5.status, 200);
  } finally {
    process.env.DASHBOARD_ACCESS_KEY = originalKey;
    process.env.NEXUS_PUBLIC_MODE = originalPublic;
  }
});

test('rate limiter demonstrates per-instance in-memory isolation (Phase D5 & SECURITY.md)', async () => {
  // Instance A and Instance B simulate two isolated serverless runtime isolates
  const nonce = Date.now();
  const modA = await import(`../src/middleware.js?instance=A&t=${nonce}`);
  const modB = await import(`../src/middleware.js?instance=B&t=${nonce}`);

  const testIp = '10.200.1.55';
  const max = 2;
  const windowMs = 10000;

  // Exhaust limit on Instance A
  assert.equal(modA.checkRateLimit(testIp, max, windowMs).allowed, true);
  assert.equal(modA.checkRateLimit(testIp, max, windowMs).allowed, true);
  assert.equal(modA.checkRateLimit(testIp, max, windowMs).allowed, false);

  // Instance B has its own independent in-memory bucket (not shared)
  const resB1 = modB.checkRateLimit(testIp, max, windowMs);
  assert.equal(resB1.allowed, true);
  assert.equal(resB1.remaining, 1);
});

