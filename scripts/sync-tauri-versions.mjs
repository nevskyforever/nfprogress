#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const enginePath = path.join(root, 'engine.py')
const defaultFrontend = path.join(root, 'frontend')
const versionPattern = /^(\d+)(?:\.(\d+))?(?:\.(\d+))?([+-][0-9A-Za-z.-]+)?$/

function canonicalVersion(raw) {
  const match = versionPattern.exec(raw.trim().replace(/^v/, ''))
  if (!match) throw new Error(`Unsupported semantic version: ${raw}`)
  return `${match[1]}.${match[2] ?? '0'}.${match[3] ?? '0'}${match[4] ?? ''}`
}

function engineVersion() {
  const match = /^version\s*=\s*['"]([^'"]+)['"]/m.exec(
    fs.readFileSync(enginePath, 'utf8'),
  )
  if (!match) throw new Error(`Could not find version in ${enginePath}`)
  return canonicalVersion(match[1])
}

function synchronize(version, frontend) {
  const tauri = path.join(frontend, 'src-tauri')
  const configPath = path.join(tauri, 'tauri.conf.json')
  const cargoPath = path.join(tauri, 'Cargo.toml')
  const lockPath = path.join(tauri, 'Cargo.lock')
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
  config.version = version
  fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`)
  let cargo = fs.readFileSync(cargoPath, 'utf8')
  if (!/^version\s*=\s*"[^"]+"$/m.test(cargo)) {
    throw new Error(`Could not find package version in ${cargoPath}`)
  }
  const cargoResult = cargo.replace(/^(version\s*=\s*)"[^"]+"$/m, `$1"${version}"`)
  fs.writeFileSync(cargoPath, cargoResult)
  let lock = fs.readFileSync(lockPath, 'utf8')
  if (!/\[\[package\]\]\s+name = "nfprogress-desktop"\s+version = "[^"]+"/ms.test(lock)) {
    throw new Error(`Could not find desktop package in ${lockPath}`)
  }
  const lockResult = lock.replace(
    /(\[\[package\]\]\s+name = "nfprogress-desktop"\s+version = )"[^"]+"/ms,
    `$1"${version}"`,
  )
  fs.writeFileSync(lockPath, lockResult)
}

const version = engineVersion()
const versionOnly = process.argv.includes('--version-only')
const frontendArgumentIndex = process.argv.indexOf('--frontend-dir')
const frontend = frontendArgumentIndex >= 0
  ? path.resolve(process.argv[frontendArgumentIndex + 1])
  : defaultFrontend

if (!versionOnly) {
  synchronize(version, frontend)
  console.log(`Synchronized Tauri files to ${version}.`)
}
console.log(version)
