/** Only run against the isolated synthetic API profile described in docs/web/C21_WEB_BASELINE.md. */
import assert from 'node:assert/strict'
import { chromium, expect } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:4173').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
assert.ok(process.argv.includes('--synthetic-profile'), 'Requires an isolated synthetic API profile; accepts its agreement and creates one fixture project; discard the isolated profile after stopping the API.')
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage()
const errors = []
page.on('pageerror', () => errors.push('pageerror')) // Never log arbitrary error bodies.
await page.addInitScript(() => {
  window.addEventListener('unhandledrejection', () => { document.documentElement.dataset.unhandledRejection = 'true' })
})
let projectId
try {
  await page.goto(`${origin}/projects`)
  const settingsResponse = await page.request.get(`${origin}/api/settings`)
  assert.equal(settingsResponse.status(), 200)
  const settings = await settingsResponse.json()
  assert.equal(settings.platform, 'web')
  assert.equal(settings.capabilities.local_file_sync, false)
  if (settings.values.user_agreement !== true) {
    await page.locator('input[type="checkbox"]').check()
    await page.locator('.agreement-actions button').last().click()
  }
  await expect(page.locator('.app-shell')).toBeVisible()
  await page.waitForLoadState('networkidle')
  const nativeState = await page.evaluate(() => ({
    platform: document.documentElement.dataset.platform,
    tauriAbsent: typeof window.__TAURI_INTERNALS__ === 'undefined',
    capacitorNative: window.Capacitor?.isNativePlatform?.() ?? false,
  }))
  assert.deepEqual(nativeState, { platform: 'web', tauriAbsent: true, capacitorNative: false })
  const created = await page.request.post(`${origin}/api/projects`, { data: { name: 'C21 synthetic browser fixture', goal: 1000 } })
  assert.equal(created.status(), 201)
  projectId = (await created.json()).id
  const routes = ['/projects', `/projects/${projectId}`, '/texts', '/maps', '/notes', `/notes/${projectId}`, `/maps/${projectId}`, '/game', '/integrations', '/help', '/settings']
  for (const route of routes) {
    await page.goto(origin + route)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.app-shell')).toBeVisible()
    await expect(page.locator('ion-router-outlet .ion-page').last()).toBeVisible()
    console.log(`route ${route}: rendered`)
    await page.waitForTimeout(300)
    assert.equal(await page.locator('html').getAttribute('data-unhandled-rejection'), null)
  }
  await page.goto(origin + '/integrations')
  await page.waitForLoadState('networkidle')
  await expect(page.locator('#local-sync-unavailable-title')).toBeVisible()
  await page.goto(origin + '/settings')
  await page.waitForLoadState('networkidle')
  await expect(page.locator('#diagnostics-title')).toHaveCount(0)
  console.log('native feature restrictions: checked')
  await page.goto(origin + '/admin/login')
  await expect(page.locator('input').first()).toBeVisible()
  console.log('admin login: rendered')
  assert.deepEqual(errors, [])

  const offline = await browser.newPage()
  await offline.route('**/api/settings', route => route.abort())
  await offline.goto(origin + '/projects')
  await expect(offline.locator('[role="alert"]')).toBeVisible()
  await expect(offline.locator('.app-shell')).toHaveCount(0)
  await offline.close()
  console.log(JSON.stringify({ result: 'PASS', nativeState, routes, features: ['agreement', 'file-sync unavailable', 'native diagnostics hidden', 'admin login', 'API failure gate'], pageErrors: errors.length }))
} catch (error) {
  console.error('Browser smoke assertion failed')
  throw error
} finally {
  await browser.close()
}
