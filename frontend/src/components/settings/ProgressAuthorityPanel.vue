<script setup lang="ts">
import {computed,ref} from 'vue'
import {useCloudSessionStore} from '@/stores/cloudSession'
import {useLocaleStore} from '@/stores/locale'
import type {ProgressOwnerView,ProgressDecision,ProgressChain} from '@/cloud/progressSyncRuntime'
import {progressMicros} from '@/cloud/progressCodec'
import FriendlyStatus from './FriendlyStatus.vue'
const props=defineProps<{projectId:string}>(),cloud=useCloudSessionStore(),t=useLocaleStore().translate
const pending=ref(false),error=ref<string|null>(null),selected=ref<Record<string,string>>({}),targets=ref<Record<string,string>>({}),corrected=ref<Record<string,string>>({})
const view=computed(()=>cloud.progressAuthority[props.projectId])
async function run(action:()=>Promise<void>){pending.value=true;error.value=null;try{await action()}catch(e){error.value=e instanceof Error?e.message:String(e)}finally{pending.value=false}}
function localChain(owner:ProgressOwnerView){return owner.local&&typeof owner.local==='object'&&'chain' in owner.local}
function chosen(owner:ProgressOwnerView){return owner.versions.find(v=>v.event_id===(selected.value[owner.entity_id]||owner.versions[0]?.event_id))}
function actions(owner:ProgressOwnerView):string[]{if(owner.versions.length!==2)return [];const keep=new Set(chosen(owner)?.chain.entries.map(f=>f.entry_id)??[]);const other=owner.versions.find(v=>v.event_id!==chosen(owner)?.event_id);return other?.chain.entries.filter(f=>!keep.has(f.entry_id)).map(f=>f.entry_id)??[]}
function total(chain:ProgressChain){return chain.entries.at(-1)?.new_total??chain.base_total}
function rebaseTotal(owner:ProgressOwnerView){const v=chosen(owner);if(!v)return '';const ids=new Set(actions(owner));let amount=progressMicros(total(v.chain));const seen=new Set<string>();for(const version of owner.versions)for(const f of version.chain.entries)if(ids.has(f.entry_id)&&!seen.has(f.entry_id)){seen.add(f.entry_id);amount+=progressMicros(f.delta)}const sign=amount<0n?'-':'';const absolute=amount<0n?-amount:amount;return `${sign}${absolute/1000000n}.${(absolute%1000000n).toString().padStart(6,'0')}`}
async function keepLocal(owner:ProgressOwnerView){await run(()=>cloud.chooseProgressHistory({project_id:props.projectId,stage_id:owner.stage_id,expected_tips:[...owner.tips],expected_local:owner.local,selected_event_id:'local',operation:'adopt_local',target_entry_id:null,rebased_from:[],corrected_delta:null}))}
async function decide(owner:ProgressOwnerView,operation:ProgressDecision['operation']){const v=chosen(owner);if(!v)return;const target=targets.value[owner.entity_id]??null;let from:string[]=[];if(operation==='rebase')from=actions(owner);if(operation==='tombstone'||operation==='correct'){const pos=v.chain.entries.findIndex(f=>f.entry_id===target);if(pos<0)return;from=v.chain.entries.slice(pos+(operation==='tombstone'?1:0)).map(f=>f.entry_id)}
  let delta:string|null=null;if(operation==='correct'){const raw=corrected.value[owner.entity_id]??'';if(!/^-?\d+(\.\d{1,6})?$/.test(raw)){error.value='progress_correction_invalid';return}const [whole,fraction='']=raw.split('.');delta=`${whole}.${fraction.padEnd(6,'0')}`}
  await run(()=>cloud.chooseProgressHistory({project_id:props.projectId,stage_id:owner.stage_id,expected_tips:[...owner.tips],expected_local:owner.local,selected_event_id:v.event_id,operation,target_entry_id:operation==='tombstone'||operation==='correct'?target:null,rebased_from:from,corrected_delta:delta}))
}
</script>
<template>
 <section class="progress-authority">
  <h4>{{t('Синхронизация истории прогресса')}}</h4>
  <p>{{t('Записи сохраняют действия и предыдущее значение. Одновременный прогресс на двух устройствах не складывается автоматически.')}}</p>
  <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="run(()=>cloud.inspectProgress(projectId))">{{t('Проверить состояние')}}</button>
  <button class="nf-button" :disabled="pending||cloud.busy" @click="run(()=>cloud.beginProgress(projectId))">{{t('Опубликовать прогресс')}}</button>
  <article v-for="owner in view?.owners||[]" :key="owner.entity_id">
   <h5>{{owner.stage_id?t('Прогресс этапа'):t('Прогресс проекта')}}</h5>
   <FriendlyStatus :code="owner.blocker||owner.state" domain="catalog" subsystem="sync" />
   <template v-if="owner.versions.length">
    <label>{{t('Выберите историю')}}<select :value="selected[owner.entity_id]||owner.versions[0]?.event_id" @change="selected[owner.entity_id]=($event.target as HTMLSelectElement).value"><option v-for="(v,index) in owner.versions" :key="v.event_id" :value="v.event_id">{{t('Сохранённая версия')}} {{index+1}} — {{total(v.chain)}} {{t('символов')}}</option></select></label>
    <ol><li v-for="f in chosen(owner)?.chain.entries||[]" :key="f.entry_id">{{f.writing_day}}: {{f.delta}} → {{f.new_total}} {{t('символов')}}</li></ol>
    <template v-if="owner.state==='conflict'">
     <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy||!localChain(owner)" @click="keepLocal(owner)">{{t('Оставить историю этого устройства')}}</button>
     <p>{{t('Истории прогресса разошлись. Выберите одну или явно перенесите действия из другой истории.')}}</p>
     <button class="nf-button" :disabled="pending||cloud.busy" @click="decide(owner,'select')">{{t('Оставить выбранную историю')}}</button>
     <ol><li v-for="id in actions(owner)" :key="id">{{owner.versions.flatMap(v=>v.chain.entries).find(f=>f.entry_id===id)?.writing_day}}: {{owner.versions.flatMap(v=>v.chain.entries).find(f=>f.entry_id===id)?.delta}} {{t('символов')}}</li></ol>
     <p v-if="owner.versions.length>2">{{t('Сначала выберите историю. Перенос действий доступен для двух веток.')}}</p>
     <p>{{t('Результат переноса действий')}}: {{rebaseTotal(owner)}} {{t('символов')}}</p>
     <button class="nf-button" :disabled="pending||cloud.busy||!actions(owner).length" @click="decide(owner,'rebase')">{{t('Перенести действия на выбранную историю')}}</button>
    </template>
    <template v-if="owner.state==='active'">
     <label>{{t('Историческая запись')}}<select v-model="targets[owner.entity_id]"><option v-for="f in chosen(owner)?.chain.entries||[]" :key="f.entry_id" :value="f.entry_id">{{f.writing_day}}: {{f.delta}} → {{f.new_total}}</option></select></label>
     <p>{{t('Последующие действия будут перенесены явно. Оригинальная история останется сохранённой.')}}</p>
     <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy||!targets[owner.entity_id]" @click="decide(owner,'tombstone')">{{t('Удалить запись и перенести последующие действия')}}</button>
     <label>{{t('Исправленная прибавка в символах')}}<input v-model="corrected[owner.entity_id]" inputmode="decimal"></label>
     <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy||!targets[owner.entity_id]" @click="decide(owner,'correct')">{{t('Исправить запись и перенести последующие действия')}}</button>
    </template>
   </template>
  </article>
  <FriendlyStatus v-if="error" :code="error" subsystem="sync" />
 </section>
</template>
<style scoped>.progress-authority,article{display:grid;gap:.5rem}h4,h5,p{margin:0}select,input{max-width:100%}ol{max-height:20rem;overflow:auto}</style>
