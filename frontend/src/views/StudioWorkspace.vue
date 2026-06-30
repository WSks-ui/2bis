<template>
  <div class="studio-workspace-page">
    <aside class="studio-left-panel">
      <div class="workspace-title">
        <router-link to="/studio" class="back-link" title="返回工作区列表" aria-label="返回工作区列表">
          <ArrowLeft :size="17" />
        </router-link>
        <div>
          <input v-model.trim="workspaceNameDraft" :disabled="!workspace" @blur="saveWorkspaceName" @keydown.enter.prevent="saveWorkspaceName" />
          <span>{{ saveStateLabel }}</span>
        </div>
      </div>

      <section class="panel-block">
        <div class="panel-block-title">
          <span>工具</span>
          <small>{{ relationLabel(activeRelationType) }}</small>
        </div>
        <div class="tool-grid">
          <button type="button" title="上传图片素材" @click="openFilePicker">
            <Upload :size="17" />
            <span>图片</span>
          </button>
          <button type="button" title="添加 Prompt 节点" @click="addTextItem('prompt')">
            <TextCursorInput :size="17" />
            <span>Prompt</span>
          </button>
          <button type="button" title="添加备注节点" @click="addTextItem('note')">
            <StickyNote :size="17" />
            <span>备注</span>
          </button>
        </div>
        <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="handleFileUpload" />
      </section>

      <section class="panel-block">
        <div class="panel-block-title">
          <span>画布生成</span>
          <small>{{ activeTaskIds.size }} 个任务</small>
        </div>
        <div class="generation-panel">
          <textarea
            v-model.trim="generationPrompt"
            class="generation-prompt"
            placeholder="描述要生成或修改的画面"
          ></textarea>
          <div class="generation-row">
            <select v-model="generationMode" title="生成模式">
              <option value="text2img">文生图</option>
              <option value="ref2img">参考生成</option>
              <option value="edit">编辑图片</option>
            </select>
            <select v-model="generationQuality" title="质量">
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
          </div>
          <select v-model="generationSize" title="尺寸">
            <option value="1024x1024">1:1 1024</option>
            <option value="1344x768">16:9 轻量</option>
            <option value="1152x1536">3:4 轻量</option>
            <option value="896x1152">3:4 平台</option>
            <option value="720x1280">9:16 轻量</option>
          </select>
          <div class="generation-source-list">
            <span v-if="!generationSourceItems.length">未选择源节点</span>
            <button
              v-for="item in generationSourceItems"
              :key="item.id"
              type="button"
              :title="item.title || item.item_type"
              @click="removeGenerationSource(item.id)"
            >
              {{ sourceItemLabel(item) }}
            </button>
          </div>
          <div class="generation-actions">
            <button type="button" class="panel-mini-button" :disabled="!selectedNodeId" @click="useSelectedNodeForGeneration">
              <MousePointer2 :size="13" />
              <span>使用选中节点</span>
            </button>
            <button type="button" class="generate-button" :disabled="generationSubmitting" @click="startStudioGeneration">
              <WandSparkles :size="15" />
              <span>{{ generationSubmitting ? '提交中' : '生成' }}</span>
            </button>
          </div>
        </div>
      </section>

      <section class="panel-block">
        <div class="panel-block-title">
          <span>连线语义</span>
          <small>从节点拖出连线</small>
        </div>
        <div class="relation-list">
          <button
            v-for="item in relationTypes"
            :key="item.value"
            type="button"
            :class="{ active: activeRelationType === item.value }"
            @click="activeRelationType = item.value"
          >
            <span>{{ item.label }}</span>
            <small>{{ item.hint }}</small>
          </button>
        </div>
      </section>

      <section class="panel-block">
        <div class="panel-block-title">
          <span>历史导入</span>
          <button class="panel-mini-button" type="button" :disabled="historyLoading" @click="loadRecentHistory">
            <RefreshCw :size="13" />
            <span>{{ historyLoading ? '同步中' : '最近作品' }}</span>
          </button>
        </div>
        <div v-if="!historyRecords.length" class="history-import-empty">
          <ArchiveRestore :size="18" />
          <span>同步最近历史后可一键放入画布</span>
        </div>
        <div v-else class="history-import-list">
          <button
            v-for="record in historyRecords"
            :key="record.id"
            type="button"
            class="history-import-row"
            :disabled="!record.image_url"
            @click="importHistoryRecord(record)"
          >
            <img v-if="record.thumbnail_url || record.image_url" :src="record.thumbnail_url || record.image_url" :alt="record.prompt" />
            <span>
              <strong>{{ record.prompt }}</strong>
              <small>{{ record.workflow_type }} / {{ record.quality }}</small>
            </span>
          </button>
        </div>
      </section>

      <section class="panel-block panel-block--grow">
        <div class="panel-block-title">
          <span>素材</span>
          <small>{{ assets.length }}</small>
        </div>
        <div v-if="!assets.length" class="asset-empty">
          <ImageIcon :size="22" />
          <span>上传图片或从历史导入后会显示在这里</span>
        </div>
        <div v-else class="asset-list">
          <button v-for="asset in assets" :key="asset.id" type="button" class="asset-row" @click="placeAsset(asset)">
            <img v-if="asset.thumbnail_url || asset.url" :src="asset.thumbnail_url || asset.url" :alt="asset.title || '素材'" />
            <span v-else class="asset-thumb-placeholder"><ImageIcon :size="16" /></span>
            <span>
              <strong>{{ asset.title || '未命名素材' }}</strong>
              <small>{{ asset.source_type }}</small>
            </span>
          </button>
        </div>
      </section>
    </aside>

    <main class="studio-canvas-shell">
      <header class="canvas-topbar">
        <div>
          <strong>{{ workspace?.name || 'Studio 工作区' }}</strong>
          <span>{{ nodes.length }} 节点 / {{ edges.length }} 关系</span>
        </div>
        <div class="canvas-actions">
          <button type="button" title="重新载入画布" @click="loadCanvas">
            <RefreshCw :size="16" />
          </button>
          <button type="button" title="删除选中节点或连线" :disabled="!selectedNodeId && !selectedEdgeId" @click="deleteSelected">
            <Trash2 :size="16" />
          </button>
        </div>
      </header>

      <section class="flow-frame" :class="{ 'is-loading': loading }">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          class="studio-flow"
          :min-zoom="0.25"
          :max-zoom="1.8"
          :default-viewport="{ x: 80, y: 60, zoom: 0.9 }"
          :node-drag-threshold="2"
          :nodes-connectable="true"
          :edges-updatable="false"
          fit-view-on-init
          @connect="handleConnect"
          @node-drag-stop="handleNodeDragStop"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
          @pane-click="clearSelection"
        >
          <template #node-image="{ data, selected }">
            <div class="studio-node image-node" :class="{ selected }">
              <Handle type="target" :position="Position.Left" />
              <Handle type="source" :position="Position.Right" />
              <div class="node-image-frame">
                <img v-if="data.item.asset?.thumbnail_url || data.item.asset?.url" :src="data.item.asset.thumbnail_url || data.item.asset.url" :alt="data.item.title || '图片素材'" />
                <ImageIcon v-else :size="28" />
              </div>
              <div class="node-caption">
                <strong>{{ data.item.title || data.item.asset?.title || '图片素材' }}</strong>
                <small>{{ data.item.asset?.source_type || 'image' }}</small>
              </div>
            </div>
          </template>

          <template #node-prompt="{ data, selected }">
            <div class="studio-node text-node prompt-node" :class="{ selected }">
              <Handle type="target" :position="Position.Left" />
              <Handle type="source" :position="Position.Right" />
              <div class="node-title">
                <TextCursorInput :size="14" />
                <strong>{{ data.item.title || 'Prompt' }}</strong>
              </div>
              <textarea
                class="nodrag nowheel"
                :value="data.item.data?.text || ''"
                placeholder="输入提示词"
                @mousedown.stop
                @wheel.stop
                @input="updateNodeTextDraft(data.item.id, $event.target.value)"
                @blur="saveNodeText(data.item.id)"
              ></textarea>
            </div>
          </template>

          <template #node-note="{ data, selected }">
            <div class="studio-node text-node note-node" :class="{ selected }">
              <Handle type="target" :position="Position.Left" />
              <Handle type="source" :position="Position.Right" />
              <div class="node-title">
                <StickyNote :size="14" />
                <strong>{{ data.item.title || '备注' }}</strong>
              </div>
              <textarea
                class="nodrag nowheel"
                :value="data.item.data?.text || ''"
                placeholder="记录素材说明"
                @mousedown.stop
                @wheel.stop
                @input="updateNodeTextDraft(data.item.id, $event.target.value)"
                @blur="saveNodeText(data.item.id)"
              ></textarea>
            </div>
          </template>

          <template #node-task="{ data, selected }">
            <div class="studio-node task-node" :class="{ selected, [`task-node--${data.item.data?.status || 'pending'}`]: true }">
              <Handle type="target" :position="Position.Left" />
              <Handle type="source" :position="Position.Right" />
              <div class="task-node-header">
                <LoaderCircle v-if="isTaskActive(data.item.data?.status)" :size="15" class="spin" />
                <WandSparkles v-else :size="15" />
                <strong>{{ data.item.title || '生成任务' }}</strong>
              </div>
              <p>{{ data.item.data?.prompt || '等待生成' }}</p>
              <div class="task-node-meta">
                <span>{{ taskStatusLabel(data.item.data?.status) }}</span>
                <span>{{ data.item.data?.mode || 'text2img' }}</span>
              </div>
            </div>
          </template>
        </VueFlow>

        <div v-if="loading" class="canvas-loading">
          <LoaderCircle :size="24" class="spin" />
          <span>正在载入画布</span>
        </div>

        <div v-else-if="!nodes.length" class="canvas-empty">
          <PanelTop :size="28" />
          <strong>从左侧添加素材或 Prompt</strong>
          <span>拖动节点排布内容，从节点边缘拖出连线建立语义关系。</span>
        </div>
      </section>
    </main>

    <aside class="studio-inspector-panel">
      <section v-if="selectedItem" class="inspector-section">
        <div class="inspector-title">
          <span>检查器</span>
          <small>{{ itemTypeLabel(selectedItem.item_type) }}</small>
        </div>

        <div v-if="selectedItem.item_type === 'image'" class="inspector-preview">
          <img
            v-if="selectedItem.asset?.thumbnail_url || selectedItem.asset?.url"
            :src="selectedItem.asset.thumbnail_url || selectedItem.asset.url"
            :alt="selectedItem.title || selectedItem.asset?.title || '图片素材'"
          />
          <ImageIcon v-else :size="26" />
        </div>

        <label class="inspector-field">
          <span>节点标题</span>
          <input
            :value="selectedItem.title || ''"
            placeholder="给这个节点命名"
            @input="updateNodeTitleDraft(selectedItem.id, $event.target.value)"
            @blur="saveNodeTitle(selectedItem.id)"
            @keydown.enter.prevent="saveNodeTitle(selectedItem.id)"
          />
        </label>

        <label v-if="selectedItem.item_type === 'prompt' || selectedItem.item_type === 'note'" class="inspector-field">
          <span>{{ selectedItem.item_type === 'prompt' ? 'Prompt 内容' : '备注内容' }}</span>
          <textarea
            :value="selectedItem.data?.text || ''"
            placeholder="记录提示词、修改方向或素材说明"
            @input="updateNodeTextDraft(selectedItem.id, $event.target.value)"
            @blur="saveNodeText(selectedItem.id)"
          ></textarea>
        </label>

        <div v-if="selectedItem.item_type === 'task'" class="inspector-meta">
          <span>
            <strong>状态</strong>
            {{ taskStatusLabel(selectedItem.data?.status) }}
          </span>
          <span>
            <strong>模式</strong>
            {{ generationModeLabel(selectedItem.data?.mode) }}
          </span>
          <span v-if="selectedItem.data?.error_message">
            <strong>错误</strong>
            {{ selectedItem.data.error_message }}
          </span>
        </div>

        <div v-if="selectedItem.item_type === 'image' && selectedItem.asset" class="inspector-meta">
          <span>
            <strong>素材</strong>
            {{ selectedItem.asset.title || `#${selectedItem.asset.id}` }}
          </span>
          <span>
            <strong>来源</strong>
            {{ assetSourceLabel(selectedItem.asset.source_type) }}
          </span>
          <span v-if="selectedItem.asset.width && selectedItem.asset.height">
            <strong>尺寸</strong>
            {{ selectedItem.asset.width }} x {{ selectedItem.asset.height }}
          </span>
          <a v-if="selectedItem.asset.url" :href="selectedItem.asset.url" target="_blank" rel="noreferrer">
            <ExternalLink :size="13" />
            <span>打开原图</span>
          </a>
        </div>

        <div class="inspector-actions">
          <button type="button" class="inspector-action" :disabled="!selectedNodeCanBeGenerationSource" @click="useSelectedNodeForGeneration">
            <MousePointer2 :size="14" />
            <span>设为生成源</span>
          </button>
          <button type="button" class="inspector-action" :disabled="!selectedPromptCandidate" @click="fillPromptFromSelected">
            <TextCursorInput :size="14" />
            <span>填入提示词</span>
          </button>
          <button type="button" class="inspector-action" :disabled="selectedItem.item_type !== 'image'" @click="startRefFromSelectedImage">
            <ImagePlus :size="14" />
            <span>参考生成</span>
          </button>
          <button type="button" class="inspector-action" :disabled="selectedItem.item_type !== 'image'" @click="startEditFromSelectedImage">
            <SquarePen :size="14" />
            <span>基于此图编辑</span>
          </button>
          <button type="button" class="inspector-action" :disabled="selectedItem.item_type !== 'image'" @click="openLocalEditDialog">
            <WandSparkles :size="14" />
            <span>局部修改</span>
          </button>
          <button type="button" class="inspector-action" :disabled="!relatedImageSources.length" @click="useRelatedImagesForGeneration">
            <Link2 :size="14" />
            <span>使用关联图片</span>
          </button>
        </div>

        <div v-if="relatedImageSources.length" class="related-source-list">
          <span>关联图片</span>
          <button v-for="item in relatedImageSources" :key="item.id" type="button" @click="addGenerationSource(item)">
            {{ sourceItemLabel(item) }}
          </button>
        </div>
      </section>

      <section v-else-if="selectedRelation" class="inspector-section">
        <div class="inspector-title">
          <span>关系</span>
          <small>{{ relationLabel(selectedRelation.relation_type) }}</small>
        </div>

        <div class="relation-endpoints">
          <span>{{ relationEndpointLabel(selectedRelation.source_item_id) }}</span>
          <Link2 :size="15" />
          <span>{{ relationEndpointLabel(selectedRelation.target_item_id) }}</span>
        </div>

        <label class="inspector-field">
          <span>关系类型</span>
          <select :value="selectedRelation.relation_type" @change="saveSelectedRelationType($event.target.value)">
            <option v-for="item in relationTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>

        <label class="inspector-field">
          <span>显示标签</span>
          <input
            :value="selectedRelation.label || ''"
            placeholder="默认使用关系类型"
            @input="updateRelationLabelDraft(selectedRelation.id, $event.target.value)"
            @blur="saveRelationLabel(selectedRelation.id)"
            @keydown.enter.prevent="saveRelationLabel(selectedRelation.id)"
          />
        </label>

        <label class="inspector-field">
          <span>强度 {{ Number(selectedRelation.strength || 1).toFixed(1) }}</span>
          <input
            type="range"
            min="0.1"
            max="2"
            step="0.1"
            :value="selectedRelation.strength || 1"
            @input="updateRelationStrengthLocal(selectedRelation.id, $event.target.value)"
            @change="saveRelationStrength(selectedRelation.id)"
          />
        </label>

        <button type="button" class="inspector-danger" @click="deleteSelected">
          <Trash2 :size="14" />
          <span>删除关系</span>
        </button>
      </section>

      <section v-else class="inspector-empty">
        <PanelTop :size="24" />
        <strong>选择画布对象</strong>
        <span>选中图片、Prompt、任务或连线后，可在这里编辑属性并调用生成工具。</span>
      </section>
    </aside>

    <LocalImageEditDialog
      :open="localEditOpen"
      :item="localEditItem"
      :busy="localEditSubmitting"
      @close="closeLocalEditDialog"
      @submit="submitLocalEdit"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Handle, MarkerType, Position, VueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import {
  ArrowLeft,
  ArchiveRestore,
  ExternalLink,
  Image as ImageIcon,
  ImagePlus,
  Link2,
  LoaderCircle,
  MousePointer2,
  PanelTop,
  RefreshCw,
  SquarePen,
  StickyNote,
  TextCursorInput,
  Trash2,
  Upload,
  WandSparkles,
} from '@lucide/vue'
import api from '../api'
import { ElMessage } from '../services/toast'
import LocalImageEditDialog from '../components/LocalImageEditDialog.vue'

defineOptions({ name: 'StudioWorkspace' })

const route = useRoute()
const router = useRouter()
const workspaceId = computed(() => Number(route.params.workspaceId))

const workspace = ref(null)
const workspaceNameDraft = ref('')
const assets = ref([])
const nodes = ref([])
const edges = ref([])
const revision = ref(0)
const loading = ref(true)
const saving = ref(false)
const lastSavedAt = ref(null)
const fileInput = ref(null)
const selectedNodeId = ref(null)
const selectedEdgeId = ref(null)
const textDrafts = ref({})
const titleDrafts = ref({})
const relationLabelDrafts = ref({})
const relationStrengthDrafts = ref({})
const activeRelationType = ref('style_reference')
const historyRecords = ref([])
const historyLoading = ref(false)
const generationPrompt = ref('')
const generationMode = ref('text2img')
const generationQuality = ref('low')
const generationSize = ref('1024x1024')
const generationSourceIds = ref([])
const generationSubmitting = ref(false)
const localEditOpen = ref(false)
const localEditItem = ref(null)
const localEditSubmitting = ref(false)
const activeTaskIds = ref(new Set())
let taskPollTimer = null

const generationSourceItems = computed(() => {
  const byId = new Map(nodes.value.map(node => [Number(node.id), node.data.item]))
  return generationSourceIds.value.map(id => byId.get(id)).filter(Boolean)
})

const selectedNode = computed(() => getSelectedNode())
const selectedItem = computed(() => selectedNode.value?.data?.item || null)
const selectedRelationEdge = computed(() => {
  if (!selectedEdgeId.value) return null
  return edges.value.find(edge => edge.id === selectedEdgeId.value) || null
})
const selectedRelation = computed(() => selectedRelationEdge.value?.data?.relation || null)
const selectedNodeCanBeGenerationSource = computed(() => ['image', 'prompt', 'note'].includes(selectedItem.value?.item_type))
const selectedPromptCandidate = computed(() => ['prompt', 'note', 'task'].includes(selectedItem.value?.item_type))
const relatedImageSources = computed(() => {
  if (!selectedItem.value) return []
  const selectedId = Number(selectedItem.value.id)
  const byId = new Map(nodes.value.map(node => [Number(node.id), node.data.item]))
  const sourceIds = []

  for (const edge of edges.value) {
    const relation = edge.data?.relation
    if (!relation) continue
    if (Number(relation.target_item_id) === selectedId) {
      sourceIds.push(Number(relation.source_item_id))
    } else if (Number(relation.source_item_id) === selectedId) {
      sourceIds.push(Number(relation.target_item_id))
    }
  }

  return [...new Set(sourceIds)]
    .map(id => byId.get(id))
    .filter(item => item?.item_type === 'image')
})

const relationTypes = [
  { value: 'style_reference', label: '风格参考', hint: 'A 的风格影响 B' },
  { value: 'character_reference', label: '角色参考', hint: '保持角色一致' },
  { value: 'composition_reference', label: '构图参考', hint: '沿用布局结构' },
  { value: 'variant_of', label: '变体来源', hint: 'B 是 A 的变体' },
  { value: 'edit_source', label: '编辑来源', hint: 'B 基于 A 编辑' },
  { value: 'note_for', label: '备注说明', hint: 'A 说明 B' },
  { value: 'same_series', label: '同一系列', hint: '归入同组探索' },
]

const saveStateLabel = computed(() => {
  if (!workspace.value) return '未载入'
  if (saving.value) return '保存中'
  if (lastSavedAt.value) return `已保存 ${formatClock(lastSavedAt.value)}`
  return `修订 ${revision.value}`
})

onMounted(() => {
  loadCanvas()
  taskPollTimer = window.setInterval(pollActiveTasks, 3000)
})

onBeforeUnmount(() => {
  if (taskPollTimer) {
    window.clearInterval(taskPollTimer)
    taskPollTimer = null
  }
})

async function loadCanvas() {
  if (!Number.isFinite(workspaceId.value)) {
    await router.replace('/studio')
    return
  }
  loading.value = true
  try {
    const res = await api.get(`/workspaces/${workspaceId.value}/canvas`)
    workspace.value = res.data.workspace
    workspaceNameDraft.value = res.data.workspace.name
    revision.value = res.data.revision
    assets.value = res.data.assets || []
    nodes.value = (res.data.items || []).map(itemToNode)
    edges.value = (res.data.relations || []).map(relationToEdge)
    syncActiveTasksFromNodes()
    lastSavedAt.value = new Date()
    await nextTick()
  } catch (error) {
    if (error.response?.status === 404) {
      ElMessage.error('工作区不存在或已删除')
      await router.replace('/studio')
      return
    }
    ElMessage.error('画布加载失败')
  } finally {
    loading.value = false
  }
}

function itemToNode(item) {
  const typeMap = {
    image: 'image',
    prompt: 'prompt',
    task: 'task',
  }
  return {
    id: String(item.id),
    type: typeMap[item.item_type] || 'note',
    position: { x: item.x, y: item.y },
    dimensions: { width: item.width, height: item.height },
    draggable: !item.locked,
    selectable: true,
    data: { item },
    style: {
      width: `${item.width}px`,
      height: `${item.height}px`,
      zIndex: item.z_index,
    },
  }
}

function relationToEdge(relation) {
  return {
    id: String(relation.id),
    source: String(relation.source_item_id),
    target: String(relation.target_item_id),
    label: relation.label || relationLabel(relation.relation_type),
    markerEnd: MarkerType.ArrowClosed,
    type: 'smoothstep',
    data: { relation },
    style: { stroke: relationColor(relation.relation_type), strokeWidth: Math.max(1, Math.round((relation.strength || 1) * 2)) },
    labelStyle: {
      fill: '#181818',
      fontWeight: 800,
      fontSize: 11,
    },
    labelBgStyle: {
      fill: '#ffffff',
      fillOpacity: 0.84,
    },
  }
}

function relationLabel(value) {
  return relationTypes.find(item => item.value === value)?.label || value
}

function relationColor(value) {
  const colors = {
    style_reference: '#3c6ee8',
    character_reference: '#3f8c68',
    composition_reference: '#8b5cf6',
    variant_of: '#d8a15f',
    edit_source: '#c84d3c',
    note_for: '#6f746f',
    same_series: '#171717',
  }
  return colors[value] || '#3c6ee8'
}

function getSelectedNode() {
  if (!selectedNodeId.value) return null
  return nodes.value.find(node => node.id === selectedNodeId.value) || null
}

function isTaskActive(status) {
  return !['success', 'failed', 'refunded'].includes(status || 'pending')
}

function taskStatusLabel(status) {
  const labels = {
    pending: '排队中',
    processing: '生成中',
    success: '已完成',
    failed: '失败',
    refunded: '已退款',
  }
  return labels[status || 'pending'] || status
}

function sourceItemLabel(item) {
  if (item.item_type === 'image') return item.title || item.asset?.title || `图片 #${item.id}`
  if (item.item_type === 'prompt') return item.title || `Prompt #${item.id}`
  return item.title || `${item.item_type} #${item.id}`
}

function itemTypeLabel(value) {
  const labels = {
    image: '图片',
    prompt: 'Prompt',
    note: '备注',
    task: '任务',
  }
  return labels[value] || value || '对象'
}

function generationModeLabel(value) {
  const labels = {
    text2img: '文生图',
    ref2img: '参考生成',
    edit: '编辑图片',
  }
  return labels[value] || value || '文生图'
}

function assetSourceLabel(value) {
  const labels = {
    upload: '上传',
    history_import: '历史导入',
    studio_generation: 'Studio 生成',
  }
  return labels[value] || value || '未知'
}

function syncActiveTasksFromNodes() {
  const next = new Set(activeTaskIds.value)
  for (const node of nodes.value) {
    const item = node.data.item
    if (item.item_type === 'task' && item.task_id && isTaskActive(item.data?.status)) {
      next.add(Number(item.task_id))
    }
  }
  activeTaskIds.value = next
}

function useSelectedNodeForGeneration() {
  const node = getSelectedNode()
  if (!node) return
  const item = node.data.item
  if (!['image', 'prompt', 'note'].includes(item.item_type)) {
    ElMessage.warning('请选择图片、Prompt 或备注节点')
    return
  }
  addGenerationSource(item)
  if (item.item_type === 'prompt' || item.item_type === 'note') {
    const text = item.data?.text || ''
    if (text && !generationPrompt.value) {
      generationPrompt.value = text
    }
  }
}

function addGenerationSource(item) {
  if (!item || !['image', 'prompt', 'note'].includes(item.item_type)) return
  if (!generationSourceIds.value.includes(item.id)) {
    generationSourceIds.value = [...generationSourceIds.value, item.id]
  }
}

function selectedPromptText() {
  const item = selectedItem.value
  if (!item) return ''
  if (item.item_type === 'prompt' || item.item_type === 'note') return item.data?.text || ''
  if (item.item_type === 'task') return item.data?.prompt || ''
  return item.asset?.metadata?.prompt || item.data?.prompt || ''
}

function fillPromptFromSelected() {
  const text = selectedPromptText()
  if (!text) {
    ElMessage.warning('当前对象没有可复用的提示词')
    return
  }
  generationPrompt.value = text
  if (selectedItem.value && ['prompt', 'note'].includes(selectedItem.value.item_type)) {
    addGenerationSource(selectedItem.value)
  }
}

function startRefFromSelectedImage() {
  if (selectedItem.value?.item_type !== 'image') return
  generationMode.value = 'ref2img'
  generationSourceIds.value = [selectedItem.value.id]
}

function startEditFromSelectedImage() {
  if (selectedItem.value?.item_type !== 'image') return
  generationMode.value = 'edit'
  generationSourceIds.value = [selectedItem.value.id]
}

function openLocalEditDialog() {
  if (selectedItem.value?.item_type !== 'image') return
  localEditItem.value = selectedItem.value
  localEditOpen.value = true
}

function closeLocalEditDialog() {
  if (localEditSubmitting.value) return
  localEditOpen.value = false
  localEditItem.value = null
}

async function submitLocalEdit(payload) {
  if (localEditSubmitting.value || !payload?.item || !payload.maskBlob) return
  const sourceNode = nodes.value.find(node => Number(node.id) === Number(payload.item.id))
  const formData = new FormData()
  formData.append('source_item_id', String(payload.item.id))
  formData.append('prompt', payload.prompt)
  formData.append('quality', payload.quality || 'low')
  formData.append('mask', payload.maskBlob, `local-edit-mask-${payload.item.id}.png`)
  formData.append('x', String(Math.round((sourceNode?.position?.x || payload.item.x || 0) + 320)))
  formData.append('y', String(Math.round(sourceNode?.position?.y || payload.item.y || 0)))

  localEditSubmitting.value = true
  saving.value = true
  try {
    const res = await api.post(`/workspaces/${workspaceId.value}/local-edit`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    upsertNode(res.data.item)
    revision.value = res.data.revision
    activeTaskIds.value = new Set([...activeTaskIds.value, Number(res.data.task.id)])
    selectedNodeId.value = String(res.data.item.id)
    selectedEdgeId.value = null
    lastSavedAt.value = new Date()
    localEditOpen.value = false
    localEditItem.value = null
    ElMessage.success('局部修改任务已放入画布')
    pollActiveTasks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '局部修改任务提交失败')
  } finally {
    localEditSubmitting.value = false
    saving.value = false
  }
}

function useRelatedImagesForGeneration() {
  if (!relatedImageSources.value.length) return
  const nextIds = new Set(generationSourceIds.value)
  for (const item of relatedImageSources.value) {
    nextIds.add(item.id)
  }
  if (selectedItem.value && ['prompt', 'note'].includes(selectedItem.value.item_type)) {
    nextIds.add(selectedItem.value.id)
    if (!generationPrompt.value && selectedItem.value.data?.text) {
      generationPrompt.value = selectedItem.value.data.text
    }
  }
  generationSourceIds.value = [...nextIds]
  generationMode.value = 'ref2img'
}

function removeGenerationSource(itemId) {
  generationSourceIds.value = generationSourceIds.value.filter(id => id !== itemId)
}

function generationAnchorPosition() {
  const sourceNodes = generationSourceIds.value
    .map(id => nodes.value.find(node => Number(node.id) === Number(id)))
    .filter(Boolean)
  const anchor = sourceNodes[sourceNodes.length - 1] || getSelectedNode()
  if (!anchor) {
    return { x: 180 + nodes.value.length * 28, y: 160 + nodes.value.length * 18 }
  }
  return {
    x: Math.round(anchor.position.x + 320),
    y: Math.round(anchor.position.y),
  }
}

function validateGenerationPayload() {
  if (!generationPrompt.value.trim()) {
    ElMessage.warning('请先输入提示词')
    return false
  }
  const sourceItems = generationSourceItems.value
  const imageCount = sourceItems.filter(item => item.item_type === 'image').length
  if (generationMode.value === 'ref2img' && imageCount < 1) {
    ElMessage.warning('参考生成至少需要一个图片源节点')
    return false
  }
  if (generationMode.value === 'edit' && imageCount !== 1) {
    ElMessage.warning('编辑图片需要且只能使用一个图片源节点')
    return false
  }
  return true
}

async function startStudioGeneration() {
  if (generationSubmitting.value || !validateGenerationPayload()) return
  const position = generationAnchorPosition()
  generationSubmitting.value = true
  saving.value = true
  try {
    const res = await api.post(`/workspaces/${workspaceId.value}/generate`, {
      prompt: generationPrompt.value,
      mode: generationMode.value,
      source_item_ids: generationSourceIds.value,
      quality: generationQuality.value,
      size: generationSize.value,
      x: position.x,
      y: position.y,
    })
    upsertNode(res.data.item)
    revision.value = res.data.revision
    activeTaskIds.value = new Set([...activeTaskIds.value, Number(res.data.task.id)])
    lastSavedAt.value = new Date()
    ElMessage.success('生成任务已放入画布')
    pollActiveTasks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '生成任务提交失败')
  } finally {
    generationSubmitting.value = false
    saving.value = false
  }
}

async function pollActiveTasks() {
  if (!activeTaskIds.value.size || !Number.isFinite(workspaceId.value)) return
  const nextActive = new Set(activeTaskIds.value)
  for (const taskId of activeTaskIds.value) {
    try {
      const res = await api.get(`/workspaces/${workspaceId.value}/tasks/${taskId}`)
      applyStudioTaskStatus(res.data)
      if (!isTaskActive(res.data.task?.status)) {
        nextActive.delete(taskId)
      }
    } catch (error) {
      if ([404, 401].includes(error.response?.status)) {
        nextActive.delete(taskId)
      }
    }
  }
  activeTaskIds.value = nextActive
}

function applyStudioTaskStatus(data) {
  if (data.asset) {
    upsertAsset(data.asset)
  }
  if (data.task_item) {
    upsertNode(data.task_item)
  }
  if (data.result_item) {
    upsertNode(data.result_item)
    selectedNodeId.value = String(data.result_item.id)
    selectedEdgeId.value = null
  }
  for (const relation of data.relations || []) {
    upsertEdge(relation)
  }
  if (Number.isFinite(data.revision)) {
    revision.value = data.revision
    lastSavedAt.value = new Date()
  }
}

function openFilePicker() {
  fileInput.value?.click()
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const formData = new FormData()
  formData.append('image', file)
  formData.append('title', file.name)
  formData.append('x', String(120 + nodes.value.length * 24))
  formData.append('y', String(100 + nodes.value.length * 18))
  formData.append('create_item', 'true')

  saving.value = true
  try {
    const res = await api.post(`/workspaces/${workspaceId.value}/assets/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    upsertAsset(res.data.asset)
    if (res.data.item) {
      upsertNode(res.data.item)
    }
    await reloadRevision()
    ElMessage.success('图片已添加到画布')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '图片上传失败')
  } finally {
    saving.value = false
  }
}

async function addTextItem(type) {
  const isPrompt = type === 'prompt'
  const data = isPrompt
    ? { text: 'cinematic lighting, detailed visual concept' }
    : { text: '记录这个素材的用途、风格或修改方向' }
  saving.value = true
  try {
    const res = await api.post(`/workspaces/${workspaceId.value}/canvas/items`, {
      item_type: type,
      title: isPrompt ? 'Prompt' : '备注',
      x: 120 + nodes.value.length * 28,
      y: 120 + nodes.value.length * 24,
      width: isPrompt ? 280 : 240,
      height: isPrompt ? 180 : 150,
      data,
    })
    upsertNode(res.data)
    await reloadRevision()
  } catch (_) {
    ElMessage.error('节点创建失败')
  } finally {
    saving.value = false
  }
}

async function placeAsset(asset) {
  saving.value = true
  try {
    const res = await api.post(`/workspaces/${workspaceId.value}/canvas/items`, {
      asset_id: asset.id,
      item_type: 'image',
      title: asset.title,
      x: 140 + nodes.value.length * 30,
      y: 120 + nodes.value.length * 20,
      width: 260,
      height: 226,
      data: { assetType: asset.asset_type },
    })
    upsertNode(res.data)
    await reloadRevision()
  } catch (_) {
    ElMessage.error('素材放置失败')
  } finally {
    saving.value = false
  }
}

async function loadRecentHistory() {
  historyLoading.value = true
  try {
    const res = await api.get('/history', {
      params: {
        page: 1,
        page_size: 8,
        range: 'all',
        workflow: 'all',
        quality: 'all',
        source: 'all',
      },
    })
    historyRecords.value = res.data?.records || []
  } catch (_) {
    ElMessage.error('历史记录同步失败')
  } finally {
    historyLoading.value = false
  }
}

async function importHistoryRecord(record) {
  if (!record.image_url) return
  saving.value = true
  try {
    const res = await api.post(`/workspaces/${workspaceId.value}/assets/import-history`, {
      history_id: record.id,
      x: 160 + nodes.value.length * 30,
      y: 140 + nodes.value.length * 20,
      create_item: true,
    })
    upsertAsset(res.data.asset)
    if (res.data.item) {
      upsertNode(res.data.item)
    }
    await reloadRevision()
    ElMessage.success('历史作品已导入画布')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '历史作品导入失败')
  } finally {
    saving.value = false
  }
}

async function handleConnect(connection) {
  if (!connection.source || !connection.target || connection.source === connection.target) return
  saving.value = true
  try {
    const res = await api.post(`/workspaces/${workspaceId.value}/canvas/relations`, {
      source_item_id: Number(connection.source),
      target_item_id: Number(connection.target),
      relation_type: activeRelationType.value,
      label: relationLabel(activeRelationType.value),
      strength: 1,
      data: {},
    })
    upsertEdge(res.data)
    await reloadRevision()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '关系创建失败')
  } finally {
    saving.value = false
  }
}

async function handleNodeDragStop(event) {
  const changed = event.nodes?.length ? event.nodes : [event.node].filter(Boolean)
  if (!changed.length) return
  saving.value = true
  try {
    const payload = {
      client_revision: revision.value,
      items: changed.map(node => ({
        id: Number(node.id),
        x: Math.round(node.position.x),
        y: Math.round(node.position.y),
      })),
    }
    const res = await api.post(`/workspaces/${workspaceId.value}/canvas/items/bulk`, payload)
    revision.value = res.data.revision
    for (const item of res.data.items || []) {
      upsertNode(item)
    }
    lastSavedAt.value = new Date()
  } catch (error) {
    if (error.response?.status === 409) {
      ElMessage.warning('画布已在别处更新，正在重新载入')
      await loadCanvas()
    } else {
      ElMessage.error('位置保存失败')
    }
  } finally {
    saving.value = false
  }
}

function handleNodeClick(event) {
  selectedNodeId.value = event.node.id
  selectedEdgeId.value = null
}

function handleEdgeClick(event) {
  selectedEdgeId.value = event.edge.id
  selectedNodeId.value = null
}

function clearSelection() {
  selectedNodeId.value = null
  selectedEdgeId.value = null
}

async function deleteSelected() {
  saving.value = true
  try {
    if (selectedNodeId.value) {
      await api.delete(`/workspaces/${workspaceId.value}/canvas/items/${selectedNodeId.value}`)
      nodes.value = nodes.value.filter(node => node.id !== selectedNodeId.value)
      edges.value = edges.value.filter(edge => edge.source !== selectedNodeId.value && edge.target !== selectedNodeId.value)
    } else if (selectedEdgeId.value) {
      await api.delete(`/workspaces/${workspaceId.value}/canvas/relations/${selectedEdgeId.value}`)
      edges.value = edges.value.filter(edge => edge.id !== selectedEdgeId.value)
    }
    clearSelection()
    await reloadRevision()
  } catch (_) {
    ElMessage.error('删除失败')
  } finally {
    saving.value = false
  }
}

function updateNodeTitleDraft(itemId, title) {
  const node = nodes.value.find(item => Number(item.id) === Number(itemId))
  if (node) {
    node.data.item.title = title
  }
  titleDrafts.value = {
    ...titleDrafts.value,
    [itemId]: title,
  }
}

async function saveNodeTitle(itemId) {
  if (!(itemId in titleDrafts.value)) return
  const node = nodes.value.find(item => Number(item.id) === Number(itemId))
  if (!node) return
  const item = node.data.item
  const title = (titleDrafts.value[itemId] || '').trim() || null
  saving.value = true
  try {
    const res = await api.patch(`/workspaces/${workspaceId.value}/canvas/items/${itemId}`, { title })
    upsertNode(res.data)
    if (item.item_type === 'image' && item.asset_id) {
      const assetRes = await api.patch(`/workspaces/${workspaceId.value}/assets/${item.asset_id}`, { title })
      upsertAsset(assetRes.data)
      upsertAssetForNodes(assetRes.data)
    }
    delete titleDrafts.value[itemId]
    await reloadRevision()
  } catch (_) {
    ElMessage.error('标题保存失败')
  } finally {
    saving.value = false
  }
}

function updateNodeTextDraft(itemId, text) {
  const node = nodes.value.find(item => Number(item.id) === Number(itemId))
  if (node) {
    // 先更新本地节点数据，避免 Vue 重新渲染时把用户正在编辑的文本回滚到旧值。
    node.data.item.data = { ...(node.data.item.data || {}), text }
  }
  textDrafts.value = {
    ...textDrafts.value,
    [itemId]: text,
  }
}

async function saveNodeText(itemId) {
  if (!(itemId in textDrafts.value)) return
  const node = nodes.value.find(item => Number(item.id) === Number(itemId))
  if (!node) return
  const text = textDrafts.value[itemId]
  const item = node.data.item
  const data = { ...(item.data || {}), text }
  saving.value = true
  try {
    const res = await api.patch(`/workspaces/${workspaceId.value}/canvas/items/${itemId}`, { data })
    upsertNode(res.data)
    delete textDrafts.value[itemId]
    await reloadRevision()
  } catch (_) {
    ElMessage.error('文本保存失败')
  } finally {
    saving.value = false
  }
}

function relationEndpointLabel(itemId) {
  const node = nodes.value.find(item => Number(item.id) === Number(itemId))
  return node ? sourceItemLabel(node.data.item) : `节点 #${itemId}`
}

function updateRelationLabelDraft(relationId, label) {
  const edge = edges.value.find(item => Number(item.id) === Number(relationId))
  if (edge?.data?.relation) {
    edge.data.relation.label = label
    edge.label = label || relationLabel(edge.data.relation.relation_type)
  }
  relationLabelDrafts.value = {
    ...relationLabelDrafts.value,
    [relationId]: label,
  }
}

async function saveRelationLabel(relationId) {
  if (!(relationId in relationLabelDrafts.value)) return
  const label = (relationLabelDrafts.value[relationId] || '').trim() || null
  await patchRelation(relationId, { label }, '关系标签保存失败')
  delete relationLabelDrafts.value[relationId]
}

async function saveSelectedRelationType(relationType) {
  if (!selectedRelation.value) return
  const label = relationLabel(relationType)
  await patchRelation(
    selectedRelation.value.id,
    {
      relation_type: relationType,
      label,
    },
    '关系类型保存失败',
  )
}

function updateRelationStrengthLocal(relationId, value) {
  const strength = Number(value)
  const edge = edges.value.find(item => Number(item.id) === Number(relationId))
  if (edge?.data?.relation && Number.isFinite(strength)) {
    edge.data.relation.strength = strength
    edge.style = {
      ...(edge.style || {}),
      strokeWidth: Math.max(1, Math.round(strength * 2)),
    }
  }
  relationStrengthDrafts.value = {
    ...relationStrengthDrafts.value,
    [relationId]: strength,
  }
}

async function saveRelationStrength(relationId) {
  if (!(relationId in relationStrengthDrafts.value)) return
  const strength = Number(relationStrengthDrafts.value[relationId])
  if (!Number.isFinite(strength)) return
  await patchRelation(relationId, { strength }, '关系强度保存失败')
  delete relationStrengthDrafts.value[relationId]
}

async function patchRelation(relationId, payload, errorMessage) {
  saving.value = true
  try {
    const res = await api.patch(`/workspaces/${workspaceId.value}/canvas/relations/${relationId}`, payload)
    upsertEdge(res.data)
    await reloadRevision()
  } catch (_) {
    ElMessage.error(errorMessage)
  } finally {
    saving.value = false
  }
}

async function saveWorkspaceName() {
  if (!workspace.value) return
  const name = workspaceNameDraft.value || '未命名工作区'
  if (name === workspace.value.name) return
  saving.value = true
  try {
    const res = await api.patch(`/workspaces/${workspaceId.value}`, { name })
    workspace.value = res.data
    workspaceNameDraft.value = res.data.name
    lastSavedAt.value = new Date()
  } catch (_) {
    workspaceNameDraft.value = workspace.value.name
    ElMessage.error('工作区名称保存失败')
  } finally {
    saving.value = false
  }
}

async function reloadRevision() {
  const res = await api.get(`/workspaces/${workspaceId.value}`)
  workspace.value = res.data
  workspaceNameDraft.value = res.data.name
  revision.value = res.data.canvas_revision
  lastSavedAt.value = new Date()
}

function upsertAsset(asset) {
  const index = assets.value.findIndex(item => item.id === asset.id)
  if (index >= 0) assets.value.splice(index, 1, asset)
  else assets.value.unshift(asset)
}

function upsertAssetForNodes(asset) {
  for (const node of nodes.value) {
    if (Number(node.data.item.asset_id) === Number(asset.id)) {
      node.data.item.asset = asset
    }
  }
}

function upsertNode(item) {
  const nextNode = itemToNode(item)
  const index = nodes.value.findIndex(node => node.id === nextNode.id)
  if (index >= 0) nodes.value.splice(index, 1, nextNode)
  else nodes.value.push(nextNode)
}

function upsertEdge(relation) {
  const nextEdge = relationToEdge(relation)
  const index = edges.value.findIndex(edge => edge.id === nextEdge.id)
  if (index >= 0) edges.value.splice(index, 1, nextEdge)
  else edges.value.push(nextEdge)
}

function formatClock(date) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>

<style scoped>
.studio-workspace-page {
  height: calc(100vh - 69px);
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 300px;
  background: #f3f4ef;
  overflow: hidden;
}

.studio-left-panel,
.studio-inspector-panel {
  min-width: 0;
  height: 100%;
  padding: 16px;
  background: rgba(251, 251, 248, 0.94);
  overflow: hidden;
}

.studio-left-panel {
  display: grid;
  grid-template-rows: auto auto auto auto auto minmax(0, 1fr);
  gap: 14px;
  border-right: 1px solid var(--color-line-strong);
}

.studio-inspector-panel {
  display: grid;
  align-content: start;
  border-left: 1px solid var(--color-line-strong);
  overflow: auto;
}

.workspace-title {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.back-link,
.canvas-actions button,
.tool-grid button,
.generate-button {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  transition: background var(--transition-base), border-color var(--transition-base), transform var(--transition-base);
}

.back-link {
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.back-link:hover,
.canvas-actions button:hover:not(:disabled),
.tool-grid button:hover,
.generate-button:hover:not(:disabled) {
  border-color: var(--color-line-strong);
  background: var(--color-paper-soft);
  transform: translateY(-1px);
}

.workspace-title input {
  width: 100%;
  height: 28px;
  border: 0;
  background: transparent;
  color: var(--color-ink);
  outline: none;
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 900;
}

.workspace-title span,
.panel-block-title small,
.asset-row small,
.canvas-topbar span {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 700;
}

.panel-block {
  min-width: 0;
  display: grid;
  gap: 10px;
  align-content: start;
}

.panel-block--grow {
  min-height: 0;
}

.panel-block-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-mini-button {
  min-height: 26px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xs);
  background: #fff;
  color: var(--color-muted);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 900;
}

.panel-mini-button:disabled {
  opacity: 0.5;
  cursor: default;
}

.panel-block-title span {
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 900;
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.tool-grid button {
  min-width: 0;
  height: 58px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 4px;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
}

.generation-panel {
  display: grid;
  gap: 8px;
}

.generation-prompt {
  width: 100%;
  min-height: 78px;
  resize: vertical;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  outline: none;
  padding: 10px;
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.45;
}

.generation-row {
  display: grid;
  grid-template-columns: 1fr 0.72fr;
  gap: 8px;
}

.generation-panel select {
  min-width: 0;
  height: 34px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  padding: 0 9px;
  outline: none;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.generation-source-list {
  min-height: 32px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.generation-source-list span {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 700;
}

.generation-source-list button {
  max-width: 100%;
  min-height: 26px;
  border: 1px solid rgba(60, 110, 232, 0.24);
  border-radius: var(--radius-xs);
  background: rgba(60, 110, 232, 0.08);
  color: var(--color-ink);
  padding: 0 8px;
  cursor: pointer;
  overflow: hidden;
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generation-actions {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.generate-button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 12px;
  background: var(--color-ink);
  color: #fff;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
}

.generate-button:disabled {
  opacity: 0.5;
  cursor: default;
}

.relation-list {
  display: grid;
  gap: 6px;
}

.relation-list button {
  min-height: 48px;
  padding: 8px 10px;
  display: grid;
  gap: 2px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  text-align: left;
}

.relation-list button.active {
  border-color: rgba(60, 110, 232, 0.38);
  background: rgba(60, 110, 232, 0.08);
}

.relation-list span {
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
}

.relation-list small {
  overflow: hidden;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-list {
  min-height: 0;
  display: grid;
  gap: 8px;
  overflow: auto;
}

.history-import-list {
  max-height: 168px;
  display: grid;
  gap: 6px;
  overflow: auto;
}

.history-import-row {
  min-width: 0;
  min-height: 52px;
  padding: 6px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  text-align: left;
}

.history-import-row:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.history-import-row img {
  width: 42px;
  height: 40px;
  border-radius: var(--radius-xs);
  object-fit: cover;
  background: var(--color-paper-soft);
}

.history-import-row strong {
  display: block;
  overflow: hidden;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-import-row small {
  display: block;
  overflow: hidden;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-row {
  min-width: 0;
  min-height: 64px;
  padding: 8px;
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  text-align: left;
}

.asset-row img,
.asset-thumb-placeholder {
  width: 50px;
  height: 48px;
  border-radius: var(--radius-xs);
  object-fit: cover;
  background: var(--color-paper-soft);
}

.asset-thumb-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-muted);
}

.asset-row strong {
  display: block;
  overflow: hidden;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-empty,
.history-import-empty {
  min-height: 130px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  border: 1px dashed var(--color-line-strong);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  text-align: center;
  font-family: var(--font-ui);
  font-size: 12px;
}

.history-import-empty {
  min-height: 72px;
  grid-template-columns: auto minmax(0, 1fr);
  align-content: center;
  text-align: left;
  padding: 12px;
}

.inspector-section,
.inspector-empty {
  min-width: 0;
  display: grid;
  gap: 12px;
}

.inspector-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.inspector-title span {
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 900;
}

.inspector-title small {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.inspector-preview {
  height: 184px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: var(--color-paper-soft);
  color: var(--color-muted);
}

.inspector-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.inspector-field {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.inspector-field span,
.related-source-list > span {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 900;
}

.inspector-field input,
.inspector-field select,
.inspector-field textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  outline: none;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 700;
}

.inspector-field input,
.inspector-field select {
  height: 34px;
  padding: 0 9px;
}

.inspector-field textarea {
  min-height: 126px;
  resize: vertical;
  padding: 9px;
  line-height: 1.5;
}

.inspector-field input[type='range'] {
  height: 28px;
  padding: 0;
}

.inspector-meta {
  display: grid;
  gap: 7px;
  padding: 10px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.72);
}

.inspector-meta span,
.inspector-meta a {
  min-width: 0;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.inspector-meta strong {
  flex: 0 0 auto;
  color: var(--color-ink);
  font-weight: 900;
}

.inspector-meta a {
  justify-content: flex-start;
  align-items: center;
  color: var(--color-blue);
  font-weight: 900;
}

.inspector-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.inspector-action,
.inspector-danger {
  min-width: 0;
  min-height: 34px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
}

.inspector-action:disabled {
  opacity: 0.48;
  cursor: default;
}

.inspector-danger {
  border-color: rgba(200, 77, 60, 0.24);
  color: #c84d3c;
}

.related-source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.related-source-list > span {
  flex: 0 0 100%;
}

.related-source-list button {
  min-width: 0;
  min-height: 26px;
  max-width: 100%;
  overflow: hidden;
  border: 1px solid rgba(60, 110, 232, 0.24);
  border-radius: var(--radius-xs);
  background: rgba(60, 110, 232, 0.08);
  color: var(--color-ink);
  padding: 0 8px;
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.relation-endpoints {
  min-width: 0;
  padding: 10px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.72);
}

.relation-endpoints span {
  overflow: hidden;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inspector-empty {
  place-items: center;
  align-content: center;
  min-height: 220px;
  border: 1px dashed var(--color-line-strong);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  text-align: center;
  padding: 20px;
}

.inspector-empty strong {
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 14px;
}

.inspector-empty span {
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.5;
}

.studio-canvas-shell {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: 58px minmax(0, 1fr);
}

.canvas-topbar {
  min-width: 0;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--color-line-strong);
  background: rgba(255, 255, 255, 0.86);
}

.canvas-topbar strong {
  display: block;
  overflow: hidden;
  max-width: 52vw;
  font-family: var(--font-ui);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-actions {
  display: inline-flex;
  gap: 8px;
}

.canvas-actions button {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.canvas-actions button:disabled {
  opacity: 0.42;
  cursor: default;
}

.flow-frame {
  position: relative;
  min-width: 0;
  min-height: 0;
}

.studio-flow {
  width: 100%;
  height: 100%;
  background:
    linear-gradient(90deg, rgba(23, 23, 23, 0.05) 1px, transparent 1px),
    linear-gradient(180deg, rgba(23, 23, 23, 0.05) 1px, transparent 1px),
    #f8f8f5;
  background-size: 36px 36px;
}

.studio-node {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 1px solid rgba(23, 23, 23, 0.12);
  border-radius: var(--radius-sm);
  background: #fff;
  box-shadow: 0 8px 22px rgba(23, 23, 23, 0.08);
}

.studio-node.selected {
  border-color: rgba(60, 110, 232, 0.72);
  box-shadow: 0 0 0 3px rgba(60, 110, 232, 0.14), 0 10px 26px rgba(23, 23, 23, 0.1);
}

.image-node {
  display: grid;
  grid-template-rows: minmax(0, 1fr) 50px;
}

.node-image-frame {
  min-height: 0;
  display: grid;
  place-items: center;
  background: var(--color-paper-soft);
  color: var(--color-muted);
}

.node-image-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.node-caption {
  min-width: 0;
  padding: 8px 10px;
  display: grid;
  gap: 1px;
}

.node-caption strong,
.node-title strong {
  overflow: hidden;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-caption small {
  overflow: hidden;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-node {
  display: grid;
  grid-template-rows: 38px minmax(0, 1fr);
}

.prompt-node {
  border-top: 3px solid var(--color-blue);
}

.note-node {
  border-top: 3px solid var(--color-orange);
}

.task-node {
  display: grid;
  grid-template-rows: 36px minmax(0, 1fr) 30px;
  border-top: 3px solid #3c6ee8;
}

.task-node--success {
  border-top-color: #3f8c68;
}

.task-node--refunded,
.task-node--failed {
  border-top-color: #c84d3c;
}

.task-node-header,
.task-node-meta {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-node-header {
  padding: 0 10px;
  border-bottom: 1px solid var(--color-line);
}

.task-node-header strong {
  overflow: hidden;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-node p {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  padding: 9px 10px;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.task-node-meta {
  justify-content: space-between;
  padding: 0 10px;
  border-top: 1px solid var(--color-line);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 800;
}

.node-title {
  min-width: 0;
  padding: 0 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--color-line);
}

.text-node textarea {
  width: 100%;
  min-width: 0;
  height: 100%;
  resize: none;
  border: 0;
  background: transparent;
  color: var(--color-ink);
  outline: none;
  padding: 10px;
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.5;
}

.canvas-loading,
.canvas-empty {
  position: absolute;
  left: 50%;
  top: 50%;
  z-index: 5;
  width: min(340px, calc(100vw - 80px));
  padding: 22px;
  display: grid;
  place-items: center;
  gap: 8px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--shadow-sm);
  color: var(--color-muted);
  text-align: center;
  transform: translate(-50%, -50%);
}

.canvas-empty strong {
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 14px;
}

.canvas-empty span,
.canvas-loading span {
  font-family: var(--font-ui);
  font-size: 12px;
}

.spin {
  animation: spin 900ms linear infinite;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  border: 2px solid #fff;
  background: var(--color-blue);
}

:deep(.vue-flow__edge.selected path) {
  stroke-width: 3;
}

:deep(.vue-flow__attribution) {
  display: none;
}

@media (max-width: 860px) {
  .studio-workspace-page {
    height: auto;
    min-height: calc(100vh - 63px);
    grid-template-columns: 1fr;
    grid-template-rows: auto 70vh auto;
    overflow: visible;
    padding-bottom: 82px;
  }

  .studio-left-panel {
    height: auto;
    max-height: none;
    border-right: 0;
    border-bottom: 1px solid var(--color-line-strong);
  }

  .studio-inspector-panel {
    height: auto;
    max-height: none;
    border-left: 0;
    border-top: 1px solid var(--color-line-strong);
    overflow: visible;
  }

  .panel-block--grow {
    max-height: 220px;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
