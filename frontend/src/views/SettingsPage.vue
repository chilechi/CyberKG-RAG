<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchSettings, type SettingsResponse } from "../api/settings";

const settings = ref<SettingsResponse | null>(null);
const loading = ref(false);
const error = ref("");

const configuredCount = computed(() => {
  if (!settings.value) return 0;
  return [settings.value.model.dashscope_configured, settings.value.model.deepseek_configured].filter(Boolean).length;
});

async function loadSettings() {
  loading.value = true;
  error.value = "";
  try {
    settings.value = await fetchSettings();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "系统设置加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(loadSettings);
</script>

<template>
  <div class="page-grid settings-page">
    <section v-if="loading" class="panel state-panel compact-state">正在加载系统设置...</section>
    <section v-else-if="error" class="panel state-panel error compact-state">{{ error }}</section>

    <template v-if="settings">
      <section class="settings-main tighter-grid">
        <div class="panel">
          <div class="section-heading compact">
            <div>
              <h2>基础设置</h2>
              <p>当前只读展示，后续再接保存接口。</p>
            </div>
          </div>
          <div class="settings-form-grid">
            <label>
              <span>系统名称</span>
              <input :value="settings.basic.system_name" disabled />
            </label>
            <label>
              <span>默认问答模式</span>
              <input :value="settings.basic.default_qa_mode" disabled />
            </label>
            <label>
              <span>系统语言</span>
              <input :value="settings.basic.language" disabled />
            </label>
            <label>
              <span>时区</span>
              <input :value="settings.basic.timezone" disabled />
            </label>
            <label class="full-field">
              <span>系统描述</span>
              <textarea :value="settings.basic.description" disabled />
            </label>
          </div>
        </div>

        <div class="panel">
          <div class="section-heading compact">
            <div>
              <h2>模型配置</h2>
              <p>敏感密钥只显示配置状态，不返回具体值。</p>
            </div>
          </div>
          <div class="settings-kv-list">
            <div>
              <span>LLM Provider</span>
              <strong>{{ settings.model.llm_provider }}</strong>
            </div>
            <div>
              <span>LLM Model</span>
              <strong>{{ settings.model.llm_model }}</strong>
            </div>
            <div>
              <span>LLM Base URL</span>
              <strong>{{ settings.model.llm_base_url }}</strong>
            </div>
            <div>
              <span>LLM 超时</span>
              <strong>{{ settings.model.llm_timeout }}s</strong>
            </div>
            <div>
              <span>向量化服务</span>
              <strong>{{ settings.model.embedding_provider }}</strong>
            </div>
            <div>
              <span>Embedding Model</span>
              <strong>{{ settings.model.embedding_model }}</strong>
            </div>
            <div>
              <span>Embedding 维度</span>
              <strong>{{ settings.model.embedding_dim }}</strong>
            </div>
            <div>
              <span>Embedding URL</span>
              <strong>{{ settings.model.embedding_url }}</strong>
            </div>
            <div>
              <span>Milvus Collection</span>
              <strong>{{ settings.model.milvus_collection }}</strong>
            </div>
            <div>
              <span>DashScope Key</span>
              <strong :class="settings.model.dashscope_configured ? 'ok-text' : 'warn-text'">
                {{ settings.model.dashscope_configured ? "已配置" : "未配置" }}
              </strong>
            </div>
            <div>
              <span>DeepSeek Key</span>
              <strong :class="settings.model.deepseek_configured ? 'ok-text' : 'warn-text'">
                {{ settings.model.deepseek_configured ? "已配置" : "未配置" }}
              </strong>
            </div>
          </div>
          <div class="settings-note">
            已配置外部密钥 {{ configuredCount }} / 2。页面不会展示 API Key 明文。
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="section-heading compact">
          <div>
            <h2>数据库连接</h2>
            <p>连接状态来自后端实时探活。</p>
          </div>
          <button class="ghost-button small-button" type="button" @click="loadSettings">刷新</button>
        </div>
        <div class="connection-grid">
          <article v-for="item in settings.connections" :key="item.name" class="connection-card">
            <div>
              <strong>{{ item.name }}</strong>
              <span :class="['status-pill', item.status]">{{ item.status === "ok" ? "正常" : "异常" }}</span>
            </div>
            <dl>
              <dt>Host</dt>
              <dd>{{ item.host }}</dd>
              <dt>Port</dt>
              <dd>{{ item.port }}</dd>
              <dt>Database / Collection</dt>
              <dd>{{ item.database || "--" }}</dd>
            </dl>
            <small>{{ item.message }}</small>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>
