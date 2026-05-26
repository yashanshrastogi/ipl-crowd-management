import { afterEach, describe, expect, it, vi } from 'vitest';

async function loadConstants() {
  vi.resetModules();
  return import('./constants.js');
}

describe('API_BASE_URL', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('falls back to the local Vite proxy', async () => {
    vi.stubEnv('VITE_BACKEND_URL', '');

    const { API_BASE_URL } = await loadConstants();

    expect(API_BASE_URL).toBe('/api');
  });

  it('uses the deployed backend URL without a trailing slash', async () => {
    vi.stubEnv('VITE_BACKEND_URL', 'https://backend.example.com/');

    const { API_BASE_URL } = await loadConstants();

    expect(API_BASE_URL).toBe('https://backend.example.com');
  });
});
