/**
 * K6 Performance Testing Script for Corporate Intel API
 * Run: k6 run k6-script.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

// Custom metrics
const errorRate = new Rate('errors');
const apiResponseTime = new Trend('api_response_time');
const apiRequests = new Counter('api_requests');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Spike to 200 users
    { duration: '5m', target: 200 },  // Stay at 200 users
    { duration: '3m', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],  // 95% < 500ms, 99% < 1s
    http_req_failed: ['rate<0.05'],                   // Error rate < 5%
    errors: ['rate<0.1'],                             // Custom error rate < 10%
  },
};

const BASE_URL = __ENV.API_URL || 'https://api.corporate-intel.com';

// Test data
const testUsers = [
  { email: 'test1@example.com', password: 'Test123!' },
  { email: 'test2@example.com', password: 'Test123!' },
  { email: 'test3@example.com', password: 'Test123!' },
];

// Helper function to get auth token
function login() {
  const user = testUsers[Math.floor(Math.random() * testUsers.length)];
  const res = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify(user), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => r.json('access_token') !== undefined,
  });

  return res.json('access_token');
}

// Main test scenario
export default function () {
  const token = login();
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  // Dashboard endpoint
  group('Dashboard', () => {
    const res = http.get(`${BASE_URL}/api/v1/dashboard`, { headers });

    check(res, {
      'dashboard status 200': (r) => r.status === 200,
      'dashboard has data': (r) => r.json('data') !== undefined,
    });

    apiResponseTime.add(res.timings.duration);
    apiRequests.add(1);
    errorRate.add(res.status !== 200);
  });

  sleep(1);

  // Organizations endpoint
  group('Organizations', () => {
    const res = http.get(`${BASE_URL}/api/v1/organizations?limit=20`, { headers });

    check(res, {
      'orgs status 200': (r) => r.status === 200,
      'orgs is array': (r) => Array.isArray(r.json('data')),
    });

    errorRate.add(res.status !== 200);
  });

  sleep(1);

  // Analytics query
  group('Analytics', () => {
    const payload = JSON.stringify({
      start_date: '2024-01-01T00:00:00Z',
      end_date: '2024-12-31T23:59:59Z',
      metrics: ['revenue', 'user_growth'],
      dimensions: ['region'],
    });

    const res = http.post(`${BASE_URL}/api/v1/analytics/query`, payload, { headers });

    check(res, {
      'analytics status 200': (r) => r.status === 200,
      'analytics has results': (r) => r.json('results') !== undefined,
      'response time < 2s': (r) => r.timings.duration < 2000,
    });

    errorRate.add(res.status !== 200);
  });

  sleep(2);

  // Search functionality
  group('Search', () => {
    const searchTerms = ['revenue', 'growth', 'market', 'trends'];
    const term = searchTerms[Math.floor(Math.random() * searchTerms.length)];

    const res = http.get(`${BASE_URL}/api/v1/search?q=${term}&limit=10`, { headers });

    check(res, {
      'search status 200': (r) => r.status === 200,
      'search has results': (r) => r.json('results') !== undefined,
    });

    errorRate.add(res.status !== 200);
  });

  sleep(1);

  // Report creation (write operation)
  group('Reports', () => {
    const payload = JSON.stringify({
      title: `K6 Test Report ${Date.now()}`,
      type: 'financial',
      parameters: {
        metrics: ['revenue', 'profit_margin'],
        period: 'monthly',
      },
    });

    const res = http.post(`${BASE_URL}/api/v1/reports`, payload, { headers });

    check(res, {
      'report created': (r) => r.status === 201 || r.status === 200,
      'report has id': (r) => r.json('id') !== undefined,
    });

    errorRate.add(res.status !== 201 && res.status !== 200);
  });

  sleep(1);
}

// Smoke test scenario
export function smokeTest() {
  const token = login();
  const headers = { 'Authorization': `Bearer ${token}` };

  const endpoints = [
    '/health',
    '/api/v1/dashboard',
    '/api/v1/organizations',
  ];

  endpoints.forEach((endpoint) => {
    const res = http.get(`${BASE_URL}${endpoint}`, { headers });
    check(res, { [`${endpoint} OK`]: (r) => r.status === 200 });
  });
}

// Stress test scenario
export function stressTest() {
  const token = login();
  const headers = { 'Authorization': `Bearer ${token}` };

  for (let i = 0; i < 10; i++) {
    http.get(`${BASE_URL}/api/v1/dashboard`, { headers });
  }
}

// Spike test scenario
export function spikeTest() {
  const token = login();
  const headers = { 'Authorization': `Bearer ${token}` };

  http.batch([
    ['GET', `${BASE_URL}/api/v1/dashboard`, null, { headers }],
    ['GET', `${BASE_URL}/api/v1/organizations`, null, { headers }],
    ['GET', `${BASE_URL}/api/v1/search?q=test`, null, { headers }],
  ]);
}

// Generate HTML report
export function handleSummary(data) {
  return {
    'summary.html': htmlReport(data),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}

// Setup and teardown
export function setup() {
  console.log('🚀 Starting K6 performance test...');
  console.log(`Target: ${BASE_URL}`);
  console.log(`Test duration: ~24 minutes`);
  return { startTime: Date.now() };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`✅ Test completed in ${duration}s`);
}
