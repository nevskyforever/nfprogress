<script setup lang="ts">
import { computed,ref } from 'vue'
import { useCloudSessionStore } from '@/stores/cloudSession'
import { useLocaleStore } from '@/stores/locale'
import FriendlyStatus from './FriendlyStatus.vue'
import type { ContentNoteConflict } from '@/cloud/contentNoteRuntime'
const props=defineProps<{projectId:string}>()
const cloud=useCloudSessionStore(),t=useLocaleStore().translate
const view=computed(()=>cloud.noteAuthority[props.projectId])
const pending=ref(false),error=ref<string|null>(null)
async function action(publish:boolean){
  if(pending.value||cloud.busy)return
  pending.value=true;error.value=null
  try{if(publish)await cloud.beginNotes(props.projectId);else await cloud.inspectNotes(props.projectId)}
  catch(e){error.value=e instanceof Error?e.message:'unknown_error'}finally{pending.value=false}
}
async function choose(group:ContentNoteConflict,selected:string){
  if(pending.value||cloud.busy)return
  pending.value=true;error.value=null
  try{await cloud.chooseNoteVersion(props.projectId,group,selected)}catch(e){error.value=e instanceof Error?e.message:'unknown_error';await cloud.inspectNotes(props.projectId)}finally{pending.value=false}
}
</script>
<template>
  <section class="note-authority">
    <h4>{{ t('Синхронизация заметок') }}</h4>
    <p>{{ t('Простые заметки проекта и заметки этапов публикуются только по вашему действию. Заметки интеллект-карт публикуются вместе с картами.') }}</p>
    <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="action(false)">{{ t('Проверить состояние') }}</button>
    <FriendlyStatus v-if="view" :code="view.state==='content_local'?'structural_local':view.state" domain="structure" subsystem="sync" />
    <button class="nf-button" :disabled="pending||cloud.busy" @click="action(true)">{{ t('Опубликовать заметки') }}</button>
    <template v-if="view"><article v-for="candidate in view.candidates.filter(c=>c.blocker)" :key="candidate.note_id"><h5>{{ candidate.title || t('Заметка') }}</h5><FriendlyStatus :code="candidate.blocker!" subsystem="sync" /></article></template>
    <article v-for="group in cloud.noteConflicts[projectId]||[]" :key="group.group_id">
      <h5>{{ group.versions.find(v=>v.note.title)?.note.title || t('Заметка') }}</h5>
      <p>{{ t('Сохранены разные версии заметки. Выберите версию, которую хотите использовать.') }}</p>
      <div v-for="version in group.versions" :key="version.event_id">
        <pre>{{ version.operation==='delete' ? t('Заметка удалена') : version.note.content }}</pre>
        <button class="nf-button" :disabled="pending||cloud.busy" @click="choose(group,version.event_id)">{{ t('Использовать эту версию') }}</button>
      </div>
    </article>
    <FriendlyStatus v-if="error" :code="error" subsystem="sync" />
  </section>
</template>
<style scoped>.note-authority{display:grid;gap:var(--nf-space-2)}h4,p{margin:0}pre{white-space:pre-wrap;max-height:15rem;overflow:auto}</style>
