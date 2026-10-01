<script setup lang="ts">
import { computed, ref } from 'vue'
import { useCloudSessionStore } from '@/stores/cloudSession'
import { useLocaleStore } from '@/stores/locale'
import type { StructuralEntity } from '@/infrastructure/sqlite/stageStructuralRepository'
const props = defineProps<{ projectId: string }>()
const cloud = useCloudSessionStore(), t = useLocaleStore().translate
const view = computed(() => cloud.structuralAuthority[props.projectId])
const pending = ref(false), error = ref(false)
const labels = {
  structural_local: 'Этапы существуют только на этом устройстве. Публикация начинается вашим действием.',
  candidate_captured: 'Локальные этапы подготовлены. Продолжите публикацию.',
  publication_pending: 'Изменение этапов сохранено. Ожидается отправка.',
  published_self_echo_pending: 'Этапы отправлены. Ожидается проверенное подтверждение.',
  active: 'Этапы и их порядок согласованы.',
  conflict: 'Версии этапов или их порядка различаются. Выберите результат.',
  blocked: 'Синхронизация этапов заблокирована. Данные сохранены.',
}
async function action(operation: () => Promise<unknown>) {
  if (pending.value || cloud.busy) return
  pending.value = true; error.value = false
  try { await operation() } catch { error.value = true } finally { pending.value = false }
}
function inspect() { return action(() => cloud.inspectStructure(props.projectId)) }
function choose(entity: StructuralEntity, eventId: string) {
  return action(() => cloud.decideStructure(props.projectId, { entity_type: entity.entity_type, entity_id: entity.entity_id,
    expected_tips: [...entity.tips].sort(), expected_local: entity.local, proposed: null, selected_event_id: eventId }))
}
function keepLocal(entity: StructuralEntity) {
  return action(() => cloud.decideStructure(props.projectId, { entity_type: entity.entity_type, entity_id: entity.entity_id,
    expected_tips: [...entity.tips].sort(), expected_local: entity.local, proposed: entity.local, selected_event_id: null }))
}
const fields = [
  ['name', 'Название'], ['goal', 'Цель'], ['infinite', 'Бесконечный проект'], ['unit', 'Единица прогресса'],
  ['status', 'Статус'], ['deadline', 'Дедлайн'], ['personal_goal', 'Личная цель'], ['auto_freeze', 'Автозаморозка'],
  ['streak_enabled', 'Серия'], ['work_method', 'Метод работы'], ['created_at', 'Дата создания'], ['completed_at', 'Дата завершения'],
] as const
function stageName(id: string): string {
  const entity = view.value?.entities.find(row => row.entity_type === 'stage' && row.entity_id === id)
  return entity && !Array.isArray(entity.local) ? entity.local.name : id
}
function display(value: unknown): string {
  if (typeof value === 'boolean') return t(value ? 'Да' : 'Нет')
  if (value === null) return '—'
  const labels: Record<string, string> = { symbols: 'Символы', A4: 'Листы A4', author_list: 'Авторские листы', ficbook_pages: 'Страницы Ficbook', manual: 'Вручную', sync: 'Синхронизация', app: 'В приложении', активен: 'активен', заморожен: 'заморожен', завершен: 'завершён' }
  return typeof value === 'string' && labels[value] ? t(labels[value]) : String(value)
}
const blockerLabel = (code: string): string => code.includes('metadata') ? 'Сначала согласуйте метаданные проекта.'
  : code.includes('tombstone') ? 'Удаление этапа ожидает проверки дочерних данных. Данные сохранены.'
  : code.includes('stale') ? 'Появилась новая версия. Проверьте все ветки и выберите результат снова.'
  : code.includes('unsupported') || code.includes('invalid') ? 'Формат этапа не поддерживается. Исходные данные сохранены.'
  : code.includes('scope') ? 'Проверьте аккаунт и подключение проекта.'
  : code.includes('conflict') ? labels.conflict : 'Для порядка этапов ещё не подтверждены все зависимости.'
</script>
<template>
  <section class="stage-authority" :data-structural-state="view?.state" :aria-label="t('Этапы проекта')">
    <h4>{{ t('Этапы проекта') }}</h4>
    <button class="nf-button nf-button--secondary" :disabled="pending || cloud.busy" @click="inspect">{{ t('Проверить этапы') }}</button>
    <template v-if="view">
      <p>{{ t(labels[view.state]) }}</p>
      <button v-if="view.state === 'structural_local' && cloud.metadataTransportMode === 3" class="nf-button nf-button--secondary" :disabled="pending || cloud.busy" @click="action(() => cloud.beginStructure(projectId))">{{ t('Опубликовать локальные этапы') }}</button>
      <button v-if="['publication_pending', 'published_self_echo_pending', 'candidate_captured', 'blocked'].includes(view.state)" class="nf-button nf-button--secondary" :disabled="pending || cloud.busy" @click="action(async () => { if (view?.state === 'candidate_captured') await cloud.beginStructure(projectId); else await cloud.retry(); await cloud.inspectStructure(projectId) })">{{ t('Безопасно продолжить') }}</button>
      <div v-for="entity in view.entities.filter(item => item.conflict && item.tips.length)" :key="entity.entity_id">
        <h5>{{ entity.entity_type === 'stage_order' ? t('Порядок этапов') : typeof entity.local === 'object' && !Array.isArray(entity.local) ? entity.local.name : entity.entity_id }}</h5>
        <div v-for="branch in entity.branches" :key="branch.header.event_id">
          <p>{{ branch.header.operation === 'delete' ? t('Удаление этапа ожидает проверки дочерних данных. Данные сохранены.') : branch.stage?.name ?? branch.stage_ids?.map(stageName).join(' → ') }}</p>
          <dl v-if="branch.stage"><template v-for="[key, label] in fields" :key="key"><dt>{{ t(label) }}</dt><dd>{{ key === 'name' ? branch.stage[key] : display(branch.stage[key]) }}</dd></template></dl>
          <button class="nf-button nf-button--secondary" :disabled="pending || cloud.busy" @click="choose(entity, branch.header.event_id)">{{ t('Использовать эту версию для согласования') }}</button>
        </div>
        <button class="nf-button nf-button--secondary" :disabled="pending || cloud.busy" @click="keepLocal(entity)">{{ t('Сохранить локальную версию как новое облачное изменение') }}</button>
      </div>
      <p v-if="view.entities.some(item => item.causal_tombstone_selected)">{{ t('Удаление этапа выбрано. Физическое удаление пока заблокировано; дочерние данные сохранены.') }}</p>
      <p v-for="blocker in view.blockers" :key="blocker">{{ t(blockerLabel(blocker)) }}</p>
    </template>
    <p v-if="error" role="alert">{{ t('Не удалось завершить согласование. Проверьте состояние и безопасно повторите действие.') }}</p>
  </section>
</template>
<style scoped>
.stage-authority { display: grid; gap: var(--nf-space-2); }
p, h4, h5 { margin: 0; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
