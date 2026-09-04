<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { IonContent, IonIcon, IonPage, onIonViewWillEnter } from '@ionic/vue'
import { closeCircleOutline, searchOutline } from 'ionicons/icons'
import { documentsApi } from '@/api/documents'
import { projectsApi } from '@/api/projects'
import StatePanel from '@/components/ui/StatePanel.vue'
import { onDataChange } from '@/services/dataChanges'
import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types/api'
import type { ProjectDocument } from '@/types/documents'

const documents = ref<ProjectDocument[]>([]); const projects = ref<Project[]>([])
const locale = useLocaleStore()
const t = locale.translate
const search = ref('')
let loadSequence = 0
let stopDataChanges: (() => void) | undefined
function projectFor(document: ProjectDocument): Project | undefined { return projects.value.find((item) => item.id === document.project_id) }
function ownerFor(document: ProjectDocument): Project | undefined {
  const project = projectFor(document)
  if (!project) return undefined
  return document.stage_id
    ? project.stages.find((stage) => stage.id === document.stage_id)
    : project
}
function isAppDocument(document: ProjectDocument): boolean {
  return ownerFor(document)?.work_method === 'app'
}
function stageNameFor(document: ProjectDocument): string {
  const project = projectFor(document)
  return document.stage_id
    ? project?.stages.find((stage) => stage.id === document.stage_id)?.name ?? 'Удалённый этап'
    : ''
}
function nameFor(document: ProjectDocument): string {
  const project = projectFor(document)
  if (!project) return 'Удалённый проект'
  return document.stage_id ? `${project.name}: ${stageNameFor(document)}` : project.name
}
function documentTimestamp(document: ProjectDocument): number {
  if (!document.updated_at) return 0
  const timestamp = Date.parse(document.updated_at)
  return Number.isFinite(timestamp) ? timestamp : 0
}
const visibleDocuments = computed(() => {
  const query = search.value.trim().toLocaleLowerCase(locale.localeTag)
  const sorted = documents.value.filter(isAppDocument).sort(
    (left, right) => documentTimestamp(right) - documentTimestamp(left),
  )
  if (!query) return sorted
  return sorted.filter((document) => nameFor(document)
    .toLocaleLowerCase(locale.localeTag).includes(query))
})
async function loadDocuments(): Promise<void> {
  const sequence = ++loadSequence
  const [loadedDocuments, loadedProjects] = await Promise.all([
    documentsApi.list(),
    projectsApi.list({}),
  ])
  if (sequence !== loadSequence) return
  documents.value = loadedDocuments
  projects.value = loadedProjects
}
onMounted(() => {
  void loadDocuments()
  stopDataChanges = onDataChange((scope) => {
    if (scope === 'projects') void loadDocuments()
  })
})
onIonViewWillEnter(() => { void loadDocuments() })
onBeforeUnmount(() => {
  loadSequence += 1
  stopDataChanges?.()
})
</script>
<template><IonPage><IonContent :fullscreen="true"><main class="texts"><p class="eyebrow">Документы</p><h1>Тексты</h1><label class="texts-search" for="texts-search"><span class="visually-hidden">{{ t('Поиск по проектам и этапам') }}</span><IonIcon :icon="searchOutline" aria-hidden="true" /><input id="texts-search" v-model="search" autocomplete="off" :placeholder="t('Поиск по проектам и этапам')" type="search" /><button v-if="search" :aria-label="t('Очистить поиск')" class="clear-search" type="button" @click="search = ''"><IonIcon :icon="closeCircleOutline" aria-hidden="true" /></button></label><p v-if="!documents.length">Здесь появятся тексты проектов и этапов после первого открытия редактора.</p><StatePanel v-else-if="!visibleDocuments.length" :icon="searchOutline" :title="t('Ничего не найдено')"><button class="nf-button nf-button--secondary" type="button" @click="search = ''">{{ t('Очистить поиск') }}</button></StatePanel><ul v-else><li v-for="item in visibleDocuments" :key="`${item.project_id}:${item.stage_id}`"><RouterLink :to="item.stage_id ? { name: 'stage-document', params: { projectId: item.project_id, stageId: item.stage_id }, query: { title: nameFor(item) } } : { name: 'document', params: { projectId: item.project_id }, query: { title: nameFor(item) } }"><strong>{{ nameFor(item) }}</strong><span v-if="!item.stage_id"> → текст проекта</span></RouterLink></li></ul></main></IonContent></IonPage></template>
<style scoped>.texts{width:min(100%,70rem);margin:0 auto;padding:var(--nf-space-6)}.texts h1{margin-top:0}.eyebrow{color:var(--nf-color-text-muted);font-weight:700;text-transform:uppercase;font-size:.8rem}.texts-search{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:var(--nf-space-2);align-items:center;min-height:3rem;margin:var(--nf-space-5) 0;padding:0 var(--nf-space-3);border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-sm);background:var(--nf-color-surface)}.texts-search:focus-within{border-color:var(--nf-color-focus);box-shadow:0 0 0 2px color-mix(in srgb,var(--nf-color-focus) 25%,transparent)}.texts-search input{width:100%;min-height:2.75rem;border:0;outline:0;background:transparent;color:var(--nf-color-text)}.texts-search input::placeholder{color:var(--nf-color-text-muted)}.clear-search{display:grid;width:2.5rem;height:2.5rem;padding:0;place-items:center;border:0;border-radius:var(--nf-radius-pill);background:transparent;color:var(--nf-color-text-muted);cursor:pointer}.clear-search ion-icon{font-size:1.25rem}.texts ul{display:grid;gap:.6rem;padding:0;list-style:none}.texts a{display:block;padding:1rem;border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-md);color:var(--nf-color-text);background:var(--nf-color-surface);text-decoration:none}.texts span{color:var(--nf-color-text-muted)}</style>
