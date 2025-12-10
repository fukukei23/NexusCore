module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: ['**/*.test.ts'],
  collectCoverageFrom: [
    '*.ts',
    '!*.d.ts',
    '!index.ts', // エントリーポイントは除外（生成コード）
    '!api.ts', // 生成コードは除外
    '!configuration.ts', // 生成コードは除外
    '!base.ts', // 生成コードは除外
    '!common.ts', // 生成コードは除外
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  moduleNameMapper: {},
  testTimeout: 30000, // E2E テスト用に30秒
};

