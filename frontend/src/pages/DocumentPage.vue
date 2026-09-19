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
const stageId = computed(() => route.name === 'stage-document' && typeof route.params.stageId === 'string'
  ? route.params.stageId
  : undefined)
const title = computed(() => typeof route.query.title === 'string' ? route.query.title : (stageId.value ? t('Текст источника') : t('Текст проекта')))
</script>
<template><IonPage><IonContent :fullscreen="true"><DocumentEditor :scope="{ projectId, stageId }" :title="title" /></IonContent></IonPage></template>
