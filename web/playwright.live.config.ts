import { defineConfig } from "@playwright/test";

const apiUrl = process.env.SJ_LIVE_E2E_API_URL ?? "http://127.0.0.1:8000";
const webUrl = process.env.SJ_LIVE_E2E_WEB_URL ?? "http://127.0.0.1:3002";
const supabaseUrl = process.env.SJ_LIVE_E2E_SUPABASE_URL ?? "http://127.0.0.1:54321";
const databaseUrl = process.env.SJ_DATABASE_URL ?? process.env.DATABASE_URL ?? "postgresql://postgres:postgres@127.0.0.1:5432/sloppy_jobulator";

export default defineConfig({
  testDir: "./tests-e2e",
  testMatch: "**/*.live.spec.ts",
  timeout: 120_000,
  expect: {
    timeout: 15_000
  },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: webUrl,
    trace: "retain-on-failure",
    channel: "chrome"
  },
  webServer: [
    {
      command: `python ../scripts/mock_supabase_auth.py --host 127.0.0.1 --port ${new URL(supabaseUrl).port || "54321"}`,
      cwd: __dirname,
      url: `${supabaseUrl}/healthz`,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000
    },
    {
      command: [
        `SJ_DATABASE_URL=${databaseUrl}`,
        `SJ_SUPABASE_URL=${supabaseUrl}`,
        "SJ_SUPABASE_ANON_KEY=test-key",
        "uv run --project api --extra dev uvicorn app.main:app --host 127.0.0.1 --port 8000",
      ].join(" "),
      cwd: `${__dirname}/..`,
      url: `${apiUrl}/healthz`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000
    },
    {
      command: `SJ_API_URL=${apiUrl} SJ_ADMIN_BEARER=admin-token pnpm dev --hostname 127.0.0.1 --port 3002`,
      cwd: __dirname,
      url: `${webUrl}/admin/cockpit`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000
    }
  ]
});
