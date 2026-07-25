import { expect } from '@jest/globals';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

describe('Vite Config', () => {
  it('should return a valid config object', async () => {
    const result = await defineConfig({
      plugins: [react()],
      server: {
        port: 5173,
      },
    });
    expect(result).toEqual({
      plugins: [{ name: 'react' }],
      server: { port: 5173 },
    });
  });

  it('should throw an error when plugin is missing', async () => {
    await expect(defineConfig({})).rejects.toThrowError(
      'Cannot read properties of undefined (reading "plugins")'
    );
  });

  it('should throw an error when server port is invalid', async () => {
    await expect(defineConfig({ server: { port: 'abc' } })).rejects.toThrowError(
      'Invalid port value: abc'
    );
  });
});

expect.extend({
  toEqual: (received, expected) =>
    expect(received).toEqual(expected),
});