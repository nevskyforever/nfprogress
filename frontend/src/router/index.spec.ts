import { describe, expect, it } from 'vitest'

import router from './index'

describe('application routes', () => {
  it('exposes every migrated top-level workspace', () => {
    const routeNames = new Set(router.getRoutes().map(({ name }) => name))

    for (const routeName of [
      'projects', 'maps', 'global-project-map', 'notes', 'global-project-notes',
      'game', 'integrations', 'help', 'settings',
    ]) {
      expect(routeNames.has(routeName)).toBe(true)
    }
  })
})
