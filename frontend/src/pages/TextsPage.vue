<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { IonContent, IonPage, onIonViewWillEnter } from '@ionic/vue'
import { documentsApi } from '@/api/documents'
import { projectsApi } from '@/api/projects'
import { onDataChange } from '@/services/dataChanges'
import type { Project } from '@/types/api'
import type { ProjectDocument } from '@/types/documents'

const documents = ref<ProjectDocument[]>([]); const projects = ref<Project[]>([])
let loadSequence = 0
let stopDataChanges: (() => void) | undefined
function nameFor(document: ProjectDocument): string { const project = projects.value.find((item) => item.id === document.project_id); if (!project) return 'Удалённый проект'; return document.stage_id ? project.stages.find((stage) => stage.id === document.stage_id)?.name ?? 'Удалённый этап' : project.name }
function projectFor(document: ProjectDocument): Project | undefined { return projects.value.find((item) => item.id === document.project_id) }
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
<template><IonPage><IonContent :fullscreen="true"><main class="texts"><p class="eyebrow">Документы</p><h1>Тексты</h1><p v-if="!documents.length">Здесь появятся тексты проектов и этапов после первого открытия редактора.</p><ul v-else><li v-for="item in documents" :key="`${item.project_id}:${item.stage_id}`"><RouterLink :to="{ name: 'document', params: { projectId: item.project_id }, query: { ...(item.stage_id ? { stageId: item.stage_id } : {}), title: nameFor(item) } }"><strong>{{ projectFor(item)?.name }}</strong><span> → {{ item.stage_id ? `этап: ${nameFor(item)}` : 'текст проекта' }}</span></RouterLink></li></ul></main></IonContent></IonPage></template>
<style scoped>.texts{width:min(100%,70rem);margin:0 auto;padding:var(--nf-space-6)}.texts h1{margin-top:0}.eyebrow{color:var(--nf-color-text-muted);font-weight:700;text-transform:uppercase;font-size:.8rem}.texts ul{display:grid;gap:.6rem;padding:0;list-style:none}.texts a{display:block;padding:1rem;border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-md);color:var(--nf-color-text);background:var(--nf-color-surface);text-decoration:none}.texts span{color:var(--nf-color-text-muted)}</style>
