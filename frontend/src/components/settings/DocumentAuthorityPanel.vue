<script setup lang="ts">
import {computed,ref} from 'vue'
import {EditorContent,useEditor} from '@tiptap/vue-3'
import {createDocumentEditorExtensions} from '@/components/documents/editor/editorExtensions'
import {useCloudSessionStore} from '@/stores/cloudSession'
import {useLocaleStore} from '@/stores/locale'
import {projectsApi} from '@/api/projects'
import type {DocumentOwnerView} from '@/cloud/documentSyncRuntime'
import type {PortableDocument} from '@/cloud/documentCodec'
import FriendlyStatus from './FriendlyStatus.vue'
const props=defineProps<{projectId:string}>(),cloud=useCloudSessionStore(),locale=useLocaleStore(),t=locale.translate
const pending=ref(false),error=ref<string|null>(null),stages=ref<Array<{id:string;name:string}>>([]),targets=ref<Record<string,string>>({})
const view=computed(()=>cloud.documentAuthority[props.projectId]),preview=useEditor({extensions:createDocumentEditorExtensions(),editable:false,content:{type:'doc',content:[{type:'paragraph'}]}})
async function run(action:()=>Promise<void>){pending.value=true;error.value=null;try{await action()}catch(e){error.value=e instanceof Error?e.message:String(e)}finally{pending.value=false}}
async function inspect(publish=false){await run(async()=>{if(publish)await cloud.beginDocuments(props.projectId);else await cloud.inspectDocuments(props.projectId);stages.value=(await projectsApi.get(props.projectId)).stages.map(s=>({id:s.id,name:s.name}))})}
function show(doc:PortableDocument|null){preview.value?.commands.setContent(doc?.content_json??{type:'doc',content:[{type:'paragraph'}]})}
async function choose(owner:DocumentOwnerView,id:string){await run(()=>cloud.chooseDocumentVersion({project_id:props.projectId,document_id:owner.entity_id,expected_tips:[...owner.tips],expected_local:owner.local,selected_event_id:id}))}
const expected=(o:DocumentOwnerView)=>({document_id:o.entity_id,document:o.local,tips:[...o.tips]})
async function move(owner:DocumentOwnerView){await run(()=>cloud.moveDocument(props.projectId,owner.entity_id,targets.value[owner.entity_id]||null,expected(owner)))}
</script>
<template>
 <section class="document-authority">
  <h4>{{t('Синхронизация документов')}}</h4>
  <p>{{t('Документы публикуются по вашему действию. Файлы Word и Scrivener привязываются отдельно на каждом устройстве.')}}</p>
  <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="inspect(false)">{{t('Проверить состояние')}}</button>
  <button class="nf-button" :disabled="pending||cloud.busy" @click="inspect(true)">{{t('Опубликовать документы')}}</button>
  <FriendlyStatus v-if="view?.blocker" :code="view.blocker" subsystem="sync" />
  <article v-for="owner in view?.owners||[]" :key="owner.entity_id">
   <h5>{{(owner.local as PortableDocument|null)?.title||t(owner.state==='blocked'?'Синхронизация документов':'Документ удалён')}}</h5>
   <FriendlyStatus :code="owner.blocker||owner.state" domain="catalog" subsystem="sync" />
   <template v-if="owner.state==='conflict'">
    <p>{{t('Сохранены полные версии документа. Название, текст и область выбираются вместе.')}}</p>
    <button class="nf-button nf-button--secondary" :disabled="pending" @click="show(owner.local as PortableDocument|null)">{{t('Версия этого устройства')}}</button>
    <button class="nf-button" :disabled="pending||cloud.busy" @click="choose(owner,'local')">{{t('Оставить версию этого устройства')}}</button>
    <details v-for="version in owner.versions" :key="version.event_id">
     <summary>{{t('Сохранённая версия')}} {{version.revision}} — {{version.document?.title||t('Документ удалён')}}</summary>
     <p>{{stages.find(s=>s.id===(version.document?.stage_id??version.stage_id))?.name||((version.document?.stage_id??version.stage_id)?t('Этап'):t('Проект'))}}</p>
     <button class="nf-button nf-button--secondary" :disabled="pending" @click="show(version.document)">{{t('Просмотреть текст')}}</button>
     <button class="nf-button" :disabled="pending||cloud.busy" @click="choose(owner,version.event_id)">{{t('Использовать эту версию')}}</button>
    </details>
   </template>
   <template v-if="owner.state==='active' && owner.local">
    <label>{{t('Перенести документ')}}<select v-model="targets[owner.entity_id]"><option value="">{{t('Проект')}}</option><option v-for="stage in stages" :key="stage.id" :value="stage.id">{{stage.name}}</option></select></label>
    <button class="nf-button" :disabled="pending||cloud.busy" @click="move(owner)">{{t('Перенести документ')}}</button>
    <button class="nf-button nf-button--secondary" :disabled="pending||cloud.busy" @click="run(()=>cloud.deleteDocument(projectId,owner.entity_id,expected(owner)))">{{t('Удалить документ')}}</button>
   </template>
  </article>
  <EditorContent :editor="preview" />
  <FriendlyStatus v-if="error" :code="error" subsystem="sync" />
 </section>
</template>
<style scoped>.document-authority,article{display:grid;gap:.5rem}h4,h5,p{margin:0}select{max-width:100%}</style>
