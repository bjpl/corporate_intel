/**
 * Jest Setup File
 * Configures test environment for migration tests
 */

// Extend Jest timeout for database operations
jest.setTimeout(30000);

// Global test utilities
global.testUtils = {
  /**
   * Wait for a condition to be true
   */
  waitFor: async (condition, timeout = 5000, interval = 100) => {
    const startTime = Date.now();
    while (!await condition()) {
      if (Date.now() - startTime > timeout) {
        throw new Error('Timeout waiting for condition');
      }
      await new Promise(resolve => setTimeout(resolve, interval));
    }
  },

  /**
   * Retry a function with exponential backoff
   */
  retry: async (fn, maxRetries = 3, delay = 1000) => {
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await fn();
      } catch (error) {
        if (i === maxRetries - 1) throw error;
        await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
      }
    }
  },

  /**
   * Generate random test data
   */
  randomString: (length = 10) => {
    return Math.random().toString(36).substring(2, length + 2);
  },

  /**
   * Format SQL for readable error messages
   */
  formatSQL: (sql) => {
    return sql
      .replace(/\s+/g, ' ')
      .trim()
      .substring(0, 100) + '...';
  }
};

// Console formatting for test output
const originalLog = console.log;
console.log = (...args) => {
  originalLog('\n', ...args);
};

// Error formatting
const originalError = console.error;
console.error = (...args) => {
  originalError('\n[ERROR]', ...args);
};

// Cleanup on test completion
afterAll(async () => {
  // Give time for async operations to complete
  await new Promise(resolve => setTimeout(resolve, 1000));
});
