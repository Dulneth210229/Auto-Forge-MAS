import { expect } from '@jest/globals';
import expressApp from './app';

describe('Express App', () => {
  it('should return OK on /api/health', async () => {
    const response = await fetch('/api/health');
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: 'ok' });
  });

  it('should limit API requests to 100 within 15 minutes', async () => {
    for (let i = 0; i < 101; i++) {
      await fetch('/api/health');
    }
    const response = await fetch('/api/health');
    expect(response.status).toBe(429);
  });

  it('should handle invalid input and return 500', async () => {
    const response = await fetch('/api/non-existent-route');
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: { message: 'Internal Server Error' },
    });
  });

  it('should handle rate limit exceeded and return 429', async () => {
    for (let i = 0; i < 101; i++) {
      await fetch('/api/health');
    }
    const response = await fetch('/api/health');
    expect(response.status).toBe(429);
  });
});