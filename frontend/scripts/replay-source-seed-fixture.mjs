/** Genuine browser crypto producers and isolated FastAPI/PostgreSQL account. */
export async function seedSourceAccount(page, username, options = {}) {
  return page.evaluate(async ({ username, options }) => {
    const cryptoApi = await import('/src/crypto/index.ts'), { encodeBase64Url } = await import('/src/api/base64url.ts')
    const { accountCryptoApi } = await import('/src/api/accountCrypto.ts')
    const { sealProjectMetadataEvent } = await import('/src/cloud/projectMetadataCodec.ts')
    const { sealNoteSyncEvent } = await import('/src/cloud/encryptedSyncProtocol.ts')
    const { sealStructuralEvent } = await import('/src/cloud/stageCodec.ts')
    const metadata = (await (await fetch('/src/cloud/__fixtures__/projectMetadataV2.json')).json())[0].event
    const note = (await (await fetch('/src/cloud/__fixtures__/noteSyncPlaintextV1.json')).json()).plaintext.note
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
      for (const project of projects) await api(`/api/v1/cloud/projects/${project.project_id}/bootstrap`, 'POST', { bootstrap_id: project.bootstrap_id, device_id: source })
      const encoded = sealed => ({ ...sealed, nonce: encodeBase64Url(sealed.nonce), ciphertext: encodeBase64Url(sealed.ciphertext) })
      const firstNotes = []
      for (let index = 0; index < (options.secondProjectNote ? 3 : 2); index++) {
        const project = index === 2 ? projects[1] : projects[0]
        const id = `initial-${index}`, event = { event_id: crypto.randomUUID(), project_id: project.project_id, entity_id: id,
          entity_type: 'note', operation: 'upsert', revision: 1, updated_at: note.updated_at, deleted_at: null }
        const sealed = await sealNoteSyncEvent(amk, me.id, event, null, { ...note, id, project_id: project.project_id,
          title: `PRIVATE_SEED_NOTE_${index}`, content: `PRIVATE_SEED_CONTENT_${index}`, metadata: {} })
        firstNotes.push({ event: sealed.event, object: encoded(sealed.object) })
      }
      const accepted = await api('/api/v3/sync/encrypted/push', 'POST', { protocol_version: 3, encrypted_sync_version: 3, device_id: source, items: firstNotes })
      await api(`/api/v1/cloud/projects/${projects[0].project_id}/bootstrap/complete`, 'POST', { bootstrap_id: projects[0].bootstrap_id, device_id: source, initial_event_count: 2, initial_max_server_sequence: accepted.results[1].server_sequence })
      await api(`/api/v1/cloud/projects/${projects[1].project_id}/bootstrap/complete`, 'POST', { bootstrap_id: projects[1].bootstrap_id, device_id: source,
        initial_event_count: options.secondProjectNote ? 1 : 0, initial_max_server_sequence: options.secondProjectNote ? accepted.results[2].server_sequence : 0 })
      const items = [], heads = new Map()
      for (let index = 0; index < (options.metadataCount ?? 102); index++) {
        const project = projects[index % 2], previous = heads.get(project.project_id), event = structuredClone(metadata)
        Object.assign(event.header, { account_id: me.id, project_id: project.project_id, entity_id: project.project_id,
          bootstrap_id: project.bootstrap_id, device_id: source, event_id: crypto.randomUUID(), operation: previous ? 'update' : 'create',
          revision: previous ? previous.revision + 1 : 1, generation: previous ? previous.generation + 1 : 1,
          parent_event_ids: previous ? [previous.event_id] : [] })
        event.metadata.name = previous ? `PRIVATE_SEED_METADATA_${index}` : `PRIVATE_SEED_PROJECT_${project.project_id}`
        event.metadata.status = 'активен'
        if (options.stage) event.metadata.stages_enabled = true
        const sealed = await sealProjectMetadataEvent(amk, event), h = event.header
        items.push({ event: { event_id: h.event_id, project_id: h.project_id, entity_id: h.entity_id, entity_type: 'project_metadata',
          operation: 'upsert', revision: h.revision, updated_at: h.updated_at, deleted_at: null }, object: encoded(sealed) })
        heads.set(project.project_id, h)
      }
      for (let i = 0; i < items.length; i += 100) await api('/api/v3/sync/encrypted/push', 'POST', { protocol_version: 3,
        encrypted_sync_version: 3, device_id: source, items: items.slice(i, i + 100) })
      if (options.stage) {
        const stage = structuredClone((await (await fetch('/src/cloud/__fixtures__/stageCodecV1.json')).json()).event)
        const project = projects[0]
        Object.assign(stage.header, { account_id: me.id, project_id: project.project_id, bootstrap_id: project.bootstrap_id,
          device_id: source, entity_id: 'first-stage', event_id: crypto.randomUUID(), metadata_event_id: heads.get(project.project_id).event_id,
          operation: 'create', revision: 1, generation: 1, parent_event_ids: [] })
        stage.stage.name = 'PRIVATE_SEED_STAGE'
        const sealed = await sealStructuralEvent(amk, stage)
        await api('/api/v3/sync/encrypted/push', 'POST', { protocol_version: 3, encrypted_sync_version: 3, device_id: source,
          items: [{ event: { event_id: stage.header.event_id, project_id: project.project_id, entity_id: stage.header.entity_id,
            entity_type: 'stage', operation: 'upsert', revision: 1, updated_at: stage.header.updated_at, deleted_at: null }, object: encoded(sealed) }] })
        if (options.stageOrder) {
          const order = { version: 1, header: { account_id: me.id, project_id: project.project_id, bootstrap_id: project.bootstrap_id,
            device_id: source, entity_type: 'stage_order', entity_id: 'stage_order', event_id: crypto.randomUUID(),
            metadata_event_id: heads.get(project.project_id).event_id, updated_at: stage.header.updated_at,
            operation: 'create', revision: 1, generation: 1, parent_event_ids: [] }, stage: null,
          stage_ids: ['first-stage'], stage_heads: { 'first-stage': [stage.header.event_id] }, deleted_at: null }
          const envelope = await sealStructuralEvent(amk, order)
          await api('/api/v3/sync/encrypted/push', 'POST', { protocol_version: 3, encrypted_sync_version: 3, device_id: source,
            items: [{ event: { event_id: order.header.event_id, project_id: project.project_id, entity_id: order.header.entity_id,
              entity_type: 'stage_order', operation: 'upsert', revision: 1, updated_at: order.header.updated_at, deleted_at: null }, object: encoded(envelope) }] })
        }
      }
      return { projects, source, count: firstNotes.length + items.length + (options.stage ? 1 : 0) + (options.stageOrder ? 1 : 0),
        firstNoteIds: firstNotes.map(item => item.event.entity_id) }
    } finally { amk.fill(0); recoveryKey.fill(0) }
  }, { username, options })
}
