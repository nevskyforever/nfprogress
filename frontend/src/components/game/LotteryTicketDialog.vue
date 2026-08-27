<script setup lang="ts">
import { IonContent, IonModal } from '@ionic/vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { useLocaleStore } from '@/stores/locale'

export interface LotteryDraw {
  player_numbers: number[]
  winning_numbers: number[]
  matches: number
  prize: number
}

const props = defineProps<{
  draws: LotteryDraw[]
}>()

const emit = defineEmits<{ close: [] }>()

const locale = useLocaleStore()
const t = locale.translate
const currentIndex = ref(0)
const revealedCount = ref(0)
const rollingNumbers = ref<number[]>([1, 1, 1, 1, 1])
let animationTimer: ReturnType<typeof window.setInterval> | undefined

const currentDraw = computed(() => props.draws[currentIndex.value] ?? null)
const isComplete = computed(() => revealedCount.value === 5)

function randomNumbers(): void {
  rollingNumbers.value = Array.from({ length: 5 }, () => Math.floor(Math.random() * 30) + 1)
}

function stopAnimation(): void {
  if (animationTimer !== undefined) window.clearInterval(animationTimer)
  animationTimer = undefined
}

function startAnimation(): void {
  stopAnimation()
  revealedCount.value = 0
  randomNumbers()
  let ticks = 0
  animationTimer = window.setInterval(() => {
    randomNumbers()
    ticks += 1
    if (ticks % 5 !== 0) return
    revealedCount.value += 1
    if (revealedCount.value === 5) stopAnimation()
  }, 90)
}

function displayedNumber(numbers: number[], index: number): number {
  return index < revealedCount.value
    ? (numbers[index] ?? 0)
    : (rollingNumbers.value[index] ?? 0)
}

function isMatch(number: number): boolean {
  const draw = currentDraw.value
  return draw ? draw.player_numbers.includes(number) && draw.winning_numbers.includes(number) : false
}

function next(): void {
  if (!isComplete.value) return
  if (currentIndex.value + 1 < props.draws.length) {
    currentIndex.value += 1
    startAnimation()
    return
  }
  emit('close')
}

watch(() => props.draws, () => {
  currentIndex.value = 0
  if (props.draws.length) startAnimation()
}, { immediate: true })

onBeforeUnmount(stopAnimation)
</script>

<template>
  <IonModal
    :is-open="draws.length > 0"
    css-class="lottery-ticket-modal"
    :backdrop-dismiss="false"
    :keyboard-close="false"
  >
    <IonContent class="lottery-dialog">
      <main v-if="currentDraw" class="lottery-dialog__card" aria-live="polite">
        <p class="lottery-dialog__eyebrow">{{ t('Лотерейный билет') }}</p>
        <h2>{{ t('🎟️ Розыгрыш «5 из 30»') }}</h2>
        <p class="lottery-dialog__hint">
          {{ isComplete ? t('Зелёным отмечены совпадения, красным — несовпадения.') : t('Числа определяются…') }}
        </p>

        <div class="lottery-dialog__row">
          <span>{{ t('Ваши числа') }}</span>
          <b
            v-for="(number, index) in currentDraw.player_numbers"
            :key="`player-${index}`"
            :class="['lottery-ball', { match: index < revealedCount && isMatch(number), miss: index < revealedCount && !isMatch(number) }]"
          >{{ displayedNumber(currentDraw.player_numbers, index) }}</b>
        </div>
        <div class="lottery-dialog__row">
          <span>{{ t('Выигрышные числа') }}</span>
          <b
            v-for="(number, index) in currentDraw.winning_numbers"
            :key="`winning-${index}`"
            :class="['lottery-ball', { match: index < revealedCount && isMatch(number), miss: index < revealedCount && !isMatch(number) }]"
          >{{ displayedNumber(currentDraw.winning_numbers, index) }}</b>
        </div>

        <p v-if="isComplete" class="lottery-dialog__result">
          <template v-if="currentDraw.prize">
            {{ t(`Совпало чисел: ${currentDraw.matches}. Выигрыш: ${currentDraw.prize} монет!`) }}
          </template>
          <template v-else>{{ t(`Совпало чисел: ${currentDraw.matches}. В этот раз не повезло :(`) }}</template>
        </p>

        <button class="nf-button" type="button" :disabled="!isComplete" @click="next">
          {{ currentIndex + 1 < draws.length ? t('Следующий билет') : t('Закрыть') }}
        </button>
      </main>
    </IonContent>
  </IonModal>
</template>

<style scoped>
.lottery-dialog { --background: transparent; }
.lottery-dialog__card { min-height: 100%; display: grid; place-content: center; gap: 1rem; padding: 2rem; text-align: center; background: radial-gradient(circle at top, #273d63, #111827 68%); color: #fff; }
.lottery-dialog__card h2 { margin: 0; font-size: clamp(1.5rem, 4vw, 2.25rem); }
.lottery-dialog__eyebrow, .lottery-dialog__hint { margin: 0; color: #c9d6ef; }
.lottery-dialog__row { display: grid; grid-template-columns: minmax(8rem, 1fr) repeat(5, minmax(2.5rem, 3.5rem)); gap: .5rem; align-items: center; text-align: left; }
.lottery-ball { display: grid; place-items: center; aspect-ratio: 1; border-radius: 50%; background: #3d4b61; font-size: 1.15rem; transition: background-color .2s, transform .2s; }
.lottery-ball.match { background: #259a59; transform: scale(1.06); }
.lottery-ball.miss { background: #ad4851; }
.lottery-dialog__result { margin: .5rem 0 0; font-weight: 700; font-size: 1.1rem; }
@media (max-width: 480px) { .lottery-dialog__card { padding: 1.25rem; } .lottery-dialog__row { grid-template-columns: repeat(5, 1fr); } .lottery-dialog__row > span { grid-column: 1 / -1; text-align: center; } }
</style>
