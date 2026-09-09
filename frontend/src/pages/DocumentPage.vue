<script setup lang="ts">
import { computed } from 'vue'
import { IonContent, IonPage } from '@ionic/vue'
import { useRoute } from 'vue-router'
import DocumentEditor from '@/components/documents/DocumentEditor.vue'
import { useLocaleStore } from '@/stores/locale'

const route = useRoute()
const locale = useLocaleStore()
const t = locale.translate
const projectId = computed(() => String(route.params.projectId))
const stageId = computed(() => {
  if (typeof route.params.stageId === 'string') return route.params.stageId
  // Keep old bookmarks and previously opened browser tabs compatible.
  return typeof route.query.stageId === 'string' ? route.query.stageId : undefined
})
const title = computed(() => typeof route.query.title === 'string' ? route.query.title : (stageId.value ? t('Текст источника') : t('Текст проекта')))
</script>
<template><IonPage><IonContent :fullscreen="true"><DocumentEditor :scope="{ projectId, stageId }" :title="title" /></IonContent></IonPage></template>
