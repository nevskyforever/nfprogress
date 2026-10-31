// Genuine producer setup against the isolated server. Reader phase never runs these writes.
export async function seedStructuralAccount(page, username, variant = 'ordinary') {
  return page.evaluate(async ({ username, variant }) => {
    const cryptoApi = await import('/src/crypto/index.ts'), { encodeBase64Url } = await import('/src/api/base64url.ts')
    const { accountCryptoApi } = await import('/src/api/accountCrypto.ts'), { sealProjectMetadataEvent } = await import('/src/cloud/projectMetadataCodec.ts')
    const { sealStructuralEvent, frameStructuralEvent } = await import('/src/cloud/stageCodec.ts')
    const metadata = (await (await fetch('/src/cloud/__fixtures__/projectMetadataV2.json')).json())[0].event
    const stage = (await (await fetch('/src/cloud/__fixtures__/stageCodecV1.json')).json()).event
    const login = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password: 'correct horse battery staple' }) })
    if (!login.ok) throw Error('fixture_login')
    const token = (await login.json()).access_token, headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const api = async (path, method = 'POST', body) => {
      const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
      if (!response.ok) throw Error(`fixture_${path}_${response.status}`)
      return response.status === 204 ? undefined : response.json()
    }
    const me = await api('/api/v1/account/me', 'GET'), amk = await cryptoApi.generateAccountMasterKey(), recoveryKey = await cryptoApi.generateRecoveryKey()
    try {
      const password = await cryptoApi.wrapAmkWithPassphrase(amk, 'encryption-password'), recovery = await cryptoApi.wrapAmkWithRecoveryKey(amk, recoveryKey)
      await accountCryptoApi.provision(token, { password: { ...password, kdf: { ...password.kdf, salt: encodeBase64Url(password.kdf.salt) }, nonce: encodeBase64Url(password.nonce), ciphertext: encodeBase64Url(password.ciphertext) },
        recovery: { ...recovery, nonce: encodeBase64Url(recovery.nonce), ciphertext: encodeBase64Url(recovery.ciphertext) } })
      const source = crypto.randomUUID(), projects = ['project', 'second-project'].map(project_id => ({ project_id, bootstrap_id: crypto.randomUUID() }))
      await api(`/api/v1/sync/devices/${source}`, 'PUT')
      await api('/api/v2/sync/encrypted/cutover', 'POST', { expected_cutover_epoch: 0 })
      await api('/api/v3/sync/encrypted/reader-ready', 'POST', { device_id: source, reader_transport_version: 3 })
      await api('/api/v3/sync/encrypted/cutover', 'POST', { expected_cutover_epoch: 1 })
      for (const project of projects) {
        await api(`/api/v1/cloud/projects/${project.project_id}/bootstrap`, 'POST', { bootstrap_id: project.bootstrap_id, device_id: source })
        await api(`/api/v1/cloud/projects/${project.project_id}/bootstrap/complete`, 'POST', { bootstrap_id: project.bootstrap_id, device_id: source, initial_event_count: 0, initial_max_server_sequence: 0 })
      }
      const items = [], metadataHeads = new Map()
      const push = async event => {
        const h = event.header, structural = h.entity_type === 'stage' || h.entity_type === 'stage_order'
        let envelope
        if (variant === 'version' && structural && h.entity_type === 'stage' && h.entity_id === 'a' && h.revision === 1) {
          const frame = frameStructuralEvent(event); frame[10] = 99
          try { envelope = await cryptoApi.encryptObjectBytes(amk, { userId: h.account_id, projectId: h.project_id, entityId: h.entity_id, entityType: h.entity_type }, frame) }
          finally { frame.fill(0) }
        } else envelope = await (structural ? sealStructuralEvent(amk, event) : sealProjectMetadataEvent(amk, event))
        if (variant === 'corrupt' && structural && h.entity_type === 'stage' && h.revision === 1 && h.entity_id === 'a') envelope.ciphertext[0] ^= 1
        items.push({ event: { event_id: h.event_id, project_id: h.project_id, entity_id: h.entity_id, entity_type: structural ? h.entity_type : 'project_metadata',
          operation: h.operation === 'delete' ? 'delete' : 'upsert', revision: h.revision, updated_at: h.updated_at, deleted_at: event.deleted_at },
        object: { ...envelope, nonce: encodeBase64Url(envelope.nonce), ciphertext: encodeBase64Url(envelope.ciphertext) } })
      }
      for (const project of variant === 'ordinary' ? projects : [projects[0]]) {
        const meta = structuredClone(metadata)
        Object.assign(meta.header, { account_id: me.id, project_id: project.project_id, entity_id: project.project_id, bootstrap_id: project.bootstrap_id, device_id: source, event_id: crypto.randomUUID() })
        meta.metadata.name = 'PRIVATE_STRUCTURAL_PROJECT'; meta.metadata.stages_enabled = true
        await push(meta); metadataHeads.set(project.project_id, meta.header)
        if (variant === 'late_metadata_dependency') {
          const later = structuredClone(meta)
          Object.assign(later.header, { event_id: crypto.randomUUID(), operation: 'update', revision: 2,
            generation: 2, parent_event_ids: [meta.header.event_id] })
          const dependent = structuredClone(stage)
          Object.assign(dependent.header, { account_id: me.id, project_id: project.project_id,
            entity_id: 'a', bootstrap_id: project.bootstrap_id, device_id: source,
            event_id: crypto.randomUUID(), metadata_event_id: later.header.event_id,
            operation: 'create', revision: 1, generation: 1, parent_event_ids: [] })
          await push(dependent)
          await push(later)
          continue
        }
        const heads = {}, creates = {}
        for (const id of ['a', 'b', 'a']) {
          const event = structuredClone(stage), old = heads[id]
          Object.assign(event.header, { account_id: me.id, project_id: project.project_id, bootstrap_id: project.bootstrap_id, device_id: source, entity_id: id, event_id: crypto.randomUUID(),
            metadata_event_id: meta.header.event_id, operation: old ? 'update' : 'create', revision: old ? 2 : 1, generation: old ? 2 : 1, parent_event_ids: old ? [old] : [] })
          event.stage.name = `PRIVATE_STRUCTURAL_STAGE_${id}${old ? '_EDITED' : ''}`
          if (id === 'a' && !old) {
            if (variant === 'bootstrap') event.header.bootstrap_id = crypto.randomUUID()
            if (variant === 'account') event.header.account_id = crypto.randomUUID()
            if (variant === 'device') event.header.device_id = crypto.randomUUID()
            if (variant === 'metadata') event.header.metadata_event_id = crypto.randomUUID()
          }
          if (old && variant === 'parent') event.header.parent_event_ids = [crypto.randomUUID()]
          if (old && variant === 'fork') { event.header.operation = 'create'; event.header.revision = event.header.generation = 1; event.header.parent_event_ids = [] }
          if (old && variant === 'delete') { event.header.operation = 'delete'; event.stage = null; event.deleted_at = event.header.updated_at }
          await push(event); heads[id] = event.header.event_id; if (!old) creates[id] = event.header.event_id
        }
        let parent = null
        for (const revision of [1, 2]) {
          const event = { version: 1, header: { account_id: me.id, project_id: project.project_id, bootstrap_id: project.bootstrap_id, device_id: source,
            entity_type: 'stage_order', entity_id: 'stage_order', event_id: crypto.randomUUID(), metadata_event_id: meta.header.event_id, updated_at: meta.header.updated_at,
            operation: parent ? 'update' : 'create', revision, generation: revision, parent_event_ids: parent ? [parent] : [] }, stage: null,
          stage_ids: revision === 1 ? ['a', 'b'] : ['b', 'a'], stage_heads: { a: [heads.a], b: [heads.b] }, deleted_at: null }
          if (variant === 'unknown') { event.stage_ids.push('unknown'); event.stage_heads.unknown = [crypto.randomUUID()] }
          if (variant === 'omit') { event.stage_ids = ['a']; delete event.stage_heads.b }
          if (variant === 'head') event.stage_heads.a = [crypto.randomUUID()]
          if (variant === 'order_parent' && parent) event.header.parent_event_ids = [creates.a]
          await push(event); parent = event.header.event_id
        }
        if (variant === 'late_stage') {
          const late = structuredClone(stage)
          Object.assign(late.header, { account_id: me.id, project_id: project.project_id, bootstrap_id: project.bootstrap_id, device_id: source,
            entity_id: 'c', event_id: crypto.randomUUID(), metadata_event_id: meta.header.event_id, operation: 'create', revision: 1, generation: 1, parent_event_ids: [] })
          await push(late)
        }
      }
      // Interleave real Metadata updates after Structural owners: metadata_cursor must stay 1.
      if (variant === 'ordinary') for (let i = 0; i < 90; i++) {
        const project = projects[i % 2], old = metadataHeads.get(project.project_id), event = structuredClone(metadata)
        event.header = { ...old, event_id: crypto.randomUUID(), operation: 'update', revision: old.revision + 1, generation: old.generation + 1, parent_event_ids: [old.event_id] }
        event.metadata.name = `PRIVATE_STRUCTURAL_METADATA_${i}`; event.metadata.stages_enabled = true
        await push(event); metadataHeads.set(project.project_id, event.header)
      }
      for (let i = 0; i < items.length; i += 100) await api('/api/v3/sync/encrypted/push', 'POST', { protocol_version: 3, encrypted_sync_version: 3, device_id: source, items: items.slice(i, i + 100) })
      const wire = await api(`/api/v3/sync/encrypted/pull?device_id=${source}&since=0&limit=200&protocol_version=3&encrypted_sync_version=3`, 'GET')
      return { wire: wire.items, total: items.length }
    } finally { amk.fill(0); recoveryKey.fill(0) }
  }, { username, variant })
}
