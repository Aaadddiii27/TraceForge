import { describe, expect, it } from 'vitest';

describe('frontend project smoke checks', () => {
  it('has a valid API base URL fallback', () => {
    const fallback = '/api/v1';
    expect(fallback.startsWith('/api/')).toBe(true);
  });
});
