import { execFileSync } from 'node:child_process'
import { mkdtemp, writeFile, rm } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Frozen real slice-1 receiver/storage. Its native IDB version check is the old-client proof.
export async function replayV1Fixture() {
  const root = dirname(fileURLToPath(import.meta.url)), directory = await mkdtemp(join(root, 'replay-v1-fixture-'))
  try {
    for (const name of ['replayRecords.ts', 'replayStorage.ts']) {
      const original = execFileSync('git', ['show', 'bdfb5601d2d4b512fc76e424c5b0db1ae87dc67c:frontend/src/platform/web/' + name], { cwd: root, encoding: 'utf8' })
      const source = original.replace(/from '\.\/([^']+)'/g, (match, module) => module === 'replayRecords' ? match : `from '../../src/platform/web/${module}'`)
      await writeFile(join(directory, name), source)
    }
    return { url: `/scripts/${directory.slice(root.length + 1)}/replayStorage.ts`, close: () => rm(directory, { recursive: true, force: true }) }
  } catch (error) { await rm(directory, { recursive: true, force: true }); throw error }
}
