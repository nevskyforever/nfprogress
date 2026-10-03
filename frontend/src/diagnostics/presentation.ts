import type { CloudSessionStatus, CloudProjectUiStatus } from '@/stores/cloudSession'
import type { MetadataAuthorityView } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import type { StructuralView } from '@/infrastructure/sqlite/stageStructuralRepository'
export interface UserFacingStatus { title: string; description: string; action: string; severity: 'info' | 'warning' | 'error'; technicalCode: string }
const messages = {
  mapReaders: ['Обновите другие устройства', 'Для публикации карт все зарегистрированные устройства должны поддерживать синхронизацию карт.', 'Откройте обновлённое приложение на каждом устройстве и повторите синхронизацию.'],
  noteReaders: ['Обновите другие устройства', 'Для публикации заметок все подключённые устройства должны поддерживать новый формат заметок.', 'Откройте обновлённое приложение на каждом устройстве и повторите синхронизацию.'],
  local: ['Хранится на этом устройстве', 'Отправка в облако начнётся только после вашего подтверждения.', 'Подключите проект, когда будете готовы.'],
  waiting: ['Ожидает связанных данных', 'Некоторые данные проекта ещё не получены. Синхронизация продолжится после их получения.', 'Повторите синхронизацию позже.'],
  pending: ['Изменения ожидают подтверждения', 'Изменения сохранены. Дождитесь завершения отправки и проверки.', 'Безопасно продолжить'],
  active: ['Данные согласованы', 'На этом устройстве используется проверенная версия данных.', ''],
  different: ['Версии различаются', 'На устройстве и в облаке сохранены разные варианты. Выберите нужный.', 'Откройте варианты и выберите результат.'],
  conflict: ['Есть конфликт изменений', 'Проект был изменён на нескольких устройствах. Сохранённые варианты доступны для выбора.', 'Откройте варианты и выберите результат.'],
  stale: ['Во время выбора появились новые изменения', 'Получены новые изменения. Предыдущий выбор сохранён, но нужно учесть новые варианты.', 'Откройте конфликт ещё раз и выберите итоговый вариант.'],
  blocked: ['Требуется ваше внимание', 'Синхронизация приостановлена. Ваши данные сохранены.', 'Проверьте причину и повторите действие.'],
  format: ['Эти данные пока не поддерживаются', 'Приложение сохранило исходные данные, но пока не может их обработать.', 'Обновите приложение или отправьте журнал для проверки.'],
  limit: ['Не удалось обработать всю историю', 'Проверенная часть сохранена. Для продолжения нужна дополнительная проверка.', 'Экспортируйте журнал и обратитесь за помощью.'],
  deletion: ['Удаление требует проверки', 'Дочерние данные сохранены. Удаление этапа и исключение из порядка пока недоступны.', 'Сохраните данные и дождитесь поддержки безопасного удаления.'],
  locked: ['Введите пароль шифрования', 'Он нужен для доступа к зашифрованным данным на этом устройстве.', 'Разблокировать'],
  loggedOut: ['Войдите в аккаунт', 'После входа можно настроить облачную синхронизацию.', 'Войти'],
  encryption: ['Настройте защиту данных', 'Создайте пароль шифрования и сохраните ключ восстановления.', 'Настроить шифрование'],
  ready: ['Готово к синхронизации', 'Можно подключить проект или продолжить обмен изменениями.', 'Синхронизировать'],
  syncing: ['Синхронизация выполняется', 'Приложение отправляет и получает изменения.', ''],
  complete: ['Обмен изменениями завершён', 'Поддерживаемые данные обработаны. Полная синхронизация всех типов данных ещё разрабатывается.', ''],
  remaining: ['Есть ещё данные для обработки', 'Обработанная часть сохранена. Продолжите обмен оставшимися изменениями.', 'Безопасно продолжить'],
  paused: ['Синхронизация приостановлена', 'Локальные данные сохранены; обмен для этого проекта остановлен.', 'Возобновить'],
  unavailable: ['Доступно в настольном приложении', 'Откройте WORTA на компьютере для этой операции.', ''],
  restore: ['Не удалось восстановить серию', 'Изменение не завершено. Журнал поможет выяснить причину.', 'Скопируйте журнал из настроек диагностики.'],
  noHistory: ['Нет сохранённой длины серии', 'Восстановление требует сведений о предыдущей серии.', 'Проверьте выбранную серию или создайте тестовую серию.'],
  unknown: ['Не удалось завершить действие', 'Возникла ошибка. Данные не следует удалять; журнал поможет выяснить причину.', 'Повторите действие или отправьте журнал для проверки.'],
} as const
type Message = keyof typeof messages
const session = { unavailable: 'unavailable', logged_out: 'loggedOut', provisioning: 'encryption', key_locked: 'locked', ready: 'ready', syncing: 'syncing', completed: 'complete', retryable_error: 'unknown', blocked: 'blocked', remaining_work: 'remaining' } satisfies Record<CloudSessionStatus, Message>
const project = { local_only: 'local', unsupported: 'format', import_available: 'ready', registering: 'pending', preparing_initial_notes: 'pending', uploading_initial_notes: 'pending', completing_registration: 'pending', pulling_remote_notes: 'waiting', remaining_work: 'remaining', initial_sync_completed: 'complete', paused: 'paused', blocked: 'blocked' } satisfies Record<CloudProjectUiStatus, Message>
const metadata = { local_legacy_only: 'local', local_candidate_ready: 'local', local_matches_authenticated: 'active', local_differs_from_authenticated: 'different', genesis_conflict: 'conflict', metadata_conflict: 'conflict', resolution_pending: 'pending', active: 'active', blocked: 'blocked' } satisfies Record<MetadataAuthorityView['state'], Message>
const structure = { structural_local: 'local', candidate_captured: 'pending', publication_pending: 'pending', published_self_echo_pending: 'pending', active: 'active', conflict: 'conflict', blocked: 'blocked' } satisfies Record<StructuralView['state'], Message>
const errors: Record<string, Message> = {map_readers_not_ready:"mapReaders",map_reader_required:"mapReaders",map_conflict_requires_resolution:"conflict",map_combined_stale_heads:"stale",map_resolution_stale:"stale",map_import_stale:"stale",map_note_identity_collision:"blocked",map_note_link_invalid:"blocked",map_unsupported_extension:"format",map_resource_limit:"limit",invalid_map_payload:"format",content_note_parent_pending:'waiting',unresolved_note_conflict:'conflict',content_note_local_candidate:'conflict',note_resolution_missing_proof:'waiting',note_resolution_invalid:'format',content_note_readers_not_ready:'noteReaders',content_note_reader_required:'noteReaders',content_note_candidate_blocked:'format',stale_note_resolution:'stale',stale_content_note_frame:'stale', content_note_codec_unsupported:'format',content_note_map_owned:'format',content_note_unsupported_source:'format',content_note_scope_mismatch:'blocked',content_note_resource_limit:'limit', catalog_conflict:'conflict',stale_catalog_resolution:'stale',catalog_folder_has_members:'deletion',catalog_project_unproven:'waiting',catalog_membership_changed:'waiting',catalog_disconnect_requires_reconciliation:'blocked', account_entity_codec_not_activated: 'format', account_scope_rejected: 'blocked', decrypt_failed: 'blocked', orphan: 'waiting', conflict_preserved: 'conflict', stale_structural_resolution: 'stale', unresolved_structural_conflict: 'conflict', project_metadata_authority_unresolved: 'different', stage_dependency_missing: 'waiting', stage_membership_head_changed: 'waiting', stage_order_membership_mismatch: 'waiting', stage_order_foreign_stage: 'blocked', stage_tombstone_child_manifest_incomplete: 'deletion', unsupported_stage_source: 'format', invalid_stage_frame: 'format', metadata_import_resource_limit: 'limit', stage_dependency_proof_limit: 'limit', structural_local_lineage_limit: 'limit', metadata_import_remaining_work: 'remaining', structural_scope_mismatch: 'blocked', structural_authentication_failed: 'blocked', streak_restore_failed: 'restore', streak_restore_no_history: 'noHistory', diagnostic_storage_unavailable: 'unknown', dependency_not_synced: 'format', unsupported_content_format: 'format', invalid_note_payload: 'format', missing_created_at: 'format', invalid_created_at: 'format', missing_updated_at: 'format', invalid_updated_at: 'format', remote_project_not_active: 'waiting', bootstrap_operation_in_progress: 'pending', local_project_lineage_not_found: 'blocked', missing_local_binding: 'waiting', missing_remote_registration: 'blocked', lineage_conflict: 'different', local_device_conflict: 'blocked', binding_not_ready: 'waiting', initializing: 'pending', legacy: 'format', paused: 'paused', blocked: 'blocked' }
export function technicalCode(code: string): string {
  // Strip entity IDs/source suffixes and free-form text. Unknown stable codes
  // remain available here, never as primary titles or arbitrary JSON.
  const prefix = code.split(':', 1)[0] ?? ''
  return /^[a-zA-Z][a-zA-Z0-9_]{0,79}$/.test(prefix) ? prefix : 'unknown_error'
}
export function presentStatus(domain: 'session' | 'project' | 'metadata' | 'structure' | 'catalog' | 'error', code: string): UserFacingStatus {
  const tables: Record<string, Record<string, Message>> = { session, project, metadata, structure, catalog:{local:"local",catalog_local:"local",captured:"pending",publication_pending:"pending",self_echo_pending:"pending",waiting:"waiting",active:"active",conflict:"conflict",blocked:"blocked"}, error: errors }
  const safe = technicalCode(code)
  const key = tables[domain]?.[safe] ?? (/unsupported|invalid.*(frame|codec|format)/.test(safe) ? 'format' : /limit/.test(safe) ? 'limit' : /dependency|parent_unknown|head_unknown/.test(safe) ? 'waiting' : 'unknown')
  const [title, description, action] = messages[key]
  return { title, description, action, severity: ['unknown', 'restore', 'blocked'].includes(key) ? 'error' : ['conflict', 'stale', 'waiting', 'limit', 'deletion', 'format', 'different'].includes(key) ? 'warning' : 'info', technicalCode: safe }
}
