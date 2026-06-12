# SiliconFlow (硅基流动) 集成指南

本系统的 Embedding 和 LLM 能力通过 [SiliconFlow](https://siliconflow.cn) 提供，这是一个中国 AI 模型服务商，提供 OpenAI-compatible API。

## 概述

本记忆系统的 SiliconFlow 集成涉及两个组件：

1. **MemOS 插件** — 负责会话记忆的提取、总结和向量化
2. **gbrain** — 负责个人知识库的向量化存储和语义检索

两个组件使用**相同的嵌入模型**以确保向量空间一致，从而实现跨系统的语义搜索。

## 模型配置

### 推荐模型组合

| 用途 | 模型 | 维度 | 说明 |
|------|------|------|------|
| Embedding | `Qwen/Qwen3-Embedding-8B` | 4096 | Matryoshka 兼容，当前免费 |
| LLM (MemOS) | `Qwen/Qwen3-8B` | — | 记忆提取和总结 |

### 维度选择 (Matryoshka)

Qwen3-Embedding-8B 支持 Matryoshka 表示，可以在以下维度中任选：

```
64, 128, 256, 512, 768, 1024, 2048, 4096
```

**建议**：使用完整 4096 维以获得最佳检索精度。如果存储受限，可降至 2048 或 1024。

## MemOS 插件配置

MemOS 使用 `openai_compatible` provider 接入 SiliconFlow：

```yaml
# ~/.hermes/memos-plugin/config.yaml
version: 1

llm:
  provider: openai_compatible
  base_url: https://api.siliconflow.cn/v1
  api_key: ${SILICONFLOW_API_KEY}  # 通过环境变量注入
  model: Qwen/Qwen3-8B

embedding:
  provider: openai_compatible
  base_url: https://api.siliconflow.cn/v1
  api_key: ${SILICONFLOW_API_KEY}
  model: Qwen/Qwen3-Embedding-8B
  dimensions: 4096
```

### 环境变量

```bash
export SILICONFLOW_API_KEY="sk-..."
```

将上述配置添加到 `~/.bashrc` 或 systemd service 的 `Environment=` 中。

## gbrain 配置

gbrain 原生支持 SiliconFlow provider（需要 gbrain 版本 ≥ 0.32.0，包含 commit `421a9173`）。

### 配置方式

```bash
# 方式一：交互式配置
gbrain init
# 选择 SiliconFlow 作为 embedding provider

# 方式二：直接编辑配置文件
gbrain config set embedding_model siliconflow:Qwen/Qwen3-Embedding-8B
gbrain config set embedding_dimensions 4096
```

### 配置文件示例

```json
{
  "engine": "postgres",
  "embedding_model": "siliconflow:Qwen/Qwen3-Embedding-8B",
  "embedding_dimensions": 4096,
  "host": "localhost",
  "port": 5432,
  "database": "gbrain",
  "user": "gbrain_user",
  "password": "CHANGE_THIS_PASSWORD"
}
```

gbrain 会自动从环境变量读取 `SILICONFLOW_API_KEY`，无需在配置文件中硬编码。

### 验证 Embedding 可用

```bash
gbrain doctor
# 应显示：
# - Embedding model: siliconflow:Qwen/Qwen3-Embedding-8B
# - API key: configured via SILICONFLOW_API_KEY
```

## 版本要求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| gbrain | ≥ 0.32.0 | 包含 SiliconFlow recipe (`421a9173`) |
| MemOS | 无特殊要求 | 使用 openai_compatible 即可 |

### gbrain 升级检查

```bash
cd ~/gbrain && git log --oneline -1 -- src/core/ai/recipes/siliconflow.ts
# 应显示 commit 包含 SiliconFlow 支持
```

如果版本过旧，升级：

```bash
cd ~/gbrain && git pull && bun install
```

## 成本估算

截至 2026-05-31：

| 服务 | 价格 |
|------|------|
| Embedding (Qwen3-Embedding-8B) | **免费** |
| Chat (Qwen3-8B) | 约 ¥0.5 / 1M tokens |

**注意**：免费策略可能变更，请以 [SiliconFlow 官网](https://siliconflow.cn) 为准。

## 故障排查

### "embedding model not found" / "unknown provider siliconflow"

**原因**：gbrain 版本过旧，不包含 SiliconFlow recipe。

**解决**：

```bash
cd ~/gbrain
git pull origin main
bun install
bun link  # 如果之前 link 过
```

### "API key not configured"

**原因**：环境变量 `SILICONFLOW_API_KEY` 未设置。

**解决**：

```bash
export SILICONFLOW_API_KEY="sk-..."
# 或添加到 ~/.bashrc
echo 'export SILICONFLOW_API_KEY="sk-..."' >> ~/.bashrc
```

### MemOS 和 gbrain 使用不同嵌入模型

**后果**：向量空间不一致，语义搜索质量下降。

**检查**：

```bash
# MemOS
grep "model:" ~/.hermes/memos-plugin/config.yaml

# gbrain
gbrain config get embedding_model
```

**修复**：确保两者使用相同的 `Qwen/Qwen3-Embedding-8B` 模型和相同的 `dimensions`。

## 替代方案

如果 SiliconFlow 不可用，以下服务商也提供兼容的 OpenAI-compatible API：

| 服务商 | 嵌入模型 | 特点 |
|--------|----------|------|
| OpenAI | text-embedding-3-large | 3072维，付费 |
| 阿里云 DashScope | text-embedding-v3 | 1024维，国内可用 |
| 本地 Ollama | nomic-embed-text 等 | 免费，需 GPU |

更换服务商时，**必须同时更新 MemOS 和 gbrain 的嵌入模型配置**，并重新运行 `--full-sync` 重建向量。
