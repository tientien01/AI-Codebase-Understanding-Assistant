import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { installUi004Api } from './fixtures'

const repositoryRoot = '/repositories/repo-ui004'

test.describe('UI-004 evidence-backed workspace', () => {
  test('architecture tour opens its justified source and passes accessibility', async ({ page }) => {
    await installUi004Api(page)
    await page.goto(`${repositoryRoot}/overview`)

    await expect(page.getByRole('heading', { name: 'Architecture Overview' })).toBeVisible()
    await page.getByRole('button', { name: 'Start Guided Tour' }).click()
    await expect(page.getByText('Step 1 of 2')).toBeVisible()
    await expect(page.locator('.tour-step-detail').getByText('Registers the application entrypoint and public boundaries.')).toBeVisible()
    await page.getByRole('button', { name: 'Open Source' }).click()

    await expect(page).toHaveURL(/\/code\?path=src%2Fmain\.ts$/)
    await expect(page.getByRole('heading', { name: 'Code Explorer' })).toBeVisible()
    await expect(page.getByText('return createApplication()')).toBeVisible()
    await expectNoSeriousAccessibilityViolations(page)
  })

  test('graph focus preserves every relation, supports reduced motion, and passes accessibility', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await installUi004Api(page, 12)
    await page.goto(`${repositoryRoot}/graph?view=api-flow`)

    const canvas = page.getByLabel('Graph nodes')
    await expect(page.getByRole('heading', { name: 'Graph Explorer' })).toBeVisible()
    await expect(canvas.getByRole('button')).toHaveCount(12)
    await expect(page.getByText('Accessible relation list (11)')).toBeVisible()

    await canvas.getByRole('button', { name: /Service 2/ }).click()
    const inspector = page.getByLabel('Selected graph entity')
    await expect(inspector.getByRole('heading', { name: 'Service 2' })).toBeVisible()
    await inspector.getByRole('tab', { name: 'relations' }).click()
    await expect(inspector.getByText(/Outgoing|Incoming/).first()).toBeVisible()

    const animationName = await page.locator('.graph-edge.active').first().evaluate((element) => getComputedStyle(element).animationName)
    const transitionDuration = await canvas.getByRole('button', { name: /Service 2/ }).evaluate((element) => getComputedStyle(element).transitionDuration)
    expect(animationName).toBe('none')
    expect(transitionDuration).toBe('0s')

    await expectNoSeriousAccessibilityViolations(page)
  })

  test('dependency graph starts adaptively and expands only the selected branch', async ({ page }) => {
    await installUi004Api(page)
    await page.goto(`${repositoryRoot}/graph?view=dependencies`)

    const canvas = page.getByLabel('Graph nodes')
    await expect(page.getByRole('heading', { name: 'Dependency Explorer' })).toBeVisible()
    await expect(canvas.getByRole('button')).toHaveCount(3)
    await expect(page.getByText('3 suggested starting points')).toBeVisible()
    await expect(page.getByText(/other qualified points available/)).toBeVisible()

    const seed = canvas.getByRole('button', { name: /Seed 0/ })
    const initialPosition = await seed.getAttribute('style')
    await seed.click()

    await expect(canvas.getByRole('button')).toHaveCount(4)
    await expect(canvas.getByRole('button', { name: /Resolved dependency/ })).toBeVisible()
    await expect(page.locator('.dependency-node.dimmed')).toHaveCount(2)
    expect(await seed.getAttribute('style')).toBe(initialPosition)
    await expect(page.getByText('Relations (1)')).toBeVisible()
    await expectNoSeriousAccessibilityViolations(page)
  })

  test('impact discloses direct, inferred, unknown and unavailable history', async ({ page }) => {
    await installUi004Api(page)
    await page.goto(`${repositoryRoot}/impact?target=node-2`)
    await page.getByRole('button', { name: 'Analyze Current Impact' }).click()

    await expect(page.getByText('Unavailable: the compatibility API does not expose version snapshots.')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Direct' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Inferred' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Unknown' })).toBeVisible()
    await expect(page.getByText('Dynamic provider dispatch is not resolved.')).toBeVisible()
    await expectNoSeriousAccessibilityViolations(page)
  })
})

for (const graphCase of [
  { name: 'Small', nodes: 12 },
  { name: 'Medium', nodes: 80 },
  { name: 'Large', nodes: 220 },
]) {
  test(`records ${graphCase.name} graph browser observation`, async ({ page }, testInfo) => {
    await installUi004Api(page, graphCase.nodes)
    const startedAt = performance.now()
    await page.goto(`${repositoryRoot}/graph?view=api-flow`)
    await expect(page.getByLabel('Graph nodes').getByRole('button')).toHaveCount(graphCase.nodes)
    await expect(page.locator('.graph-edge')).toHaveCount(Math.max(0, graphCase.nodes - 1))
    const readyMs = Math.round(performance.now() - startedAt)
    const browserMetrics = await page.evaluate(() => ({
      domNodes: document.getElementsByTagName('*').length,
      navigationMs: Math.round(performance.getEntriesByType('navigation')[0]?.duration ?? 0),
    }))
    const observation = `${graphCase.name}: ${graphCase.nodes} nodes/${Math.max(0, graphCase.nodes - 1)} edges, ready ${readyMs} ms, navigation ${browserMetrics.navigationMs} ms, DOM ${browserMetrics.domNodes}`
    testInfo.annotations.push({ type: 'graph-observation', description: observation })
    console.log(`[UI-004] ${observation}`)
  })
}

async function expectNoSeriousAccessibilityViolations(page: Page) {
  const result = await new AxeBuilder({ page })
    .include('main')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const blocking = result.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
  expect(blocking, blocking.map((violation) => `${violation.id}: ${violation.help}`).join('\n')).toEqual([])
}
