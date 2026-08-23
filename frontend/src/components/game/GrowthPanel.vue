<script setup lang="ts">
import { ref } from 'vue'

import InspirationPanel from '@/components/game/InspirationPanel.vue'
import QuestsPanel from '@/components/game/QuestsPanel.vue'
import SkillsPanel from '@/components/game/SkillsPanel.vue'
import SpecializationPanel from '@/components/game/SpecializationPanel.vue'
import { useLocaleStore } from '@/stores/locale'
import type {
  GameQuests,
  GameSkills,
  InspirationState,
  SpecializationsState,
} from '@/types/game'

defineProps<{
  inspiration: InspirationState
  inspirationPoints: number
  specializations: SpecializationsState
  skills: GameSkills
  quests: GameQuests
  level: number
  busy: boolean
}>()

const emit = defineEmits<{
  activateInspiration: [abilityId: string]
  resolveCreativeEvent: [choice: 'safe' | 'risk']
  selectSpecialization: [specializationId: string]
  activateSpecialization: []
  increaseSkill: [skillId: string]
  startQuest: [questId: string]
  abandonQuest: [questId: string]
}>()

type GrowthTab = 'inspiration' | 'specialization' | 'skills' | 'quests'

const locale = useLocaleStore()
const t = locale.translate
const tab = ref<GrowthTab>('inspiration')
const tabs: ReadonlyArray<{ key: GrowthTab; label: string }> = [
  { key: 'inspiration', label: 'Вдохновение' },
  { key: 'specialization', label: 'Специализация' },
  { key: 'skills', label: 'Навыки' },
  { key: 'quests', label: 'Задания' },
]
</script>

<template>
  <section class="game-panel" :aria-labelledby="'growth-title'">
    <header class="panel-heading">
      <p>{{ t('Развитие') }}</p>
      <h2 id="growth-title">{{ t('Способности и задания') }}</h2>
    </header>

    <div class="growth-tabs" role="tablist" :aria-label="t('Раздел развития')">
      <button
        v-for="item in tabs"
        :key="item.key"
        :id="`growth-tab-${item.key}`"
        type="button"
        role="tab"
        :aria-selected="tab === item.key"
        :aria-controls="`growth-panel-${item.key}`"
        :class="{ active: tab === item.key }"
        @click="tab = item.key"
      >
        {{ t(item.label) }}
      </button>
    </div>

    <div
      :id="`growth-panel-${tab}`"
      role="tabpanel"
      :aria-labelledby="`growth-tab-${tab}`"
      tabindex="0"
    >
      <InspirationPanel
        v-if="tab === 'inspiration'"
        :inspiration="inspiration"
        :points="inspirationPoints"
        :busy="busy"
        @activate="(id) => emit('activateInspiration', id)"
        @resolve="(choice) => emit('resolveCreativeEvent', choice)"
      />
      <SpecializationPanel
        v-else-if="tab === 'specialization'"
        :specializations="specializations"
        :level="level"
        :busy="busy"
        @select="(id) => emit('selectSpecialization', id)"
        @activate="emit('activateSpecialization')"
      />
      <SkillsPanel
        v-else-if="tab === 'skills'"
        :skills="skills"
        :busy="busy"
        @increase="(id) => emit('increaseSkill', id)"
      />
      <QuestsPanel
        v-else
        :quests="quests"
        :level="level"
        :busy="busy"
        @start="(id) => emit('startQuest', id)"
        @abandon="(id) => emit('abandonQuest', id)"
      />
    </div>
  </section>
</template>

<style scoped>
.game-panel {
  padding: var(--nf-space-5);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-lg);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
}

.panel-heading p,
.panel-heading h2 {
  margin: 0;
}

.panel-heading p {
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.panel-heading h2 {
  font-family: var(--nf-font-serif);
}

.growth-tabs {
  display: flex;
  gap: var(--nf-space-1);
  margin: var(--nf-space-5) 0;
  overflow-x: auto;
  border-bottom: 1px solid var(--nf-color-border);
}

.growth-tabs button {
  flex: 0 0 auto;
  min-height: 2.8rem;
  padding: 0.65rem 0.85rem;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.growth-tabs button.active {
  border-bottom-color: var(--nf-color-primary);
  color: var(--nf-color-primary);
  font-weight: 750;
}

[role='tabpanel']:focus-visible {
  outline: 3px solid var(--nf-color-focus);
  outline-offset: 3px;
}

@media (max-width: 44rem) {
  .game-panel {
    padding: var(--nf-space-4);
  }
}
</style>
