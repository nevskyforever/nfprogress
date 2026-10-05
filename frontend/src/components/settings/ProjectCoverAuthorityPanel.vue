<script setup lang="ts">
import {computed,onMounted,onUnmounted,ref,watch} from 'vue'
import {useCloudSessionStore} from '@/stores/cloudSession'
import {useLocaleStore} from '@/stores/locale'
import {onDataChange} from '@/services/dataChanges'
const props=defineProps<{projectId:string}>()
const cloud=useCloudSessionStore(),t=useLocaleStore().translate,pending=ref(false),failed=ref(false)
const view=computed(()=>cloud.coverAuthority[props.projectId])
const status=computed(()=>{
 const v=view.value
 if(v?.blockers.includes('cover_blob_invalid'))return 'Обложка не прошла проверку'
 if(v?.blockers.includes('cover_blob_missing'))return 'Зашифрованная обложка пока недоступна'
 if(['metadata_conflict','genesis_conflict'].includes(v?.metadata_state??'')||v?.pending?.blocker==='cover_conflict')return 'Конфликт обложки: выберите полную версию настроек проекта'
 if(v?.pending?.blocker==='cover_source_invalid')return 'Локальная обложка повреждена или не поддерживается'
 if(v?.pending?.blocker==='cover_readers_not_ready')return 'Для обложки требуется обновление всех устройств'
 if(v?.pending)return 'Публикация обложки ожидает завершения'
 return v?.active?'Обложка синхронизирована':'Обложка хранится только на этом устройстве'
})
async function inspect(){try{await cloud.inspectCover(props.projectId)}catch{failed.value=true}}
async function act(publish:boolean){
 if(pending.value||cloud.busy)return
 pending.value=true;failed.value=false
 try{if(publish)await cloud.beginCover(props.projectId);else await cloud.retry();await inspect()}
 catch{failed.value=true;await inspect()}finally{pending.value=false}
}
onMounted(inspect)
const unsubscribe=onDataChange(scope=>{if(scope==='projects')void inspect()})
onUnmounted(unsubscribe)
watch(()=>cloud.busy,value=>{if(!value)void inspect()})
</script>
<template>
 <section :aria-label="t('Обложка в облаке')" class="cover-authority">
  <h4>{{t('Обложка в облаке')}}</h4>
  <p role="status">{{t(status)}}</p>
  <p>{{t('Обложка шифруется до отправки. Сервер не видит изображение.')}}</p>
  <p v-if="view?.blockers.length">{{t('Недоступная обложка временно задерживает полную синхронизацию.')}}</p>
  <p>{{t('Удаление обложки сохраняет зашифрованные изображения в истории.')}}</p>
  <button v-if="!view?.active&&view?.has_local_cover&&view?.metadata_state==='active'&&!view?.pending" class="nf-button nf-button--secondary" type="button" :disabled="pending||cloud.busy" @click="act(true)">{{t('Опубликовать обложку')}}</button>
  <button v-if="view?.pending||view?.blockers.length" class="nf-button nf-button--secondary" type="button" :disabled="pending||cloud.busy" @click="act(false)">{{t('Повторить')}}</button>
  <p v-if="failed" role="alert">{{t('Не удалось завершить синхронизацию обложки')}}</p>
 </section>
</template>
<style scoped>.cover-authority{display:grid;gap:var(--nf-space-2)}</style>
