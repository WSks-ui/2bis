<template>
  <div class="admin-page paper-page">
    <main class="admin-shell">
      <section v-reveal class="admin-hero">
        <div>
          <p class="eyebrow">Admin Console</p>
          <h1>API Key 控制台</h1>
          <p>管理上游生图接口配置。完整 Key 只在提交时传输，页面和接口响应只显示掩码。</p>
          <div class="admin-hero-points" aria-label="控制台能力">
            <span>掩码展示</span>
            <span>熔断可视化</span>
            <span>连接测试</span>
          </div>
        </div>
        <div class="status-card surface-card" :class="{ healthy: activeConfig, fallback: !activeConfig }">
          <div class="status-orb" aria-hidden="true"></div>
          <span>当前生效配置</span>
          <strong>{{ activeConfig?.name || '环境变量兜底' }}</strong>
          <small>{{ activeConfig ? `${activeConfig.provider} · ${activeConfig.key_mask}` : '未配置数据库 Key 时使用 .env' }}</small>
          <div class="status-metrics" aria-label="上游状态摘要">
            <div>
              <b>{{ enabledCount }}</b>
              <em>启用</em>
            </div>
            <div>
              <b>{{ openCircuitCount }}</b>
              <em>熔断</em>
            </div>
            <div>
              <b>{{ testedCount }}</b>
              <em>已测</em>
            </div>
          </div>
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
          <div class="security-note">
            <span aria-hidden="true">●</span>
            <p>保存后页面不会回显完整 Key；编辑时留空即可保留原 Key。</p>
          </div>
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
          <div v-if="loading && !apiKeys.length" class="empty-state loading-state">
            <div class="empty-orb" aria-hidden="true"></div>
            <strong>正在读取上游配置</strong>
            <p>会优先展示数据库中的配置；没有记录时继续使用 .env 兜底。</p>
          </div>
          <div v-else-if="!apiKeys.length" class="empty-state">
            <div class="empty-orb quiet" aria-hidden="true"></div>
            <strong>还没有数据库 API Key</strong>
            <p>建议先添加主力通道，再添加备用通道；系统当前会继续使用 .env 配置。</p>
          </div>
          </Transition>

          <TransitionGroup name="list" tag="div" class="key-card-list">
          <article v-for="item in apiKeys" :key="item.id" class="key-card" :class="{ active: item.is_active }">
            <div class="card-status-rail" :class="statusRailClass(item)" aria-hidden="true"></div>
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
              <button class="btn-danger" type="button" :disabled="item.is_active" @click="confirmDelete(item)">删除</button>
            </div>
          </article>
          </TransitionGroup>
        </section>
      </section>
    </main>

    <Transition name="modal-fade">
    <div v-if="deleteTarget" class="confirm-overlay" @click.self="deleteTarget = null">
      <Transition name="modal-pop" appear>
      <div class="confirm-card">
        <p class="eyebrow">Danger Zone</p>
        <h3>删除上游配置？</h3>
        <p>将删除「{{ deleteTarget.name }}」。已生效配置不能删除；删除备用配置后，相关熔断与测试记录也会一并移除。</p>
        <div class="confirm-actions">
          <button class="btn-ghost" type="button" @click="deleteTarget = null">取消</button>
          <button class="btn-danger" type="button" :disabled="deletingId === deleteTarget.id" @click="deleteKey(deleteTarget)">
            {{ deletingId === deleteTarget.id ? '删除中' : '确认删除' }}
          </button>
        </div>
      </div>
      </Transition>
    </div>
    </Transition>
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
const deleteTarget = ref(null)
const deletingId = ref(null)

const activeConfig = computed(() => apiKeys.value.find((item) => item.is_active))
const enabledCount = computed(() => apiKeys.value.filter((item) => item.is_enabled).length)
const openCircuitCount = computed(() => apiKeys.value.filter((item) => item.circuit_state === 'open').length)
const testedCount = computed(() => apiKeys.value.filter((item) => item.last_tested_at).length)

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

function confirmDelete(item) {
  deleteTarget.value = item
}

async function deleteKey(item) {
  deletingId.value = item.id
  try {
    await api.delete(`/admin/api-keys/${item.id}`)
    ElMessage.success('配置已删除')
    deleteTarget.value = null
    await fetchKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    deletingId.value = null
  }
}

function statusRailClass(item) {
  if (item.circuit_state === 'open') return 'rail-danger'
  if (!item.is_enabled) return 'rail-muted'
  if (item.is_active) return 'rail-active'
  if (item.last_test_status === 'success') return 'rail-success'
  if (item.last_test_status === 'failed') return 'rail-warning'
  return 'rail-idle'
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

.admin-hero-points {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.admin-hero-points span {
  padding: 7px 10px;
  border: 1px solid rgba(60, 110, 232, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.6);
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 850;
  transition: transform var(--transition-base), background var(--transition-base), border-color var(--transition-base);
}

.admin-hero-points span:hover {
  border-color: rgba(60, 110, 232, 0.24);
  background: rgba(255, 255, 255, 0.86);
  transform: translateY(-2px);
}

.status-card {
  position: relative;
  padding: 24px;
  display: grid;
  align-content: center;
  gap: 8px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.86), rgba(246, 244, 238, 0.62)),
    radial-gradient(circle at 16% 10%, rgba(60, 110, 232, 0.12), transparent 16rem);
}

.status-card:hover {
  transform: translateY(-3px);
}

.status-orb {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 32%, #fff, rgba(63, 140, 104, 0.72) 42%, rgba(63, 140, 104, 0.12) 72%);
  box-shadow: 0 0 0 8px rgba(63, 140, 104, 0.08);
  animation: status-breathe 2.8s ease-in-out infinite;
}

.status-card.fallback .status-orb {
  background: radial-gradient(circle at 35% 32%, #fff, rgba(216, 161, 95, 0.78) 42%, rgba(216, 161, 95, 0.14) 72%);
  box-shadow: 0 0 0 8px rgba(216, 161, 95, 0.1);
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

.status-metrics {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px;
}

.status-metrics div {
  padding: 10px;
  border: 1px solid rgba(226, 229, 223, 0.8);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.58);
  transition: transform var(--transition-base), background var(--transition-base);
}

.status-card:hover .status-metrics div {
  background: rgba(255, 255, 255, 0.84);
  transform: translateY(-1px);
}

.status-metrics b,
.status-metrics em {
  display: block;
  font-style: normal;
}

.status-metrics b {
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: 22px;
  line-height: 1;
}

.status-metrics em {
  margin-top: 5px;
  color: var(--color-muted);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 850;
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

.security-note {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 13px;
  border: 1px solid rgba(63, 140, 104, 0.14);
  border-radius: var(--radius-md);
  background: rgba(63, 140, 104, 0.07);
  color: #2e6f52;
}

.security-note span {
  color: var(--color-green);
  font-size: 10px;
  line-height: 1.8;
}

.security-note p {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
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
  padding: 42px 16px;
  display: grid;
  justify-items: center;
  gap: 10px;
  border: 1px dashed var(--color-line-strong);
  border-radius: var(--radius-lg);
  color: var(--color-muted);
  text-align: center;
}

.empty-state strong {
  color: var(--color-ink);
  font-size: 16px;
}

.empty-state p {
  max-width: 420px;
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
}

.empty-orb {
  width: 58px;
  height: 58px;
  border-radius: 22px;
  background:
    radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.96), transparent 20px),
    linear-gradient(135deg, rgba(60, 110, 232, 0.22), rgba(63, 140, 104, 0.18));
  box-shadow: 0 16px 34px rgba(60, 110, 232, 0.12);
  animation: empty-orb-float 2.6s var(--ease-out-soft) infinite;
}

.empty-orb.quiet {
  animation: none;
  opacity: 0.82;
}

.key-card {
  position: relative;
  padding: 18px;
  display: grid;
  gap: 16px;
  overflow: hidden;
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

.card-status-rail {
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--color-line-strong);
  opacity: 0.9;
}

.card-status-rail.rail-active,
.card-status-rail.rail-success {
  background: linear-gradient(180deg, var(--color-green), rgba(63, 140, 104, 0.22));
}

.card-status-rail.rail-danger {
  background: linear-gradient(180deg, var(--color-red), rgba(200, 77, 60, 0.22));
}

.card-status-rail.rail-warning {
  background: linear-gradient(180deg, var(--color-orange), rgba(216, 161, 95, 0.22));
}

.card-status-rail.rail-muted {
  background: linear-gradient(180deg, var(--color-soft), rgba(111, 116, 111, 0.16));
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

.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(23, 23, 23, 0.42);
  backdrop-filter: blur(10px);
}

.confirm-card {
  width: min(430px, 100%);
  padding: 26px;
  border: 1px solid rgba(200, 77, 60, 0.18);
  border-radius: var(--radius-xl);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(255, 249, 247, 0.94)),
    radial-gradient(circle at 10% 0%, rgba(200, 77, 60, 0.08), transparent 16rem);
  box-shadow: var(--shadow-lg);
}

.confirm-card h3 {
  margin: 0 0 10px;
  font-size: 24px;
}

.confirm-card > p:not(.eyebrow) {
  margin: 0;
  color: var(--color-muted);
}

.confirm-actions {
  margin-top: 22px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
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

@keyframes status-breathe {
  0%, 100% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.08);
  }
}

@keyframes empty-orb-float {
  0%, 100% {
    border-radius: 22px;
    transform: translateY(0) rotate(-2deg);
  }

  50% {
    border-radius: 28px 20px 26px 22px;
    transform: translateY(-4px) rotate(3deg);
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
  .switch-row,
  .confirm-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .status-metrics {
    grid-template-columns: 1fr;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-orb,
  .empty-orb,
  .pill,
  .test-message {
    animation: none;
  }

  .status-card:hover,
  .key-card:hover,
  .admin-hero-points span:hover {
    transform: none;
  }
}
</style>
