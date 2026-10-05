<script setup lang="ts">
import { computed, ref } from 'vue'
import FriendlyStatus from './FriendlyStatus.vue'
import DiagnosticDetails from './DiagnosticDetails.vue'
import { useCloudSessionStore } from '@/stores/cloudSession'
import { useLocaleStore } from '@/stores/locale'
import type { ProjectMetadata } from '@/cloud/projectMetadataCodec'
import type { MetadataDecisionKind } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'

const props = defineProps<{ projectId: string }>()
const cloud = useCloudSessionStore()
const t = useLocaleStore().translate
const view = computed(() => cloud.metadataAuthority[props.projectId])
const pending = ref(false)
const error = ref(false)
const draft = ref<ProjectMetadata | null>(null)
const coverPreviews=ref<Record<string,string>>({})
async function previewCover(eventId:string,metadata:ProjectMetadata){
 if(!metadata.cover_reference)return
 try{const image=await cloud.coverPreview(props.projectId,metadata.cover_reference);if(image)coverPreviews.value={...coverPreviews.value,[eventId]:image}}
 catch{error.value=true}
}

const fields: Array<{ key: keyof ProjectMetadata; label: string; kind: 'string' | 'number' | 'boolean' | 'nullable' }> = [
  { key: 'name', label: 'Название', kind: 'string' },
  { key: 'goal', label: 'Цель', kind: 'number' },
  { key: 'infinite', label: 'Бесконечный проект', kind: 'boolean' },
  { key: 'unit', label: 'Единица прогресса', kind: 'string' },
  { key: 'deadline', label: 'Дедлайн', kind: 'nullable' },
  { key: 'status', label: 'Статус', kind: 'string' },
  { key: 'personal_goal', label: 'Личная цель', kind: 'number' },
  { key: 'auto_freeze', label: 'Автозаморозка', kind: 'boolean' },
  { key: 'streak_enabled', label: 'Серия', kind: 'boolean' },
  { key: 'work_method', label: 'Метод работы', kind: 'string' },
  { key: 'stages_enabled', label: 'Этапы', kind: 'boolean' },
  { key: 'combine_stage_mindmaps', label: 'Объединение карт этапов', kind: 'boolean' },
]
async function action(operation: () => Promise<unknown>): Promise<void> {
  if (pending.value || cloud.busy) return
  pending.value = true; error.value = false
  try { await operation() } catch { error.value = true } finally { pending.value = false }
}
function inspect(): Promise<void> { return action(() => cloud.inspectProjectMetadata(props.projectId)) }
function adopt(): Promise<void> {
  const snapshot = view.value
  if (!snapshot?.head_event_id || !snapshot.local) return Promise.resolve()
  return action(() => cloud.adoptMetadata(props.projectId, snapshot.head_event_id!, snapshot.local!))
}
function decide(kind: MetadataDecisionKind, selected: string | null = null): Promise<void> {
  const snapshot = view.value
  if (!snapshot?.local) return Promise.resolve()
  return action(async () => {
    await cloud.decideMetadata(props.projectId, kind, selected, draft.value, snapshot.local!, snapshot.branches.map(branch => branch.event_id).sort())
    draft.value = null
  })
}
function edit(): void {
  const source = view.value?.authenticated ?? view.value?.local
  if (source) draft.value = { ...source }
}
function display(value: ProjectMetadata[keyof ProjectMetadata]): string {
  if (typeof value === 'boolean') return t(value ? 'Да' : 'Нет')
  if (value === null) return '—'
  const names: Record<string, string> = { manual: 'Вручную', sync: 'Синхронизация', app: 'В приложении', symbols: 'Символы', A4: 'Листы A4', author_list: 'Авторские листы', ficbook_pages: 'Страницы Ficbook' }
  return typeof value === 'string' && names[value] ? t(names[value]) : String(value)
}
function setField(key: keyof ProjectMetadata, kind: string, event: Event): void {
  if (!draft.value) return
  const input = event.target as HTMLInputElement
  const value = kind === 'boolean' ? input.checked : kind === 'number' ? (input.value === '' ? null : Number(input.value)) : kind === 'nullable' && input.value === '' ? null : input.value
  draft.value = { ...draft.value, [key]: value }
  if (key === 'infinite' && value === true) draft.value.goal = null
}
</script>

<template>
  <section class="metadata-authority" :data-metadata-state="view?.state" :aria-label="t('Настройки проекта в облаке')">
    <h4>{{ t('Настройки проекта в облаке') }}</h4>
    <button type="button" class="nf-button nf-button--secondary" :disabled="pending || cloud.busy" @click="inspect">{{ t('Проверить настройки') }}</button>
    <template v-if="view">
      <FriendlyStatus domain="metadata" :code="view.state" subsystem="migrations" />
      <div v-if="cloud.metadataTransportMode !== 3" class="metadata-actions">
        <p>{{ t('Для синхронизации настроек подтвердите поддержку на всех устройствах, затем включите её для аккаунта.') }}</p>
        <button class="nf-button nf-button--secondary" v-if="cloud.metadataTransportMode === 1" type="button" :disabled="pending || cloud.busy" @click="action(cloud.prepareMetadataTransport)">{{ t('Подготовить аккаунт к синхронизации настроек') }}</button>
        <button class="nf-button nf-button--secondary" v-if="cloud.metadataTransportMode === 2" type="button" :disabled="pending || cloud.busy" @click="action(cloud.declareMetadataReaderReady)">{{ t('Подтвердить поддержку устройства') }}</button>
        <button class="nf-button nf-button--secondary" v-if="cloud.metadataTransportMode === 2" type="button" :disabled="pending || cloud.busy" @click="action(async () => { await cloud.cutoverMetadataTransport(); await cloud.inspectProjectMetadata(projectId) })">{{ t('Включить синхронизацию настроек') }}</button>
      </div>
      <p v-if="view.local">{{ t('Локальная версия') }}</p>
      <dl v-if="view.local">
        <template v-for="field in fields" :key="field.key"><dt>{{ t(field.label) }}</dt><dd>{{ field.key === 'name' ? view.local[field.key] : display(view.local[field.key]) }}</dd></template>
      </dl>
      <div v-for="branch in view.branches" :key="branch.event_id" class="metadata-branch">
        <p>{{ t('Проверенная облачная версия') }}:  <span v-if="branch.local_candidate">({{ t('Локальная версия') }})</span></p>
        <DiagnosticDetails :code="view.state" subsystem="migrations" operation="conflict_resolution" />
        <dl><template v-for="field in fields" :key="field.key"><dt>{{ t(field.label) }}</dt><dd>{{ field.key === 'name' ? branch.metadata[field.key] : display(branch.metadata[field.key]) }}</dd></template></dl>
        <p v-if="branch.metadata.cover_reference===null">{{t('Версия без обложки')}}</p>
        <button v-if="branch.metadata.cover_reference" class="nf-button nf-button--secondary" type="button" @click="previewCover(branch.event_id,branch.metadata)">{{t('Показать обложку этой версии')}}</button>
        <img v-if="coverPreviews[branch.event_id]" :src="coverPreviews[branch.event_id]" :alt="t('Обложка')" style="max-width:100px;aspect-ratio:2/3;object-fit:contain" />
        <button class="nf-button nf-button--secondary" v-if="['genesis_conflict', 'metadata_conflict'].includes(view.state)" type="button" :disabled="pending || cloud.busy" @click="decide('choose_branch', branch.event_id)">{{ t('Выбрать этот вариант') }}</button>
      </div>
      <div v-if="cloud.metadataTransportMode === 3" class="metadata-actions">
        <template v-if="['local_legacy_only', 'local_candidate_ready'].includes(view.state)">
          <p>{{ t('Показанные настройки будут отправлены в облако после вашего подтверждения.') }}</p>
          <button class="nf-button nf-button--secondary" type="button" :disabled="pending || cloud.busy" @click="action(() => cloud.beginMetadataMigration(projectId))">{{ t('Отправить настройки этого устройства') }}</button>
        </template>
        <button class="nf-button nf-button--secondary" v-if="['local_matches_authenticated', 'local_differs_from_authenticated'].includes(view.state)" type="button" :disabled="pending || cloud.busy" @click="adopt">{{ t('Использовать облачную версию') }}</button>
        <button class="nf-button nf-button--secondary" v-if="view.state === 'local_differs_from_authenticated'" type="button" :disabled="pending || cloud.busy" @click="decide('keep_local')">{{ t('Использовать вариант этого устройства') }}</button>
        <button class="nf-button nf-button--secondary" v-if="['active', 'local_differs_from_authenticated', 'genesis_conflict', 'metadata_conflict'].includes(view.state)" type="button" :disabled="pending || cloud.busy" @click="edit">{{ t('Редактировать результат') }}</button>
        <button class="nf-button nf-button--secondary" v-if="view.state === 'resolution_pending'" type="button" :disabled="pending || cloud.busy" @click="action(async () => { await cloud.retry(); await cloud.inspectProjectMetadata(projectId) })">{{ t('Безопасно продолжить') }}</button>
      </div>
      <form v-if="draft" @submit.prevent="decide(view.branches.length > 1 ? 'resolve_manual' : view.state === 'active' ? 'edit' : 'manual')">
        <label v-for="field in fields" :key="field.key">{{ t(field.label) }}
          <select v-if="field.key === 'unit'" :value="draft.unit" @change="setField(field.key, field.kind, $event)">
            <option value="symbols">{{ t('Символы') }}</option><option value="A4">{{ t('Листы A4') }}</option>
            <option value="author_list">{{ t('Авторские листы') }}</option><option value="ficbook_pages">{{ t('Страницы Ficbook') }}</option>
          </select>
          <select v-else-if="field.key === 'work_method'" :value="draft.work_method" @change="setField(field.key, field.kind, $event)">
            <option value="manual">{{ t('Вручную') }}</option><option value="sync">{{ t('Синхронизация') }}</option><option value="app">{{ t('В приложении') }}</option>
          </select>
          <select v-else-if="field.key === 'status'" :value="draft.status" @change="setField(field.key, field.kind, $event)">
            <option :value="draft.status">{{ t(draft.status) }}</option><option value="активен">{{ t('активен') }}</option>
            <option value="заморожен">{{ t('заморожен') }}</option><option value="завершен">{{ t('завершён') }}</option>
          </select>
          <input v-else :type="field.kind === 'boolean' ? 'checkbox' : field.kind === 'number' ? 'number' : 'text'" :checked="draft[field.key] === true" :value="draft[field.key] ?? ''" :step="field.kind === 'number' ? 'any' : undefined" @input="setField(field.key, field.kind, $event)" />
        </label>
        <button class="nf-button nf-button--secondary" type="submit" :disabled="pending || cloud.busy">{{ t('Сохранить выбранный результат') }}</button>
        <button class="nf-button nf-button--secondary" type="button" @click="draft = null">{{ t('Отмена') }}</button>
      </form>
      <FriendlyStatus v-for="blocker in view.blockers" :key="blocker" :code="blocker" subsystem="migrations" />
    </template>
    <p v-if="error" role="alert">{{ t('Не удалось завершить согласование. Проверьте состояние и безопасно повторите действие.') }}</p>
  </section>
</template>

<style scoped>
.metadata-authority, .metadata-actions, form { display: grid; gap: var(--nf-space-2); }
h4, p { margin: 0; }
dl { display: grid; grid-template-columns: minmax(8rem, 1fr) 2fr; gap: .3rem 1rem; }
dd { margin: 0; overflow-wrap: anywhere; }
.metadata-branch { padding: var(--nf-space-2); border: 1px solid var(--nf-color-border); }
label { display: flex; justify-content: space-between; gap: 1rem; }
</style>
