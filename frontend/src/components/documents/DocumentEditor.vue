<script setup lang="ts">
import DocumentEditorView from './DocumentEditorView.vue'
import type { DocumentScope } from '@/types/documents'

defineProps<{ scope: DocumentScope; title: string }>()
</script>

<template>
  <DocumentEditorView :scope="scope" :title="title" />
</template>
