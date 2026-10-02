/** Support diagnostics accept scalars from explicit allowlists, never application payloads. */
export const subsystems = ['application', 'sync', 'encryption', 'projects', 'stages', 'documents', 'migrations', 'game', 'developer'] as const
export type Subsystem = typeof subsystems[number]
export const operations = ['runtime_start', 'sync_cycle', 'retry', 'metadata_migration', 'stage_migration', 'catalog_migration', 'conflict_resolution', 'project_connect', 'project_import', 'unlock', 'create', 'update', 'reorder', 'load', 'save', 'documents_sync', 'restore_streak', 'create_streak', 'copy', 'export', 'clear'] as const
export type Operation = typeof operations[number]
export const eventCodes = ['requested', 'started', 'succeeded', 'failed', 'cancelled', 'sync_result', 'blocker', 'native_validation', 'native_attempt', 'native_succeeded', 'native_failed', 'pull_result', 'upload_result', 'apply_result', 'ack_result'] as const
export type EventCode = typeof eventCodes[number]
export const safeCodes = ['applied','folder','folder_order','folder_membership','project_order','invalid_catalog_frame','catalog_dependency_missing','catalog_parent_unknown','catalog_membership_changed','catalog_project_unproven','catalog_folder_has_members','catalog_resource_limit','catalog_dependency_conflict','catalog_conflict','stale_catalog_resolution','unsupported_catalog_source','catalog_disconnect_requires_reconciliation','account_entity_codec_not_activated', 'account_scope_rejected', 'decrypt_failed', 'unknown_error', 'Validation', 'NotFound', 'Database', 'PrerequisiteMissing', 'InvalidState', 'ApiError', 'TypeError', 'Error', 'KeyNotProvisionedError', 'StaleAuthContextError', 'ApiResponseTooLargeError', 'streak_restore_no_history', 'diagnostic_storage_unavailable', 'metadata_import_resource_limit', 'metadata_import_remaining_work', 'invalid_stage_frame', 'structural_authentication_failed', 'structural_scope_mismatch', 'stage_dependency_missing', 'stage_membership_head_changed', 'stage_order_membership_mismatch', 'stage_order_foreign_stage', 'stage_tombstone_child_manifest_incomplete', 'stale_structural_resolution', 'project_metadata_authority_unresolved', 'unresolved_structural_conflict', 'stage_dependency_proof_limit', 'structural_local_lineage_limit', 'metadata_scope_mismatch', 'unsupported_stage_source', 'blocked', 'orphan', 'conflict_preserved', 'active', 'conflict', 'publication_pending', 'published_self_echo_pending', 'candidate_captured', 'structural_local', 'resolution_pending', 'ready', 'completed', 'remaining_work', 'retryable_error', 'logged_out', 'key_locked', 'global', 'project', 'stage', 'no_progress', 'advanced', 'already_acknowledged', 'already_advanced', 'stale', 'CloudProjectBootstrapBlockedError', 'AccountCryptoAlreadyProvisionedError', 'AccountCryptoProvisioningConflictError', 'RecoveryKeyConfirmationRequiredError', 'AccountCryptoProvisioningDisposedError', 'metadata_import_continuation_required', 'dependency_not_synced', 'unsupported_content_format', 'invalid_note_payload', 'missing_created_at', 'invalid_created_at', 'missing_updated_at', 'invalid_updated_at', 'remote_project_not_active', 'bootstrap_operation_in_progress', 'local_project_lineage_not_found', 'missing_local_binding', 'missing_remote_registration', 'lineage_conflict', 'local_device_conflict', 'binding_not_ready', 'initializing', 'legacy', 'paused'] as const
export type SafeCode = typeof safeCodes[number]
export interface DiagnosticEvent {
  schema_version: 1; timestamp: string; severity: 'debug' | 'info' | 'warning' | 'error'
  subsystem: Subsystem; operation: Operation; code: EventCode; correlation_id: string
  context: Record<string, number | boolean | SafeCode>
}
const numeric = new Set(['count', 'applied', 'conflicts', 'orphans', 'pending', 'duration_ms', 'http_status'])
const codes = new Set<string>(safeCodes)
export function sanitizeContext(value: unknown): DiagnosticEvent['context'] {
  const result: DiagnosticEvent['context'] = {}
  if (!value || typeof value !== 'object' || Array.isArray(value)) return result
  for (const [key, item] of Object.entries(value)) {
    if (numeric.has(key) && typeof item === 'number' && Number.isSafeInteger(item) && item >= 0 && item <= 1_000_000_000) result[key] = item
    if (['retry', 'supported'].includes(key) && typeof item === 'boolean') result[key] = item
    if (['status', 'error_code', 'error_class', 'target_type'].includes(key) && typeof item === 'string' && codes.has(item)) result[key] = item as SafeCode
  }
  return result
}
export function safeError(error: unknown): DiagnosticEvent['context'] {
  // Never copy messages, stacks, HTTP details or arbitrary error objects.
  const value = error && typeof error === 'object' ? error as { code?: unknown; name?: unknown } : {}
  const machineCode = typeof value.code === 'string' && codes.has(value.code) ? value.code
    : error instanceof Error && ['metadata_import_resource_limit', 'metadata_import_continuation_required'].includes(error.message) ? error.message : 'unknown_error'
  return sanitizeContext({ error_code: machineCode,
    error_class: error instanceof Error && codes.has(error.name) ? error.name : 'Error' })
}
export function correlationId(): string { return crypto.randomUUID() }
