<script setup lang="ts">
import {computed,ref} from 'vue'
import {useCloudSessionStore} from '@/stores/cloudSession'
import {useLocaleStore} from '@/stores/locale'
import type {GameOwnerView} from '@/cloud/gameSyncRuntime'
import FriendlyStatus from './FriendlyStatus.vue'
const cloud=useCloudSessionStore(),t=useLocaleStore().translate
const pending=ref(false),error=ref<string|null>(null),selected=ref<Record<string,string>>({}),reward=ref(''),confirmReversal=ref(false)
const account=computed(()=>cloud.gameAuthority?.owners.find(o=>o.owner_key==='account'))
async function run(action:()=>Promise<void>){pending.value=true;error.value=null;try{await action()}catch(e){error.value=e instanceof Error?e.message:String(e)}finally{pending.value=false}}
function amount(snapshot:unknown,key:string){if(!snapshot||typeof snapshot!=='object')return '';const value=(snapshot as Record<string,unknown>)[key];return typeof value==='string'||typeof value==='number'?value:''}
function label(owner:GameOwnerView){if(owner.owner_key==='account')return t('Игровая история аккаунта');try{return JSON.parse(owner.owner_key)[1]?t('Игровая история этапа'):t('Игровая история проекта')}catch{return t('Игровая история проекта')}}
async function choose(owner:GameOwnerView){const id=selected.value[owner.owner_key]||owner.versions[0]?.event_id;if(!id)return;await run(()=>cloud.chooseGameHistory({owner_key:owner.owner_key,expected_tips:[...owner.tips],expected_local:owner.local,selected_event_id:id}))}
async function compensate(){const owner=account.value;if(!owner||!reward.value||!confirmReversal.value)return;await run(()=>cloud.compensateGameReward({target_action_id:reward.value,expected_tips:[...owner.tips],expected_local:owner.local}));confirmReversal.value=false}
</script>
<template>
 <section class="game-authority">
  <h4>{{t('Синхронизация игрового прогресса')}}</h4>
  <p>{{t('Публикация сохраняет прежние награды без повторной выплаты. Подключённые проекты и история аккаунта передаются вместе; локальные проекты не подключаются автоматически.')}}</p>
  <div class="actions">
   <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="run(()=>cloud.inspectGame())">{{t('Проверить состояние')}}</button>
   <button class="nf-button" :disabled="pending||cloud.busy" @click="run(()=>cloud.beginGame())">{{t('Опубликовать игровой прогресс')}}</button>
  </div>
  <FriendlyStatus v-for="code in cloud.gameAuthority?.blockers||[]" :key="code" :code="code" domain="catalog" subsystem="sync" />
  <article v-for="(owner,index) in cloud.gameAuthority?.owners||[]" :key="owner.owner_key">
   <h5>{{label(owner)}} <span v-if="owner.owner_key!=='account'">{{index}}</span></h5>
   <FriendlyStatus :code="owner.blocker||(owner.state==='conflict'?'game_noncommutative_conflict':owner.state)" domain="catalog" subsystem="sync" />
   <template v-if="owner.state==='conflict'&&owner.versions.length">
    <p>{{t('Игровые действия разошлись. Выберите сохранённую историю; остальные ветки останутся в истории.')}}</p>
    <label>{{t('Выберите историю')}}<select v-model="selected[owner.owner_key]"><option v-for="(version,i) in owner.versions" :key="version.event_id" :value="version.event_id">{{t('Сохранённая версия')}} {{i+1}} <template v-if="owner.owner_key==='account'">— {{t('Монеты')}}: {{amount(version.snapshot,'coins')}}; {{t('Опыт')}}: {{amount(version.snapshot,'experience')}}</template></option></select></label>
    <button class="nf-button" :disabled="pending||cloud.busy" @click="choose(owner)">{{t('Оставить выбранную историю')}}</button>
   </template>
   <button v-if="owner.tips.length===1" class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="run(()=>cloud.rebuildGameProjection(owner.owner_key))">{{t('Восстановить игровую проекцию из истории')}}</button>
  </article>
  <template v-if="account?.state==='active'&&cloud.gameAuthority?.rewards.length">
   <label>{{t('Награда для отмены')}}<select v-model="reward"><option value="">{{t('Выберите награду')}}</option><option v-for="(item,i) in cloud.gameAuthority.rewards" :key="item.event_id" :value="item.event_id">{{i+1}} — {{item.date.slice(0,10)}}; {{t('Монеты')}}: {{item.reward.coins}}; {{t('Опыт')}}: {{item.reward.experience}}</option></select></label>
   <label><input v-model="confirmReversal" type="checkbox">{{t('Подтверждаю отмену награды отдельным действием. Оригинальная награда останется в истории.')}}</label>
   <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy||!reward||!confirmReversal" @click="compensate">{{t('Отменить выбранную награду')}}</button>
  </template>
  <div v-if="error" role="alert"><FriendlyStatus :code="error" domain="catalog" subsystem="sync" /></div>
 </section>
</template>
<style scoped>.game-authority,article{display:grid;gap:.5rem}.actions{display:flex;gap:.5rem;flex-wrap:wrap}h4,h5,p{margin:0}select{max-width:100%}</style>
