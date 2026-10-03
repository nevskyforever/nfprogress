<script setup lang="ts">
import {computed,ref} from 'vue'
import {useCloudSessionStore} from '@/stores/cloudSession'
import {useLocaleStore} from '@/stores/locale'
import type {MapOwnerView,MapDecision} from '@/cloud/mapSyncRuntime'
import type {MindMapResponse,JsonObject} from '@/types/notes'
import FriendlyStatus from './FriendlyStatus.vue'
import {NOTE_COLORS} from '@/components/notes/noteColors'
import MindMapEditor from '@/components/notes/MindMapEditor.vue'
const props=defineProps<{projectId:string}>(),cloud=useCloudSessionStore(),t=useLocaleStore().translate
const view=computed(()=>cloud.mapAuthority[props.projectId]),pending=ref(false),error=ref<string|null>(null)
async function action(publish:boolean){if(pending.value||cloud.busy)return;pending.value=true;error.value=null;try{if(publish)await cloud.beginMaps(props.projectId);else await cloud.inspectMaps(props.projectId)}catch(e){error.value=e instanceof Error?e.message:'unknown_error'}finally{pending.value=false}}
async function choose(owner:MapOwnerView,selected:string,keepLocal?:boolean){if(pending.value||cloud.busy)return;pending.value=true;error.value=null;const decision:MapDecision={project_id:props.projectId,stage_id:owner.stage_id,expected_tips:owner.tips,expected_local:owner.local,selected_event_id:selected};try{await cloud.chooseMapVersion(decision,keepLocal)}catch(e){error.value=e instanceof Error?e.message:'unknown_error';await cloud.inspectMaps(props.projectId)}finally{pending.value=false}}
function preview(owner:MapOwnerView,version:MapOwnerView['versions'][number]):MindMapResponse{return {project_id:props.projectId,stage_id:owner.stage_id,name:t(owner.stage_id?'Карта этапа':'Карта проекта'),data:version.map?.data as JsonObject|null,combined:false,read_only:true,has_empty_completed_stage_map:false}}
function localPreview(owner:MapOwnerView):MindMapResponse{const local=owner.local as {owner?:{mindmap?:JsonObject}};return {...preview(owner,{event_id:"local",revision:0,mutation:"upsert",map:null}),data:local.owner?.mindmap??null}}
interface AnnotationPreview {note_id:string;title:string;tags:string[];color:string;pinned:boolean;archived:boolean;created_at:string;sort_order:number;checklist:Array<{text:string;checked:boolean}>}
function annotations(version:MapOwnerView['versions'][number]):AnnotationPreview[]{return (Object.values(version.map?.annotations||{}) as AnnotationPreview[]).sort((a,b)=>a.sort_order-b.sort_order)}
function localAnnotations(owner:MapOwnerView):AnnotationPreview[]{const source=owner.local as {notes?:Array<AnnotationPreview&{id:string;source_type:string}>};return (source.notes||[]).filter(n=>n.source_type==='mindmap').map(n=>({...n,note_id:n.id})).sort((a,b)=>a.sort_order-b.sort_order)}
async function readOnly():Promise<never>{throw new Error('map_preview_read_only')}
</script>
<template>
 <section class="map-authority">
  <h4>{{t('Синхронизация карт')}}</h4>
  <p>{{t('Карты проекта и этапов публикуются только по вашему действию. Текст и оформление связанных заметок передаются вместе с картой. Объединённая карта остаётся представлением отдельных карт.')}}</p>
  <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="action(false)">{{t('Проверить состояние')}}</button>
  <button class="nf-button" :disabled="pending||cloud.busy" @click="action(true)">{{t('Опубликовать карты')}}</button>
  <article v-for="owner in view?.owners||[]" :key="owner.entity_id">
   <h5>{{t(owner.stage_id?'Карта этапа':'Карта проекта')}}</h5>
   <FriendlyStatus :code="owner.blocker||owner.state" domain="catalog" subsystem="sync" />
   <template v-if="owner.state==='conflict'">
    <p>{{t('Сохранены полные версии карты и связанных заметок. Проверьте варианты и выберите нужный.')}}</p>
    <details><summary>{{t('Карта этого устройства')}}</summary><MindMapEditor :map="localPreview(owner)" :persist="readOnly" :import-x-mind="readOnly" /><ul><li v-for="annotation in localAnnotations(owner)" :key="annotation.note_id"><strong>{{annotation.title}}</strong><p>{{t('Теги')}}: {{annotation.tags.join(', ')}}</p><p>{{t('Цвет')}}: {{t(NOTE_COLORS.find(c=>c.value===annotation.color)?.label||'Цвет')}} · {{t('Закреплено')}}: {{t(annotation.pinned?'Да':'Нет')}} · {{t('В архиве')}}: {{t(annotation.archived?'Да':'Нет')}}</p><ul><li v-for="(check,index) in annotation.checklist" :key="index">{{check.checked?'☑':'☐'}} {{check.text}}</li></ul></li></ul></details>
    <details v-for="version in owner.versions" :key="version.event_id">
     <summary>{{t('Сохранённая версия')}} {{version.revision}}</summary>
     <p v-if="version.mutation==='delete'">{{t('Карта удалена')}}</p>
     <MindMapEditor v-else :map="preview(owner,version)" :persist="readOnly" :import-x-mind="readOnly" />
     <ul v-if="version.map"><li v-for="annotation in annotations(version)" :key="annotation.note_id"><strong>{{annotation.title}}</strong>
      <p>{{t('Теги')}}: {{annotation.tags.join(', ')}}</p>
      <p>{{t('Цвет')}}: {{t(NOTE_COLORS.find(c=>c.value===annotation.color)?.label||'Цвет')}} · {{t('Закреплено')}}: {{t(annotation.pinned?'Да':'Нет')}} · {{t('В архиве')}}: {{t(annotation.archived?'Да':'Нет')}}</p>
      <p>{{t('Дата создания')}}: {{annotation.created_at}}</p><ul><li v-for="(check,index) in (annotation.checklist as Array<{text:string;checked:boolean}>)" :key="index">{{check.checked?'☑':'☐'}} {{check.text}}</li></ul></li></ul>
     <button class="nf-button" :disabled="pending||cloud.busy" @click="choose(owner,version.event_id,owner.tips.length===1?false:undefined)">{{t('Использовать эту версию')}}</button>
    </details>
    <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="choose(owner,owner.tips.length===1?owner.tips[0]!:'local',owner.tips.length===1?true:undefined)">{{t('Оставить карту этого устройства')}}</button>
   </template>
  </article>
  <FriendlyStatus v-if="error" :code="error" subsystem="sync" />
 </section>
</template>
<style scoped>.map-authority{display:grid;gap:var(--nf-space-2)}h4,p{margin:0}article{display:grid;gap:.5rem}details{min-width:0}summary{cursor:pointer}</style>
