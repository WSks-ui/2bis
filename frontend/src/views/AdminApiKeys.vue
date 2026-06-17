<template>
  <div class="admin-page paper-page">
    <main class="admin-shell">
      <section v-reveal class="admin-hero">
        <div>
          <p class="eyebrow">Admin Console</p>
          <h1>API Key 控制台</h1>
          <p>管理上游生图接口配置。完整 Key 只在提交时传输，页面和接口响应只显示掩码。</p>
        </div>
        <div class="status-card surface-card">
          <span>当前生效配置</span>
          <strong>{{ activeConfig?.name || '环境变量兜底' }}</strong>
          <small>{{ activeConfig ? `${activeConfig.provider} · ${activeConfig.key_mask}` : '未配置数据库 Key 时使用 .env' }}</small>
        </div>
      </section>

      <section class="admin-grid">
        <form v-reveal="100" class="surface-card key-form" autocomplete="off" @submit.prevent="submitForm">
          <div class="section-head">
            <p class="eyebrow">{{ editingId ? 'Edit Key' : 'New Key' }}</p>
            <h2>{{ editingId ? '编辑配置' : '添加 API Key' }}</h2>
          </div>

          <label>
            <span>配置名称</span>
            <input v-model.trim="form.name" required maxlength="80" placeholder="例如：主力通道" autocomplete="off" />
          </label>

          <label>
            <span>服务商</span>
            <input v-model.trim="form.provider" required maxlength="40" placeholder="aiartmirror" autocomplete="off" />
          </label>

          <label>
            <span>Base URL</span>
            <input v-model.trim="form.api_url" required maxlength="255" placeholder="https://www.aiartmirror.com/v1" autocomplete="off" />
          </label>

          <label>
            <span>API Key</span>
            <input
              v-model.trim="form.api_key"
              :required="!editingId"
              type="password"
              maxlength="4096"
              :placeholder="editingId ? '留空表示不替换 Key' : '粘贴新的 API Key'"
              autocomplete="new-password"
            />
          </label>

          <label>
            <span>response_format</span>
            <select v-model="form.response_format">
              <option value="">不发送</option>
              <option value="url">url</option>
              <option value="b64_json">b64_json</option>
            </select>
          </label>

          <div class="switch-row">
            <label class="check-line">
              <input v-model="form.send_quality" type="checkbox" />
              <span>发送 quality 参数</span>
            </label>
            <label class="check-line">
              <input v-model="form.is_enabled" type="checkbox" />
              <span>启用配置</span>
            </label>
            <label v-if="!editingId" class="check-line">
              <input v-model="form.activate" type="checkbox" />
              <span>创建后设为当前使用</span>
            </label>
          </div>

          <div class="form-actions">
            <button class="btn-black" type="submit" :disabled="saving">
              {{ saving ? '保存中' : editingId ? '保存修改' : '添加配置' }}
            </button>
            <button v-if="editingId" class="btn-ghost" type="button" @click="resetForm">取消编辑</button>
          </div>

          <p class="form-note">当前 aiartmirror 与 zilan520 默认不发送 response_format；zilan520 已支持 quality 参数，可保持“发送 quality 参数”。点击“测试”只会请求 /models 验证 Key 与 Base URL，不会发起生图请求。</p>
        </form>

        <section v-reveal="150" class="surface-card key-list">
          <div class="section-head row">
            <div>
              <p class="eyebrow">Runtime Keys</p>
              <h2>上游配置</h2>
            </div>
            <button class="btn-ghost" type="button" :disabled="loading" @click="fetchKeys">
              {{ loading ? '刷新中' : '刷新' }}
            </button>
          </div>

          <Transition name="modal-pop" mode="out-in">
          <div v-if="loading && !apiKeys.length" class="empty-state">加载中...</div>
          <div v-else-if="!apiKeys.length" class="empty-state">还没有数据库 API Key，系统会继续使用 .env 配置。</div>
          </Transition>

          <TransitionGroup name="list" tag="div" class="key-card-list">
          <article v-for="item in apiKeys" :key="item.id" class="key-card" :class="{ active: item.is_active }">
            <div class="key-main">
              <div>
                <div class="key-title">
                  <strong>{{ item.name }}</strong>
                  <span v-if="item.is_active" class="pill active-pill">当前使用</span>
                  <span v-if="item.circuit_state === 'open'" class="pill danger-pill">熔断中</span>
                  <span v-if="!item.is_enabled" class="pill muted-pill">已停用</span>
                </div>
                <p>{{ item.provider }} · {{ item.key_mask }}</p>
                <small>{{ item.api_url }}</small>
              </div>
              <div class="test-state" :class="item.last_test_status">
                {{ testLabel(item) }}
              </div>
            </div>

            <dl class="meta-grid">
              <div>
                <dt>返回格式</dt>
                <dd>{{ item.response_format || '不发送' }}</dd>
              </div>
              <div>
                <dt>质量参数</dt>
                <dd>{{ item.send_quality ? '发送' : '不发送' }}</dd>
              </div>
              <div>
                <dt>最后测试</dt>
                <dd>{{ formatDate(item.last_tested_at) }}</dd>
              </div>
              <div>
                <dt>最后使用</dt>
                <dd>{{ formatDate(item.last_used_at) }}</dd>
              </div>
              <div>
                <dt>失败次数</dt>
                <dd>{{ item.failure_count || 0 }}</dd>
              </div>
              <div>
                <dt>熔断恢复</dt>
                <dd>{{ item.circuit_state === 'open' ? formatDate(item.circuit_open_until) : '未熔断' }}</dd>
              </div>
            </dl>

            <p v-if="item.last_test_message" class="test-message">{{ item.last_test_message }}</p>
            <p v-if="item.circuit_reason" class="test-message danger-message">{{ item.circuit_reason }}</p>

            <div class="card-actions">
              <button class="btn-ghost" type="button" :disabled="testingId === item.id" @click="testSavedKey(item)">
                {{ testingId === item.id ? '测试中' : '测试' }}
              </button>
              <button class="btn-ghost" type="button" @click="editItem(item)">编辑</button>
              <button class="btn-ghost" type="button" :disabled="item.is_active || !item.is_enabled" @click="activateKey(item)">设为当前</button>
              <button class="btn-ghost" type="button" @click="toggleEnabled(item)">
                {{ item.is_enabled ? '停用' : '启用' }}
              </button>
              <button class="btn-danger" type="button" :disabled="item.is_active" @click="deleteKey(item)">删除</button>
            </div>
          </article>
          </TransitionGroup>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { ElMessage } from '../services/toast'

defineOptions({ name: 'AdminApiKeys' })

const defaultForm = () => ({
  name: '',
  provider: 'aiartmirror',
  api_url: 'https://www.aiartmirror.com/v1',
  api_key: '',
  response_format: '',
  send_quality: true,
  is_enabled: true,
  activate: true
})

const apiKeys = ref([])
const form = ref(defaultForm())
const editingId = ref(null)
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)

const activeConfig = computed(() => apiKeys.value.find((item) => item.is_active))

onMounted(fetchKeys)

async function fetchKeys() {
  loading.value = true
  try {
    const res = await api.get('/admin/api-keys')
    apiKeys.value = res.data || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'API Key 配置加载失败')
  } finally {
    loading.value = false
  }
}

async function submitForm() {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      provider: form.value.provider,
      api_url: form.value.api_url,
      response_format: form.value.response_format || null,
      clear_response_format: !form.value.response_format,
      send_quality: form.value.send_quality,
      is_enabled: form.value.is_enabled
    }
    if (form.value.api_key) payload.api_key = form.value.api_key

    if (editingId.value) {
      await api.patch(`/admin/api-keys/${editingId.value}`, payload)
      ElMessage.success('API Key 配置已更新')
    } else {
      await api.post('/admin/api-keys', {
        ...payload,
        api_key: form.value.api_key,
        activate: form.value.activate
      })
      ElMessage.success('API Key 配置已添加')
    }

    resetForm()
    await fetchKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function editItem(item) {
  editingId.value = item.id
  form.value = {
    name: item.name,
    provider: item.provider,
    api_url: item.api_url,
    api_key: '',
    response_format: item.response_format || '',
    send_quality: item.send_quality !== false,
    is_enabled: item.is_enabled,
    activate: item.is_active
  }
}

function resetForm() {
  editingId.value = null
  form.value = defaultForm()
}

async function activateKey(item) {
  try {
    await api.post(`/admin/api-keys/${item.id}/activate`)
    ElMessage.success('当前使用配置已切换')
    await fetchKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '切换失败')
  }
}

async function testSavedKey(item) {
  testingId.value = item.id
  try {
    const res = await api.post(`/admin/api-keys/${item.id}/test`, {})
    if (res.data.ok) {
      ElMessage.success(res.data.message || '连接测试成功')
    } else {
      ElMessage.warning(res.data.message || '连接测试失败')
    }
    await fetchKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '测试失败')
  } finally {
    testingId.value = null
  }
}

async function toggleEnabled(item) {
  try {
    await api.patch(`/admin/api-keys/${item.id}`, { is_enabled: !item.is_enabled })
    ElMessage.success(item.is_enabled ? '配置已停用' : '配置已启用')
    await fetchKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '状态更新失败')
  }
}

async function deleteKey(item) {
  if (!window.confirm(`确认删除 ${item.name}？`)) return
  try {
    await api.delete(`/admin/api-keys/${item.id}`)
    ElMessage.success('配置已删除')
    await fetchKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function testLabel(item) {
  if (item.last_test_status === 'success') return '测试通过'
  if (item.last_test_status === 'failed') return '测试失败'
  return '未测试'
}

function formatDate(value) {
  if (!value) return '无'
  return new Date(value).toLocaleString()
}
</script>

<style scoped>
.admin-shell {
  max-width: 1320px;
  margin: 0 auto;
  padding: 42px 28px 100px;
}

.admin-hero {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) 360px;
  gap: 28px;
  align-items: stretch;
}

.eyebrow {
  margin: 0 0 9px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.admin-hero h1 {
  margin: 0;
  font-size: clamp(34px, 5vw, 58px);
  letter-spacing: -0.06em;
}

.admin-hero p {
  max-width: 560px;
  margin: 12px 0 0;
  color: var(--color-muted);
  font-size: 15px;
}

.status-card {
  padding: 24px;
  display: grid;
  align-content: center;
  gap: 8px;
  overflow: hidden;
}

.status-card:hover {
  transform: translateY(-3px);
}

.status-card span,
.key-form label span,
.meta-grid dt {
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
}

.status-card strong {
  font-family: var(--font-heading);
  font-size: 28px;
}

.status-card small,
.key-main small,
.form-note {
  color: var(--color-muted);
}

.admin-grid {
  margin-top: 28px;
  display: grid;
  grid-template-columns: 390px minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.key-form,
.key-list {
  padding: 24px;
}

.section-head {
  margin-bottom: 20px;
}

.section-head h2 {
  margin: 0;
  font-size: 24px;
}

.section-head.row,
.key-main,
.card-actions,
.form-actions,
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.key-form {
  display: grid;
  gap: 16px;
}

.key-form label {
  display: grid;
  gap: 7px;
}

.key-form input,
.key-form select {
  min-height: 42px;
  width: 100%;
  padding: 0 13px;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.76);
  color: var(--color-ink);
  outline: none;
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base),
    background var(--transition-base),
    transform var(--transition-base);
}

.key-form input:focus,
.key-form select:focus {
  border-color: var(--color-ink);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 0 0 4px rgba(23, 23, 23, 0.06);
  transform: translateY(-1px);
}

.check-line {
  display: inline-flex !important;
  grid-template-columns: auto auto;
  align-items: center;
  gap: 8px !important;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.check-line input {
  min-height: auto;
  width: auto;
}

.form-actions {
  justify-content: flex-start;
}

.btn-ghost,
.btn-danger {
  position: relative;
  overflow: hidden;
  min-height: 38px;
  padding: 0 13px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  transition:
    border-color var(--transition-base),
    background var(--transition-base),
    color var(--transition-base),
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.btn-ghost {
  border: 1px solid var(--color-line-strong);
  background: rgba(255, 255, 255, 0.58);
  color: var(--color-muted);
}

.btn-danger {
  border: 1px solid rgba(200, 77, 60, 0.22);
  background: rgba(200, 77, 60, 0.08);
  color: var(--color-red);
}

.btn-ghost:disabled,
.btn-danger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-ghost:hover:not(:disabled),
.btn-danger:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 22px rgba(23, 23, 23, 0.08);
  transform: translateY(-1px);
}

.btn-ghost:active:not(:disabled),
.btn-danger:active:not(:disabled) {
  transform: translateY(0) scale(0.97);
}

.empty-state {
  padding: 40px 16px;
  border: 1px dashed var(--color-line-strong);
  border-radius: var(--radius-lg);
  color: var(--color-muted);
  text-align: center;
}

.key-card {
  padding: 18px;
  display: grid;
  gap: 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.58);
  transition:
    border-color var(--transition-base),
    background var(--transition-base),
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.key-card-list {
  position: relative;
}

.key-card + .key-card {
  margin-top: 14px;
}

.key-card.active {
  border-color: rgba(63, 140, 104, 0.42);
  box-shadow: 0 0 0 1px rgba(63, 140, 104, 0.12);
}

.key-card:hover {
  border-color: rgba(60, 110, 232, 0.22);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: var(--shadow-md);
  transform: translateY(-3px);
}

.key-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.key-title strong {
  font-family: var(--font-heading);
  font-size: 18px;
}

.key-main p {
  margin: 4px 0 1px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 760;
}

.pill {
  padding: 3px 8px;
  border-radius: 999px;
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 900;
  animation: pill-in 360ms var(--ease-out-soft) both;
}

.active-pill {
  background: rgba(63, 140, 104, 0.1);
  color: var(--color-green);
}

.muted-pill {
  background: rgba(111, 116, 111, 0.1);
  color: var(--color-muted);
}

.danger-pill {
  background: rgba(200, 77, 60, 0.1);
  color: var(--color-red);
}

.test-state {
  min-width: 74px;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(111, 116, 111, 0.08);
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 900;
  text-align: center;
  transition: transform var(--transition-base), background var(--transition-base), color var(--transition-base);
}

.key-card:hover .test-state {
  transform: translateY(-1px);
}

.test-state.success {
  background: rgba(63, 140, 104, 0.1);
  color: var(--color-green);
}

.test-state.failed {
  background: rgba(200, 77, 60, 0.09);
  color: var(--color-red);
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.meta-grid div {
  padding: 10px;
  border-radius: var(--radius-md);
  background: rgba(245, 246, 241, 0.74);
  transition: transform var(--transition-base), background var(--transition-base);
}

.key-card:hover .meta-grid div {
  background: rgba(245, 246, 241, 0.96);
  transform: translateY(-1px);
}

.meta-grid dd {
  margin: 4px 0 0;
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
}

.test-message {
  margin: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: rgba(245, 246, 241, 0.8);
  color: var(--color-muted);
  font-size: 12px;
  word-break: break-word;
  animation: message-in 320ms var(--ease-out-soft) both;
}

.danger-message {
  background: rgba(200, 77, 60, 0.08);
  color: var(--color-red);
}

@keyframes pill-in {
  from {
    opacity: 0;
    transform: translate3d(0, -3px, 0) scale(0.94);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
  }
}

@keyframes message-in {
  from {
    opacity: 0;
    transform: translate3d(0, 6px, 0);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

.card-actions {
  justify-content: flex-start;
  flex-wrap: wrap;
}

@media (max-width: 980px) {
  .admin-hero,
  .admin-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .admin-shell {
    padding: 28px 14px 96px;
  }

  .key-main,
  .section-head.row,
  .switch-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
