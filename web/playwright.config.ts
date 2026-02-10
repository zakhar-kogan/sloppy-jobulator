import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests-e2e",
  testIgnore: "**/*.live.spec.ts",
  timeout: 60_000,
  expect: {
    timeout: 10_000
  },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3001",
    trace: "retain-on-failure",
    channel: "chrome"
  },
  webServer: {
    command: "pnpm dev --hostname 127.0.0.1 --port 3001",
    url: "http://127.0.0.1:3001/admin/cockpit",
    cwd: __dirname,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000
  }
});
