import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { installUi005Api } from './fixtures'

test.describe('UI-005 truthful settings and evaluation', () => {
  test('settings renders the non-secret server profile and passes accessibility', async ({ page }) => {
    await installUi005Api(page)
    await page.goto('/settings')

    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
    await expect(page.getByText('Balanced')).toBeVisible()
    await expect(page.getByText('Configured', { exact: true })).toBeVisible()
    await expect(page.getByText('Not configured', { exact: true })).toBeVisible()
    await expect(page.getByText('node_modules')).toBeVisible()
    await expect(page.getByText(/PATCH \/settings\/preferences/)).toBeVisible()
    await expectKeyboardTarget(page)
    await expectNoSeriousAccessibilityViolations(page)
  })

  test('settings reports permission denial without leaking profile data', async ({ page }) => {
    await installUi005Api(page, { settingsMode: 'permission' })
    await page.goto('/settings')

    await expect(page.getByText('Access denied')).toBeVisible()
    await expect(page.getByText('You do not have access to this data.')).toBeVisible()
    await expect(page.getByText('Balanced')).toHaveCount(0)
  })

  test('settings exposes bounded retry and recovers in place', async ({ page }) => {
    const api = await installUi005Api(page, { settingsMode: 'retryable' })
    await page.goto('/settings')

    await expect(page.getByText('Temporary request failure')).toBeVisible({ timeout: 12_000 })
    api.recoverSettings()
    await page.getByRole('button', { name: 'Try Again' }).click()
    await expect(page.getByText('Balanced')).toBeVisible()
  })

  test('evaluation preserves repository/index facts, stays unavailable, and passes accessibility', async ({ page }) => {
    await installUi005Api(page)
    await page.goto('/repositories/repo-ui005/evaluation')

    await expect(page.getByRole('heading', { name: 'Evaluation', exact: true })).toBeVisible()
    await expect(page.getByText('UI-005 Truthful Workspace').first()).toBeVisible()
    await expect(page.getByText('Active index: 31')).toBeVisible()
    await expect(page.getByText('42 of 48')).toBeVisible()
    await expect(page.getByText('Capability unavailable')).toBeVisible()
    await expect(page.getByText('POST /evaluation/runs')).toBeVisible()
    await expect(page.getByText('Where is login implemented?')).toHaveCount(0)
    await expectKeyboardTarget(page)
    await expectNoSeriousAccessibilityViolations(page)
  })
})

async function expectKeyboardTarget(page: Page) {
  await page.keyboard.press('Tab')
  const activeTag = await page.evaluate(() => document.activeElement?.tagName ?? 'BODY')
  expect(activeTag).toMatch(/A|BUTTON/)
}

async function expectNoSeriousAccessibilityViolations(page: Page) {
  const result = await new AxeBuilder({ page })
    .include('main')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const blocking = result.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
  expect(blocking, blocking.map((violation) => `${violation.id}: ${violation.help}`).join('\n')).toEqual([])
}
