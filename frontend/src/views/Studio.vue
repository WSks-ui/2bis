<template>
  <div class="studio-index-page paper-page">
    <main class="studio-index-shell">
      <header class="studio-index-header">
        <div>
          <p class="eyebrow">2Bis Studio</p>
          <h1>工作区</h1>
          <p>用画布整理图片、提示词、备注和素材关系，把一次性生成结果沉淀成可继续迭代的创作项目。</p>
        </div>
        <form class="create-workspace" @submit.prevent="createWorkspace">
          <input v-model.trim="newWorkspaceName" maxlength="120" placeholder="新工作区名称" />
          <button class="btn-black" type="submit" :disabled="creating">
            <Plus :size="16" />
            <span>{{ creating ? '创建中' : '新建' }}</span>
          </button>
        </form>
      </header>

      <Transition name="modal-pop" mode="out-in">
      <section v-if="loading" class="workspace-state surface-card">
        <LoaderCircle :size="22" class="spin" />
        <strong>正在载入工作区</strong>
      </section>

      <section v-else-if="!workspaces.length" class="workspace-empty surface-card">
        <div class="empty-icon"><PanelTop :size="28" /></div>
        <strong>还没有 Studio 工作区</strong>
        <p>先创建一个项目，然后在画布里上传素材、放置 Prompt，并用连线标注素材之间的关系。</p>
        <button class="btn-black" type="button" :disabled="creating" @click="createWorkspace">创建默认工作区</button>
      </section>

      <section v-else class="workspace-list">
        <article v-for="workspace in workspaces" :key="workspace.id" class="workspace-row surface-card">
          <router-link class="workspace-main-link" :to="`/studio/${workspace.id}`">
            <span class="workspace-mark"><PanelsTopLeft :size="20" /></span>
            <span>
              <strong>{{ workspace.name }}</strong>
              <small>{{ workspace.description || '画布修订 ' + workspace.canvas_revision }}</small>
            </span>
          </router-link>
          <div class="workspace-meta">
            <span>{{ formatTime(workspace.updated_at) }}</span>
            <router-link :to="`/studio/${workspace.id}`">打开</router-link>
          </div>
        </article>
      </section>
      </Transition>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { LoaderCircle, PanelTop, PanelsTopLeft, Plus } from '@lucide/vue'
import api from '../api'
import { ElMessage } from '../services/toast'
import { useRouter } from 'vue-router'

defineOptions({ name: 'Studio' })

const router = useRouter()
const workspaces = ref([])
const loading = ref(true)
const creating = ref(false)
const newWorkspaceName = ref('')

onMounted(() => {
  loadWorkspaces()
})

async function loadWorkspaces() {
  loading.value = true
  try {
    const res = await api.get('/workspaces')
    workspaces.value = res.data || []
  } catch (_) {
    ElMessage.error('工作区加载失败')
  } finally {
    loading.value = false
  }
}

async function createWorkspace() {
  if (creating.value) return
  creating.value = true
  try {
    const name = newWorkspaceName.value || '未命名工作区'
    const res = await api.post('/workspaces', { name })
    newWorkspaceName.value = ''
    await router.push(`/studio/${res.data.id}`)
  } catch (_) {
    ElMessage.error('工作区创建失败')
  } finally {
    creating.value = false
  }
}

function formatTime(value) {
  if (!value) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
</script>

<style scoped>
.studio-index-page {
  min-height: calc(100vh - 69px);
}

.studio-index-shell {
  width: min(1120px, calc(100vw - 40px));
  margin: 0 auto;
  padding: 46px 0 70px;
  display: grid;
  gap: 24px;
}

.studio-index-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 440px);
  align-items: end;
  gap: 28px;
}

.eyebrow {
  margin-bottom: 8px;
  color: var(--color-blue);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.studio-index-header h1 {
  font-size: 46px;
  letter-spacing: 0;
}

.studio-index-header p {
  max-width: 660px;
  margin-top: 10px;
  color: var(--color-muted);
  font-size: 15px;
}

.create-workspace {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.76);
}

.create-workspace input {
  min-width: 0;
  height: 42px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: var(--color-paper-soft);
  color: var(--color-ink);
  padding: 0 12px;
  outline: none;
  font-family: var(--font-ui);
  font-size: 14px;
}

.create-workspace button,
.workspace-empty .btn-black {
  min-height: 42px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 900;
}

.workspace-list {
  display: grid;
  gap: 12px;
}

.workspace-row {
  min-height: 82px;
  padding: 14px 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  border-radius: var(--radius-sm);
}

.workspace-main-link {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 14px;
  color: var(--color-ink);
}

.workspace-main-link strong {
  display: block;
  overflow: hidden;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-main-link small,
.workspace-meta span,
.workspace-empty p {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
}

.workspace-mark,
.empty-icon {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-blue);
  flex: 0 0 auto;
}

.workspace-meta {
  display: inline-flex;
  align-items: center;
  gap: 16px;
  font-family: var(--font-ui);
}

.workspace-meta a {
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-ink);
  color: #fff;
  font-size: 12px;
  font-weight: 900;
}

.workspace-state,
.workspace-empty {
  min-height: 230px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  border-radius: var(--radius-sm);
  text-align: center;
}

.workspace-state strong,
.workspace-empty strong {
  font-family: var(--font-ui);
  font-size: 16px;
}

.workspace-empty p {
  max-width: 440px;
}

.spin {
  animation: spin 900ms linear infinite;
}

@media (max-width: 760px) {
  .studio-index-page {
    padding-bottom: 80px;
  }

  .studio-index-shell {
    width: calc(100vw - 28px);
    padding-top: 28px;
  }

  .studio-index-header,
  .workspace-row {
    grid-template-columns: 1fr;
  }

  .studio-index-header h1 {
    font-size: 34px;
  }

  .create-workspace {
    grid-template-columns: 1fr;
  }

  .workspace-meta {
    justify-content: space-between;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
