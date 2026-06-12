# gbrain 完整安装与配置指南

gbrain 是基于 SQLite/PostgreSQL + pgvector 的个人知识库系统，支持语义搜索和 Markdown 导入。

## 安装前提

- Linux/macOS
- [Bun](https://bun.sh) ≥ 1.1
- (可选) Docker — 用于 PostgreSQL + pgvector

## 安装步骤

### 1. 安装 Bun

```bash
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"
```

添加到 `~/.bashrc` 使其持久化：

```bash
echo 'export PATH="$HOME/.bun/bin:$PATH"' >> ~/.bashrc
```

### 2. 安装 gbrain

**推荐方式：从源码安装（便于自定义和升级）**

```bash
git clone https://github.com/garrytan/gbrain.git ~/gbrain
cd ~/gbrain && bun install && bun link
```

**备选方式：全局安装**

```bash
bun install -g github:garrytan/gbrain
```

> 如果全局安装后 `gbrain doctor` 报告 `schema_version: 0`，请回退到源码安装方式。

### 3. 初始化知识库

```bash
gbrain init
```

交互式向导会提示选择：
- **存储引擎**：PGLite（零配置，本地文件）或 PostgreSQL（生产推荐）
- **嵌入模型**：选择 SiliconFlow（国内）或 OpenAI 等
- **搜索模式**：根据成本和精度需求选择

### 4. 配置嵌入模型

如果使用 SiliconFlow（推荐，国内可用，嵌入免费）：

```bash
# 设置 API key（通过环境变量，不写入配置文件）
export SILICONFLOW_API_KEY="sk-..."

# 配置嵌入模型
gbrain config set embedding_model siliconflow:Qwen/Qwen3-Embedding-8B
gbrain config set embedding_dimensions 4096
```

如果使用 OpenAI：

```bash
export OPENAI_API_KEY="sk-..."
gbrain config set embedding_model openai:text-embedding-3-large
gbrain config set embedding_dimensions 3072
```

### 5. 验证安装

```bash
gbrain doctor
```

预期输出：

```
✓ gbrain CLI
✓ Database connection
✓ Embedding model: siliconflow:Qwen/Qwen3-Embedding-8B
✓ API key: configured
```

## 数据库引擎选择

### PGLite（零配置）

适合个人使用，无需安装 PostgreSQL。

```bash
gbrain init --engine pglite
```

数据存储在 `~/.gbrain/gbrain.db`。

### PostgreSQL + pgvector（生产推荐）

适合大量文档或多设备同步。

**使用 Docker 一键启动：**

```bash
cd hermes-memos-gbrain-bridge
docker compose -f docker-compose.yml up -d
```

然后初始化：

```bash
gbrain init --engine postgres
# 按提示输入：
# host: localhost
# port: 5432
# database: gbrain
# user: gbrain_user
# password: CHANGE_THIS_PASSWORD
```

### Supabase（云端）

适合多设备同步。

```bash
gbrain init --engine postgres
# host: your-project.supabase.co
# port: 5432
# 使用 Supabase 提供的连接字符串
```

## 配置文件

gbrain 配置文件位于 `~/.gbrain/config.json`：

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

**安全注意**：API key 从不写入此文件，始终通过环境变量提供。

## 常见问题

### "command not found: gbrain"

```bash
# 检查 bun 是否安装
which bun

# 检查 gbrain 是否 link
cd ~/gbrain && bun link

# 或检查 PATH
echo $PATH | grep bun
```

### "schema_version: 0" 错误

数据库未正确初始化。运行：

```bash
gbrain apply-migrations --yes
```

### 嵌入模型报错 "unknown provider"

gbrain 版本过旧，不支持该 provider。升级：

```bash
cd ~/gbrain && git pull && bun install && bun link
```

### 想更换嵌入模型

更换嵌入模型后，**必须重建所有向量**：

```bash
gbrain config set embedding_model <new-model>
gbrain config set embedding_dimensions <new-dims>
gbrain embed --force  # 重建所有向量
```

## 版本信息

本指南基于 gbrain 版本要求：

- **最低版本**：包含 SiliconFlow recipe 的版本（commit `421a9173` 或更新）
- **验证命令**：`gbrain --version`
- **升级命令**：`gbrain upgrade` 或 `cd ~/gbrain && git pull && bun install`
