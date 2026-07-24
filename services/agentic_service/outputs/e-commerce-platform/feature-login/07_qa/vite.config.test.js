Here are the functional test cases for the provided source code using Jest:

jest
import { defineConfig } from "vite";
import { react } from "@vitejs/plugin-react";

describe('Vite Config', () => {
  it('defines a Vite config with React plugin', () => {
    const config = defineConfig({
      plugins: [react()],
      server: {
        port: 5173,
      },
    });

    expect(config).toEqual({
      plugins: [{ name: 'react' }],
      server: { port: 5173 },
    });
  });

  it('throws an error if React plugin is not provided', () => {
    expect(() => defineConfig({ server: { port: 5173 } })).toThrowError();
  });

  it('defines a Vite config with default port', () => {
    const config = defineConfig({
      plugins: [react()],
    });

    expect(config).toEqual({
      plugins: [{ name: 'react' }],
      server: { port: 3000 },
    });
  });

  it('throws an error if invalid port is provided', () => {
    expect(() => defineConfig({ server: { port: -1 } })).toThrowError();
  });

  it('defines a Vite config with custom port', () => {
    const config = defineConfig({
      plugins: [react()],
      server: {
        port: 8080,
      },
    });

    expect(config).toEqual({
      plugins: [{ name: 'react' }],
      server: { port: 8080 },
    });
  });
});