<script setup lang="ts">
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import {
  alertCircleOutline,
  checkmarkCircleOutline,
  closeOutline,
  informationCircleOutline,
  warningOutline,
} from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import { useNotificationsStore, type NotificationKind } from '@/stores/notifications'

const locale = useLocaleStore()
const notifications = useNotificationsStore()
const t = locale.translate

const icons: Record<NotificationKind, string> = {
  success: checkmarkCircleOutline,
  error: alertCircleOutline,
  warning: warningOutline,
  info: informationCircleOutline,
}

const labels = computed<Record<NotificationKind, string>>(() => ({
  success: t('Успешно'),
  error: t('Ошибка'),
  warning: t('Внимание'),
  info: t('Информация'),
}))
</script>

<template>
  <aside
    v-if="notifications.notifications.length"
    class="notification-stack"
    :aria-label="t('Уведомления')"
    aria-live="polite"
    aria-relevant="additions"
  >
    <article
      v-for="notification in notifications.notifications"
      :key="notification.id"
      class="notification"
      :class="`notification--${notification.kind}`"
      :role="notification.kind === 'error' ? 'alert' : 'status'"
    >
      <IonIcon :icon="icons[notification.kind]" aria-hidden="true" />
      <div>
        <strong>{{ labels[notification.kind] }}</strong>
        <p>{{ notification.message }}</p>
      </div>
      <button
        type="button"
        :aria-label="t('Закрыть уведомление')"
        @click="notifications.dismiss(notification.id)"
      >
        <IonIcon :icon="closeOutline" aria-hidden="true" />
      </button>
    </article>
  </aside>
</template>

<style scoped>
.notification-stack {
  position: fixed;
  z-index: 10010;
  right: max(var(--nf-space-4), env(safe-area-inset-right));
  bottom: max(var(--nf-space-4), env(safe-area-inset-bottom));
  display: grid;
  width: min(26rem, calc(100vw - 2 * var(--nf-space-4)));
  gap: var(--nf-space-3);
  pointer-events: none;
}

.notification {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--nf-space-3);
  align-items: start;
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-left: 0.3rem solid var(--nf-color-primary);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
  box-shadow: var(--nf-shadow-card);
  color: var(--nf-color-text);
  pointer-events: auto;
}

.notification > ion-icon {
  margin-top: 0.1rem;
  color: var(--nf-color-primary);
  font-size: 1.25rem;
}

.notification strong,
.notification p {
  margin: 0;
}

.notification strong {
  display: block;
  font-size: 0.85rem;
}

.notification p {
  margin-top: 0.12rem;
  color: var(--nf-color-text-muted);
  font-size: 0.85rem;
  line-height: 1.4;
}

.notification button {
  display: grid;
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: var(--nf-radius-sm);
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.notification button:hover,
.notification button:focus-visible {
  background: var(--nf-color-surface-muted);
  color: var(--nf-color-text);
}

.notification--success {
  border-left-color: var(--nf-color-success);
}

.notification--success > ion-icon {
  color: var(--nf-color-success);
}

.notification--error {
  border-left-color: var(--nf-color-danger);
}

.notification--error > ion-icon {
  color: var(--nf-color-danger);
}

.notification--warning {
  border-left-color: var(--nf-color-warning);
}

.notification--warning > ion-icon {
  color: var(--nf-color-warning);
}
</style>
