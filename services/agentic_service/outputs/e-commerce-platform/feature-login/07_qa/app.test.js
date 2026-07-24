jest
import { app } from './app';

describe('API Health Check', () => {
  it('should return OK status for /api/health endpoint', async () => {
    const response = await fetch('/api/health');
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: 'ok' });
  });

  it('should rate limit API requests', async () => {
    // Simulate multiple requests within the windowMs
    for (let i = 0; i < 101; i++) {
      await fetch('/api/health');
    }

    const response = await fetch('/api/health');
    expect(response.status).toBe(429);
    expect(await response.json()).toEqual({
      error: { message: 'Too Many Requests' },
    });
  });

  it('should handle invalid requests', async () => {
    const response = await fetch('/api/invalid');
    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({
      error: { message: 'Not Found' },
    });
  });

  it('should handle errors in the middleware', async () => {
    app.use((req, res) => {
      throw new Error('Test error');
    });

    const response = await fetch('/api/health');
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: { message: 'Internal Server Error' },
    });
  });
});