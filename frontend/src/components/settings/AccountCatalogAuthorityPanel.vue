<script setup lang="ts">
import { projectsApi } from '@/api/projects'
import { computed,ref } from 'vue'
import FriendlyStatus from './FriendlyStatus.vue'
import { useCloudSessionStore } from '@/stores/cloudSession'
import { useLocaleStore } from '@/stores/locale'
import type { CatalogEntity } from '@/infrastructure/sqlite/accountCatalogRepository'
import type { CatalogPayload } from '@/cloud/accountCatalogCodec'
const cloud=useCloudSessionStore(),t=useLocaleStore().translate,view=computed(()=>cloud.catalogAuthority),pending=ref(false),error=ref(false)
async function action(operation:()=>Promise<unknown>){if(pending.value||cloud.busy)return;pending.value=true;error.value=false;try{await operation()}catch{error.value=true}finally{pending.value=false}}
function name(id:string):string {const f=view.value?.entities.find(e=>e.entity_type==='folder'&&e.entity_id===id);return f?.local&&'name' in f.local?f.local.name:view.value?.project_names[id]??t('Папка')}
function display(p:CatalogPayload):string{if(p===null)return t('Удалить папку');if('name' in p)return p.name;if('folder_id' in p)return p.folder_id===null?t('Без папки'):name(p.folder_id);return p.ids.map(name).join(' → ')}
function choose(e:CatalogEntity,id:string|null){return action(()=>cloud.decideCatalog({entity_type:e.entity_type,entity_id:e.entity_id,expected_tips:[...e.tips].sort(),expected_local:e.local,proposed:e.local,selected_event_id:id}))}
function moveFolder(index:number,direction:number){const order=view.value?.entities.find(e=>e.entity_type==='folder_order');if(!order?.local||!('ids' in order.local))return;const ids=[...order.local.ids],target=index+direction;if(target<0||target>=ids.length)return;[ids[index],ids[target]]=[ids[target]!,ids[index]!];return action(async()=>{await projectsApi.reorderFolders(ids);await cloud.retry();await cloud.inspectCatalog()})}
const folderOrder=computed(()=>{const p=view.value?.entities.find(e=>e.entity_type==='folder_order')?.local;return p&&'ids' in p?p.ids:[]})
const labels={folder:'Папка была изменена одновременно на нескольких устройствах',folder_order:'Порядок папок',folder_membership:'Расположение по папкам отличается',project_order:'Порядок проектов изменён на нескольких устройствах'}
</script>
<template>
<section class="catalog-authority" :data-catalog-state="view?.state">
 <h4>{{t('Структура проектов')}}</h4>
 <p>{{t('Местные проекты останутся на этом устройстве. Публикация структуры начинается только по вашему выбору.')}}</p>
 <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="action(()=>cloud.inspectCatalog())">{{t('Проверить структуру проектов')}}</button>
 <template v-if="view">
  <FriendlyStatus domain="catalog" :code="view.state" subsystem="projects" />
  <button v-if="view.state==='catalog_local'" class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="action(()=>cloud.beginCatalog())">{{t('Опубликовать структуру проектов')}}</button>
  <button v-else-if="['captured','publication_pending','self_echo_pending','blocked'].includes(view?.state??'')" class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="action(async()=>{if(view?.blockers.includes('unsupported_catalog_source')||view?.blockers.includes('catalog_resource_limit')||view?.blockers.includes('catalog_project_unproven'))await cloud.beginCatalog();else await cloud.retry();await cloud.inspectCatalog()})">{{t('Безопасно продолжить')}}</button>
  <div v-for="entity in view.entities.filter(e=>e.conflict&&e.tips.length)" :key="entity.entity_type+entity.entity_id">
   <h5>{{t(labels[entity.entity_type])}}</h5><p v-if="entity.entity_type==='folder_membership'">{{view.project_names[entity.entity_id]}}</p>
   <div v-for="branch in entity.branches" :key="branch.header.event_id"><p>{{display(branch.payload)}}</p><button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="choose(entity,branch.header.event_id)">{{t('Выбрать этот вариант')}}</button></div>
   <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="choose(entity,null)">{{t('Использовать вариант этого устройства')}}</button>
  </div>
  <div v-if="view.state==='active'"><h5>{{t('Порядок папок')}}</h5><div v-for="(id,index) in folderOrder" :key="id"><span>{{name(id)}}</span><button :disabled="pending||index===0" @click="moveFolder(index,-1)">{{t('Выше')}}</button><button :disabled="pending||index===folderOrder.length-1" @click="moveFolder(index,1)">{{t('Ниже')}}</button></div></div>
  <div v-for="entity in view.entities.filter(e=>['active','conflict'].includes(view?.state??'')&&e.entity_type==='folder'&&!e.tips.length)" :key="entity.entity_id"><p>{{display(entity.local)}}</p><button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="choose(entity,null)">{{t('Добавить папку в облачную структуру')}}</button></div>
  <FriendlyStatus v-for="blocker in view.blockers" :key="blocker" :code="blocker" subsystem="projects" />
 </template>
 <p v-if="error" role="alert">{{t('Не удалось завершить согласование. Проверьте состояние и безопасно повторите действие.')}}</p>
</section>
</template>
<style scoped>.catalog-authority{display:grid;gap:var(--nf-space-2)}p,h4,h5{margin:0}</style>
