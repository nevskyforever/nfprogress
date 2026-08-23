<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { IonContent, IonIcon, IonPage } from '@ionic/vue'
import { alertCircleOutline, refreshOutline, sparklesOutline } from 'ionicons/icons'

import { apiErrorMessage } from '@/api/client'
import { gameApi } from '@/api/game'
import { settingsApi } from '@/api/settings'
import AwardsBankPanel from '@/components/game/AwardsBankPanel.vue'
import CabinetPanel from '@/components/game/CabinetPanel.vue'
import ChallengesPanel from '@/components/game/ChallengesPanel.vue'
import GameOverview from '@/components/game/GameOverview.vue'
import GrowthPanel from '@/components/game/GrowthPanel.vue'
import InventoryShopPanel from '@/components/game/InventoryShopPanel.vue'
import WritingSessionPanel from '@/components/game/WritingSessionPanel.vue'
import StatePanel from '@/components/ui/StatePanel.vue'
import { useLocaleStore } from '@/stores/locale'
import { useNotificationsStore } from '@/stores/notifications'
import type {
  BankProductRequest,
  GameCommandResponse,
  GameState,
  InventoryCommand,
  WritingSessionStart,
} from '@/types/game'

type GameTab =
  | 'overview'
  | 'sessions'
  | 'challenges'
  | 'items'
  | 'growth'
  | 'cabinet'
  | 'economy'

const locale = useLocaleStore()
const notifications = useNotificationsStore()
const t = locale.translate
const state = ref<GameState | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const tab = ref<GameTab>('overview')
const bankPreview = ref<GameCommandResponse['result']>(null)
const inventoryCategory = ref('')
let stateController: AbortController | undefined
let preferencesController: AbortController | undefined
let preferenceRequest = 0
let inventoryPreferenceSaveChain: Promise<void> = Promise.resolve()

const tabs: ReadonlyArray<{ key: GameTab; label: string }> = [
  { key: 'overview', label: 'Обзор' },
  { key: 'sessions', label: 'Сессии' },
  { key: 'challenges', label: 'Испытания' },
  { key: 'items', label: 'Предметы' },
  { key: 'growth', label: 'Развитие' },
  { key: 'cabinet', label: 'Кабинет' },
  { key: 'economy', label: 'Награды и банк' },
]

function applyState(nextState: GameState): void {
  state.value = nextState
  notifications.setGameHistory(nextState.notifications)
}

async function loadState(showRefresh = false): Promise<void> {
  stateController?.abort()
  stateController = new AbortController()
  if (showRefresh) refreshing.value = true
  else if (!state.value) loading.value = true
  error.value = ''
  try {
    applyState(await gameApi.state(stateController.signal))
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === 'AbortError') return
    error.value = apiErrorMessage(caught)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function loadInventoryPreference(): Promise<void> {
  preferencesController?.abort()
  preferencesController = new AbortController()
  const request = ++preferenceRequest
  try {
    const settings = await settingsApi.get(preferencesController.signal)
    const value = settings.values.inventory_filter
    if (request === preferenceRequest && typeof value === 'string') {
      inventoryCategory.value = value
    }
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === 'AbortError') return
    // The game screen still works if a noncritical view preference is unavailable.
  }
}

function persistInventoryCategory(category: string): void {
  if (!category || category === inventoryCategory.value) return
  inventoryCategory.value = category
  const requestedCategory = category
  inventoryPreferenceSaveChain = inventoryPreferenceSaveChain
    .then(() => settingsApi.update({ inventory_filter: requestedCategory }))
    .then((settings) => {
      if (
        inventoryCategory.value === requestedCategory
        && typeof settings.values.inventory_filter === 'string'
      ) {
        inventoryCategory.value = settings.values.inventory_filter
      }
    })
    .catch((caught: unknown) => {
      error.value = apiErrorMessage(caught)
      notifications.error(error.value)
    })
}

async function runCommand(
  action: () => Promise<GameCommandResponse>,
  options: { capturePreview?: boolean; fallbackMessage?: string } = {},
): Promise<void> {
  if (busy.value) return
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    const response = await action()
    applyState(response.state)
    bankPreview.value = options.capturePreview ? response.result : null
    success.value =
      response.messages.filter(Boolean).join(' ') ||
      response.message ||
      t(options.fallbackMessage ?? 'Изменения сохранены.')
    notifications.success(success.value)
    await loadState(false)
  } catch (caught) {
    error.value = apiErrorMessage(caught)
    notifications.error(error.value)
  } finally {
    busy.value = false
  }
}

function applyFreeze(target: 'global' | 'project', projectId?: string): void {
  void runCommand(() => gameApi.applyStreakFreeze(target, projectId))
}

function startSession(payload: WritingSessionStart): void {
  void runCommand(() => gameApi.startWritingSession(payload))
}

function inventoryCommand(
  action: 'buy' | 'sell' | 'use',
  payload: InventoryCommand,
): void {
  const command = {
    buy: gameApi.buyItem,
    sell: gameApi.sellItem,
    use: gameApi.useItem,
  }[action]
  void runCommand(() => command(payload))
}

function previewBank(payload: BankProductRequest): void {
  void runCommand(() => gameApi.previewBankProduct(payload), {
    capturePreview: true,
    fallbackMessage: 'Расчёт обновлён.',
  })
}

onMounted(() => {
  void loadState()
  void loadInventoryPreference()
})
onBeforeUnmount(() => {
  stateController?.abort()
  preferencesController?.abort()
})
</script>

<template>
  <IonPage>
    <IonContent :fullscreen="true" class="game-content">
      <main class="game-workspace">
        <header class="page-header">
          <div>
            <p class="page-eyebrow">{{ t('Творческая мотивация') }}</p>
            <h1>{{ t('Игровой режим') }}</h1>
            <p class="page-introduction">
              {{ t('Развивайте писательский ритм, а все награды доверяйте правилам nfprogress.') }}
            </p>
          </div>
          <button
            class="nf-button nf-button--secondary"
            type="button"
            :disabled="loading || refreshing || busy"
            @click="loadState(true)"
          >
            <IonIcon :icon="refreshOutline" aria-hidden="true" />
            {{ refreshing ? t('Обновляем') : t('Обновить') }}
          </button>
        </header>

        <StatePanel
          v-if="loading && !state"
          :title="t('Загружаем игровой режим')"
          :message="t('Синхронизируем прогресс, награды и активные эффекты.')"
          loading
        />

        <StatePanel
          v-else-if="error && !state"
          :title="t('Не удалось загрузить игровой режим')"
          :message="error"
          :icon="alertCircleOutline"
        >
          <button class="nf-button" type="button" @click="loadState()">{{ t('Повторить') }}</button>
        </StatePanel>

        <StatePanel
          v-else-if="state && !state.enabled"
          :title="t('Игровой режим отключён')"
          :message="t('Включите игровой режим в настройках, чтобы получать опыт, монеты и испытания.')"
          :icon="sparklesOutline"
        />

        <template v-else-if="state">
          <div class="command-feedback" aria-live="polite" aria-atomic="true">
            <p v-if="error" class="feedback feedback--error">{{ error }}</p>
            <p v-else-if="success" class="feedback feedback--success">{{ success }}</p>
            <p v-else-if="busy" class="feedback">{{ t('Применяем изменение…') }}</p>
          </div>

          <nav class="game-tabs" role="tablist" :aria-label="t('Разделы игрового режима')">
            <button
              v-for="item in tabs"
              :key="item.key"
              :id="`game-tab-${item.key}`"
              type="button"
              role="tab"
              :aria-selected="tab === item.key"
              :aria-controls="`game-panel-${item.key}`"
              :class="{ active: tab === item.key }"
              @click="tab = item.key"
            >
              {{ t(item.label) }}
            </button>
          </nav>

          <section
            :id="`game-panel-${tab}`"
            class="active-game-panel"
            role="tabpanel"
            :aria-labelledby="`game-tab-${tab}`"
            tabindex="0"
          >
            <GameOverview
              v-if="tab === 'overview'"
              :profile="state.profile"
              :buffs="state.buffs"
              :streak-freezes="state.streak_freezes"
              :busy="busy"
              @apply-freeze="applyFreeze"
            />

            <WritingSessionPanel
              v-else-if="tab === 'sessions'"
              :session="state.writing_session"
              :busy="busy"
              @start="startSession"
              @finish="runCommand(() => gameApi.finishWritingSession())"
              @cancel="runCommand(() => gameApi.cancelWritingSession())"
            />

            <ChallengesPanel
              v-else-if="tab === 'challenges'"
              :daily="state.daily_challenge"
              :weekly="state.weekly_challenge"
              :inspiration="state.profile.inspiration"
              :busy="busy"
              @select-daily="(id) => runCommand(() => gameApi.selectDailyChallenge(id))"
              @start-weekly="(id) => runCommand(() => gameApi.startWeeklyChallenge(id))"
            />

            <InventoryShopPanel
              v-else-if="tab === 'items'"
              :inventory="state.inventory"
              :shop="state.shop"
              :busy="busy"
              :initial-inventory-category="inventoryCategory"
              @buy="(payload) => inventoryCommand('buy', payload)"
              @sell="(payload) => inventoryCommand('sell', payload)"
              @use="(payload) => inventoryCommand('use', payload)"
              @inventory-category="persistInventoryCategory"
            />

            <GrowthPanel
              v-else-if="tab === 'growth'"
              :inspiration="state.inspiration"
              :inspiration-points="state.profile.inspiration"
              :specializations="state.specializations"
              :skills="state.skills"
              :quests="state.quests"
              :level="state.profile.level"
              :busy="busy"
              @activate-inspiration="(id) => runCommand(() => gameApi.activateInspirationAbility(id))"
              @resolve-creative-event="(choice) => runCommand(() => gameApi.resolveCreativeEvent(choice))"
              @select-specialization="(id) => runCommand(() => gameApi.selectSpecialization(id))"
              @activate-specialization="runCommand(() => gameApi.activateSpecializationAbility())"
              @increase-skill="(id) => runCommand(() => gameApi.increaseSkill(id))"
              @start-quest="(id) => runCommand(() => gameApi.startQuest(id))"
              @abandon-quest="(id) => runCommand(() => gameApi.abandonQuest(id))"
            />

            <CabinetPanel
              v-else-if="tab === 'cabinet'"
              :manuscripts="state.manuscripts"
            />

            <AwardsBankPanel
              v-else
              :awards="state.custom_awards"
              :bank="state.bank"
              :preview="bankPreview"
              :busy="busy"
              @create-award="(name, price) => runCommand(() => gameApi.createCustomAward(name, price))"
              @update-award="(id, name, price) => runCommand(() => gameApi.updateCustomAward(id, { name, price }))"
              @delete-award="(id) => runCommand(() => gameApi.deleteCustomAward(id))"
              @buy-award="(id, count) => runCommand(() => gameApi.buyCustomAward(id, count))"
              @sell-award="(id, count) => runCommand(() => gameApi.sellCustomAward(id, count))"
              @use-award="(id, count) => runCommand(() => gameApi.useCustomAward(id, count))"
              @preview-bank="previewBank"
              @open-credit="(amount, days) => runCommand(() => gameApi.openBankCredit(amount, days))"
              @open-deposit="(amount, days, interest) => runCommand(() => gameApi.openBankDeposit(amount, days, interest))"
              @process-bank="runCommand(() => gameApi.processBankEvents())"
              @pay-credit="runCommand(() => gameApi.makeBankLoanPayment())"
              @partial-repay="(amount) => runCommand(() => gameApi.partiallyRepayBankCredit(amount))"
              @repay-credit="runCommand(() => gameApi.repayBankCredit())"
              @top-up-deposit="(amount) => runCommand(() => gameApi.topUpBankDeposit(amount))"
              @withdraw-deposit="(early) => runCommand(() => gameApi.withdrawBankDeposit(early))"
              @withdraw-interest="runCommand(() => gameApi.withdrawBankDepositInterest())"
            />
          </section>
        </template>
      </main>
    </IonContent>
  </IonPage>
</template>

<style scoped>
.game-content {
  --background: var(--nf-color-canvas);
}

.game-workspace {
  width: min(100%, 94rem);
  min-height: 100%;
  margin: 0 auto;
  padding: calc(var(--nf-space-7) + env(safe-area-inset-top)) clamp(1rem, 3vw, 3.5rem)
    calc(var(--nf-space-7) + env(safe-area-inset-bottom));
}

.page-header {
  display: flex;
  gap: var(--nf-space-5);
  align-items: flex-end;
  justify-content: space-between;
}

.page-eyebrow {
  margin: 0 0 var(--nf-space-2);
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page-header h1 {
  margin: 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(2.25rem, 6vw, 4rem);
  font-weight: 650;
  letter-spacing: -0.04em;
}

.page-introduction {
  max-width: 47rem;
  margin: var(--nf-space-3) 0 0;
  color: var(--nf-color-text-muted);
  font-size: clamp(1rem, 2vw, 1.1rem);
  line-height: 1.6;
}

.command-feedback {
  min-height: 3.25rem;
  padding-top: var(--nf-space-3);
}

.feedback {
  width: fit-content;
  max-width: 100%;
  margin: 0;
  padding: 0.6rem 0.85rem;
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-muted);
  color: var(--nf-color-text-muted);
  line-height: 1.4;
}

.feedback--success {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-success);
}

.feedback--error {
  background: color-mix(in srgb, var(--nf-color-danger) 12%, var(--nf-color-surface));
  color: var(--nf-color-danger);
}

.game-tabs {
  position: sticky;
  z-index: 5;
  top: 0;
  display: flex;
  gap: var(--nf-space-1);
  margin-bottom: var(--nf-space-5);
  padding: var(--nf-space-2);
  overflow-x: auto;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: color-mix(in srgb, var(--nf-color-surface) 94%, transparent);
  backdrop-filter: blur(12px);
}

.game-tabs button {
  flex: 1 0 auto;
  min-height: 2.75rem;
  padding: 0.65rem 0.85rem;
  border: 0;
  border-radius: var(--nf-radius-sm);
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.game-tabs button.active {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
  font-weight: 750;
}

.active-game-panel {
  outline: none;
}

.active-game-panel:focus-visible {
  outline: 3px solid var(--nf-color-focus);
}

@media (max-width: 44rem) {
  .game-workspace {
    padding-top: calc(var(--nf-space-5) + env(safe-area-inset-top));
  }

  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .page-header .nf-button {
    width: 100%;
  }

  .game-tabs {
    margin-inline: calc(-1 * clamp(1rem, 3vw, 3.5rem));
    border-inline: 0;
    border-radius: 0;
  }
}
</style>
