import { test, expect } from '@playwright/test'

test('homepage loads', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/Pharma|Тахрир|Tahrir/i)
})

test('login page reachable', async ({ page }) => {
  await page.goto('/')
  // LoginGuard should render an email input
  const email = page.getByPlaceholder(/email/i).first()
  await expect(email).toBeVisible({ timeout: 10_000 })
})

test('backend health endpoint', async ({ request }) => {
  const apiBase = process.env.E2E_API_BASE || 'https://api.pharmtech.info'
  const res = await request.get(`${apiBase}/api/health`)
  expect(res.ok()).toBeTruthy()
  const json = await res.json()
  expect(json.status).toBe('ok')
})

test('public AI engines endpoint', async ({ request }) => {
  const apiBase = process.env.E2E_API_BASE || 'https://api.pharmtech.info'
  const res = await request.get(`${apiBase}/api/ai-engines`)
  expect(res.ok()).toBeTruthy()
  const json = await res.json()
  expect(json.engines).toBeDefined()
})
