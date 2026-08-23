<script setup lang="ts">
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import {
  archiveOutline,
  arrowDownOutline,
  arrowUpOutline,
  createOutline,
  locateOutline,
  pinOutline,
  trashOutline,
} from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import type { ProjectNote } from '@/types/notes'

const props = withDefaults(
  defineProps<{
    note: ProjectNote
    disabled?: boolean
    canMoveUp?: boolean
    canMoveDown?: boolean
  }>(),
  {
    disabled: false,
    canMoveUp: false,
    canMoveDown: false,
  },
)

const emit = defineEmits<{
  edit: [note: ProjectNote]
  togglePin: [note: ProjectNote]
  toggleArchive: [note: ProjectNote]
  delete: [note: ProjectNote]
  moveUp: [note: ProjectNote]
  moveDown: [note: ProjectNote]
  openMap: [note: ProjectNote]
}>()

const locale = useLocaleStore()
const t = locale.translate

const preview = computed(() => {
  if (props.note.source_type === 'mindmap' || props.note.content_format === 'plain') {
    return props.note.content.trim()
  }
  const container = document.createElement('div')
  container.innerHTML = props.note.content
  return (container.textContent ?? '').trim()
})

const title = computed(
  () => props.note.display_title.trim() || props.note.title.trim() || t('Без названия'),
)
</script>

<template>
  <article
    class="note-card"
    :class="{ 'note-card--archived': note.archived, 'note-card--pinned': note.pinned }"
    :data-color="note.color"
  >
    <header class="note-card__header">
      <div class="note-card__title">
        <span v-if="note.pinned" class="note-card__pin-label">
          <IonIcon :icon="pinOutline" aria-hidden="true" />
          {{ t('Закреплено') }}
        </span>
        <span v-if="note.stage_name" class="note-card__stage">{{ note.stage_name }}</span>
        <h2>{{ title }}</h2>
      </div>

      <button
        class="icon-button"
        type="button"
        :aria-label="t('Редактировать заметку')"
        :disabled="disabled || note.read_only"
        @click="emit('edit', note)"
      >
        <IonIcon :icon="createOutline" aria-hidden="true" />
      </button>
    </header>

    <p v-if="preview" class="note-card__preview">{{ preview }}</p>
    <p v-else class="note-card__empty">{{ t('В заметке пока нет текста.') }}</p>

    <ul v-if="note.checklist.length" class="note-card__checklist" :aria-label="t('Чек-лист')">
      <li v-for="item in note.checklist.slice(0, 4)" :key="item.id">
        <span aria-hidden="true">{{ item.checked ? '✓' : '○' }}</span>
        <span :class="{ 'is-checked': item.checked }">{{ item.text }}</span>
      </li>
    </ul>

    <div v-if="note.tags.length || note.system_tags.length" class="note-card__tags">
      <span v-for="tag in note.system_tags" :key="`system-${tag}`">#{{ tag }}</span>
      <span v-for="tag in note.tags" :key="tag">#{{ tag }}</span>
    </div>

    <footer class="note-card__footer">
      <time :datetime="note.updated_at">
        {{ t('Изменено') }} {{ locale.formatDate(note.updated_at) }}
      </time>

      <div class="note-card__actions">
        <button
          v-if="note.source_type === 'mindmap'"
          class="icon-button"
          type="button"
          :aria-label="t('Показать заметку на карте')"
          @click="emit('openMap', note)"
        >
          <IonIcon :icon="locateOutline" aria-hidden="true" />
        </button>
        <button
          class="icon-button"
          type="button"
          :aria-label="note.pinned ? t('Открепить заметку') : t('Закрепить заметку')"
          :disabled="disabled || note.read_only"
          @click="emit('togglePin', note)"
        >
          <IonIcon :icon="pinOutline" aria-hidden="true" />
        </button>
        <button
          class="icon-button"
          type="button"
          :aria-label="t('Переместить заметку выше')"
          :disabled="disabled || note.read_only || !canMoveUp"
          @click="emit('moveUp', note)"
        >
          <IonIcon :icon="arrowUpOutline" aria-hidden="true" />
        </button>
        <button
          class="icon-button"
          type="button"
          :aria-label="t('Переместить заметку ниже')"
          :disabled="disabled || note.read_only || !canMoveDown"
          @click="emit('moveDown', note)"
        >
          <IonIcon :icon="arrowDownOutline" aria-hidden="true" />
        </button>
        <button
          class="icon-button"
          type="button"
          :aria-label="note.archived ? t('Вернуть заметку из архива') : t('Архивировать заметку')"
          :disabled="disabled || note.read_only"
          @click="emit('toggleArchive', note)"
        >
          <IonIcon :icon="archiveOutline" aria-hidden="true" />
        </button>
        <button
          class="icon-button icon-button--danger"
          type="button"
          :aria-label="t('Удалить заметку')"
          :disabled="disabled || note.read_only"
          @click="emit('delete', note)"
        >
          <IonIcon :icon="trashOutline" aria-hidden="true" />
        </button>
      </div>
    </footer>
  </article>
</template>

<style scoped>
.note-card {
  --note-accent: var(--nf-color-border);
  --note-paper: var(--nf-color-surface);
  position: relative;
  display: grid;
  gap: var(--nf-space-4);
  min-width: 0;
  min-height: 18rem;
  overflow: hidden;
  padding: var(--nf-space-5);
  border: 1px solid color-mix(in srgb, var(--note-accent) 48%, var(--nf-color-border));
  border-top: 0.38rem solid var(--note-accent);
  border-radius: var(--nf-radius-sm);
  background: var(--note-paper);
  box-shadow: 0 10px 26px rgb(43 55 50 / 10%);
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.note-card::after {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 1.5rem;
  height: 1.5rem;
  background: linear-gradient(135deg, color-mix(in srgb, var(--note-accent) 18%, transparent) 50%, var(--nf-color-canvas) 51%);
  content: '';
}

.note-card:hover { transform: translateY(-2px); box-shadow: 0 16px 34px rgb(43 55 50 / 15%); }

.note-card[data-color='coral'] { --note-accent: #d96c60; --note-paper: color-mix(in srgb, #d96c60 9%, var(--nf-color-surface)); }
.note-card[data-color='orange'] { --note-accent: #d98a48; --note-paper: color-mix(in srgb, #d98a48 10%, var(--nf-color-surface)); }
.note-card[data-color='yellow'] { --note-accent: #c9a83d; --note-paper: color-mix(in srgb, #f0cd55 20%, var(--nf-color-surface)); }
.note-card[data-color='green'] { --note-accent: #5b9970; --note-paper: color-mix(in srgb, #5b9970 9%, var(--nf-color-surface)); }
.note-card[data-color='teal'] { --note-accent: #4c9a98; --note-paper: color-mix(in srgb, #4c9a98 9%, var(--nf-color-surface)); }
.note-card[data-color='blue'] { --note-accent: #568dcc; --note-paper: color-mix(in srgb, #568dcc 9%, var(--nf-color-surface)); }
.note-card[data-color='purple'] { --note-accent: #826cb7; --note-paper: color-mix(in srgb, #826cb7 9%, var(--nf-color-surface)); }
.note-card[data-color='pink'] { --note-accent: #c5729b; --note-paper: color-mix(in srgb, #c5729b 9%, var(--nf-color-surface)); }
.note-card[data-color='brown'] { --note-accent: #92715b; --note-paper: color-mix(in srgb, #92715b 9%, var(--nf-color-surface)); }
.note-card[data-color='gray'] { --note-accent: #7d8783; --note-paper: color-mix(in srgb, #7d8783 8%, var(--nf-color-surface)); }

.note-card--archived {
  opacity: 0.78;
}

.note-card__header,
.note-card__footer {
  display: flex;
  gap: var(--nf-space-3);
  align-items: flex-start;
  justify-content: space-between;
}

.note-card__title {
  min-width: 0;
}

.note-card h2 {
  margin: var(--nf-space-1) 0 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: 1.35rem;
  overflow-wrap: anywhere;
  white-space: pre-line;
}

.note-card__pin-label,
.note-card__stage {
  display: inline-flex;
  gap: var(--nf-space-1);
  align-items: center;
  margin-right: var(--nf-space-2);
  color: var(--nf-color-primary);
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
}

.note-card__preview,
.note-card__empty {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--nf-color-text-muted);
  line-height: 1.55;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 6;
}

.note-card__empty {
  font-style: italic;
}

.note-card__checklist {
  display: grid;
  gap: var(--nf-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.note-card__checklist li {
  display: flex;
  gap: var(--nf-space-2);
  align-items: flex-start;
}

.is-checked {
  text-decoration: line-through;
  opacity: 0.7;
}

.note-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--nf-space-2);
}

.note-card__tags span {
  padding: 0.2rem 0.55rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
  font-size: 0.75rem;
  font-weight: 700;
}

.note-card__footer {
  align-items: center;
  margin-top: auto;
  padding-top: var(--nf-space-3);
  border-top: 1px solid var(--nf-color-border);
}

.note-card__footer time {
  color: var(--nf-color-text-muted);
  font-size: 0.72rem;
}

.note-card__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.icon-button {
  display: inline-grid;
  width: 2.75rem;
  min-width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: var(--nf-radius-sm);
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.icon-button:hover:not(:disabled) {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
}

.icon-button--danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--nf-color-danger) 12%, transparent);
  color: var(--nf-color-danger);
}

.icon-button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

@media (max-width: 39.99rem) {
  .note-card__footer {
    align-items: stretch;
    flex-direction: column;
  }

  .note-card__actions {
    justify-content: flex-start;
  }
}
</style>
