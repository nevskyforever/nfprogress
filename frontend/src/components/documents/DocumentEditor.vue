<script setup lang="ts">
import { computed } from 'vue'
import DocumentEditorView from './DocumentEditorView.vue'
import type { DocumentScope } from '@/types/documents'

const props = defineProps<{ scope: DocumentScope; title: string }>()

// `useDocumentSync` captures its scope while the editor view is created. Routes
// reuse this wrapper when a user switches between a project and one of its
// stages, so give each document its own editor-view instance.
const scopeKey = computed(() => `${props.scope.projectId}:${props.scope.stageId ?? 'project'}`)
</script>

<template>
  <DocumentEditorView :key="scopeKey" :scope="scope" :title="title" />
</template>
