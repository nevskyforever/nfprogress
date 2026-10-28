// Test setup only: real shared-codec producers and real authenticated API writes.
// Reader requests are recorded separately, after setup, and must all be GETs.
export async function seedMetadataAccount(page, username, variant = 'ordinary', sourceDevice = null) {
  return page.evaluate(async ({ username, variant, sourceDevice }) => {
    const cryptoApi = await import('/src/crypto/index.ts'), { encodeBase64Url } = await import('/src/api/base64url.ts')
    const { accountCryptoApi } = await import('/src/api/accountCrypto.ts'), { sealProjectMetadataEvent } = await import('/src/cloud/projectMetadataCodec.ts')
    const { sealCatalogEvent } = await import('/src/cloud/accountCatalogCodec.ts')
    const base = (await (await fetch('/src/cloud/__fixtures__/projectMetadataV2.json')).json())[0].event
    const folder = await (await fetch('/src/cloud/__fixtures__/accountCatalogV1.json')).json()
    const login = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password: 'correct horse battery staple' }) })
    if (!login.ok) throw Error('fixture_login')
    const token = (await login.json()).access_token, headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const api = async (path, method = 'POST', body) => {
      const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
      if (!response.ok) throw Error(`fixture_${path}_${response.status}_${await response.text()}`)
      return response.status === 204 ? undefined : response.json()
    }
    const me = await api('/api/v1/account/me', 'GET'), amk = await cryptoApi.generateAccountMasterKey(), recoveryKey = await cryptoApi.generateRecoveryKey()
    try {
      const password = await cryptoApi.wrapAmkWithPassphrase(amk, 'encryption-password'), recovery = await cryptoApi.wrapAmkWithRecoveryKey(amk, recoveryKey)
      await accountCryptoApi.provision(token, { password: { ...password, kdf: { ...password.kdf, salt: encodeBase64Url(password.kdf.salt) }, nonce: encodeBase64Url(password.nonce), ciphertext: encodeBase64Url(password.ciphertext) },
        recovery: { ...recovery, nonce: encodeBase64Url(recovery.nonce), ciphertext: encodeBase64Url(recovery.ciphertext) } })
      const source = sourceDevice ?? crypto.randomUUID(), projects = ['project', 'second-project'].map(project_id => ({ project_id, bootstrap_id: crypto.randomUUID() }))
      await api(`/api/v1/sync/devices/${source}`, 'PUT')
      await api('/api/v2/sync/encrypted/cutover', 'POST', { expected_cutover_epoch: 0 })
      await api('/api/v3/sync/encrypted/reader-ready', 'POST', { device_id: source, reader_transport_version: 3 })
      await api('/api/v3/sync/encrypted/cutover', 'POST', { expected_cutover_epoch: 1 })
      for (const project of projects) {
        await api(`/api/v1/cloud/projects/${project.project_id}/bootstrap`, 'POST', { bootstrap_id: project.bootstrap_id, device_id: source })
        await api(`/api/v1/cloud/projects/${project.project_id}/bootstrap/complete`, 'POST', { bootstrap_id: project.bootstrap_id, device_id: source, initial_event_count: 0, initial_max_server_sequence: 0 })
      }
      let batch = [], total = variant === 'ordinary' ? 102 : ['missing', 'generation', 'delete', 'conflict'].includes(variant) ? 3 : variant === 'mixed' ? 2 : 1
      const flush = async () => { if (batch.length) { await api('/api/v3/sync/encrypted/push', 'POST', { protocol_version: 3, encrypted_sync_version: 3, device_id: source, items: batch }); batch = [] } }
      const heads = new Map(), initial = new Map()
      for (let index = 0; index < total; index++) {
        const account = variant === 'mixed' && index === 0, event = structuredClone(account ? folder : base)
        const project = projects[variant === 'ordinary' ? index % 2 : 0], parent = heads.get(project.project_id)
        event.header = { ...event.header, account_id: me.id, device_id: source, event_id: crypto.randomUUID() }
        if (account) event.payload.name = 'PRIVATE_METADATA_FOLDER'
        else {
          Object.assign(event.header, { project_id: project.project_id, entity_id: project.project_id, bootstrap_id: project.bootstrap_id,
            operation: parent ? 'update' : 'create', revision: parent ? parent.revision + 1 : 1, generation: parent ? parent.revision + 1 : 1,
            parent_event_ids: parent ? [parent.event_id] : [] })
          event.metadata.name = `PRIVATE_METADATA_SERVER_${username}_${index}`
          if (variant === 'bootstrap') event.header.bootstrap_id = crypto.randomUUID()
          if (variant === 'account') event.header.account_id = crypto.randomUUID()
          if (variant === 'device') event.header.device_id = crypto.randomUUID()
          if (index === 1 && variant === 'missing') event.header.parent_event_ids = [crypto.randomUUID()]
          if (index === 1 && variant === 'generation') event.header.generation = 1
          if (index === 2 && variant === 'conflict') { event.header.parent_event_ids = [initial.get(project.project_id)]; event.header.revision = 2 }
          if (index === 1 && variant === 'delete') { event.header.operation = 'delete'; event.deleted_at = event.header.updated_at; event.metadata = null }
          if (variant === 'cover') event.version = 2
          if (variant === 'cover') event.metadata.cover_reference = { version: 1, blob_id: crypto.randomUUID(), crypto_version: 1, aad_version: 1, mime_type: 'image/jpeg', plaintext_size: 4, key_fingerprint: '0'.repeat(64), envelope_sha256: '1'.repeat(64) }
          heads.set(project.project_id, event.header); if (!parent) initial.set(project.project_id, event.header.event_id)
        }
        const sealed = await (account ? sealCatalogEvent(amk, event) : sealProjectMetadataEvent(amk, event)), h = event.header
        if (variant === 'corrupt') sealed.ciphertext[0] ^= 1
        const item = { event: { event_id: h.event_id, ...(account ? { canonical_user_id: me.id, scope: 'account' } : { project_id: h.project_id }), entity_id: h.entity_id,
          entity_type: account ? 'folder' : 'project_metadata', operation: h.operation === 'delete' ? 'delete' : 'upsert', revision: variant === 'descriptor' ? 2 : h.revision, updated_at: h.updated_at, deleted_at: event.deleted_at },
        object: { ...sealed, nonce: encodeBase64Url(sealed.nonce), ciphertext: encodeBase64Url(sealed.ciphertext) } }
        if (account) { await flush(); await api('/api/v3/sync/encrypted/account/push', 'POST', { protocol_version: 3, encrypted_sync_version: 3, device_id: source, items: [item] }) }
        else { batch.push(item); if (batch.length === 100) await flush() }
      }
      await flush()
      const expectedWire = await api(`/api/v3/sync/encrypted/pull?device_id=${source}&since=0&limit=200&protocol_version=3&encrypted_sync_version=3`, 'GET')
      return { source, total, canonicalUserId: me.id, expectedWire: expectedWire.items }
    } finally { amk.fill(0); recoveryKey.fill(0) }
  }, { username, variant, sourceDevice })
}
