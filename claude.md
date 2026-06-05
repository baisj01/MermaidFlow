# MermaidFlow AutoDL 服务器复现计划

## 背景

在 AutoDL 云服务器（RTX 4090 24GB, Ubuntu 22.04, CUDA 11.8, Miniconda Python 3.10）上复现 MermaidFlow 项目。使用 Ollama 本地开源模型替代付费 API，通过本机 Clash HTTP 代理解决服务器网络问题。

## 与原始项目的关键差异

| 项目 | 原始方案 | 本方案 |
|------|---------|--------|
| LLM API | OpenAI / OpenRouter 付费 API | Ollama 本地开源模型 |
| 模型 | gpt-4o-mini | Qwen2.5:14b（推荐）或类似 |
| API 端点 | api.openai.com | localhost:11434/v1 |
| Mermaid CLI | 需要 mmdc | 需要 Node.js + mmdc |

## 待用户提供的信息

在开始前需要用户提供：
1. **GitHub 仓库 URL** — 用于 git clone 和后续 push
2. **AutoDL SSH 登录信息** — IP、端口、用户名、密码/密钥
3. **本机局域网 IP** — Clash HTTP 代理地址（如 `192.168.x.x:7890`）
4. **确认模型选择** — Qwen2.5:14b（推荐）/ Qwen2.5:7b / Qwen2.5:32b
5. **wandb/weave API key**（如无可跳过，尝试禁用 weave 追踪）

## 实施步骤

### 第 0 步：前期准备（本机操作）

- [ ] 确认 Clash 已开启"允许局域网连接"，记录 HTTP 代理端口（默认 7890）
- [ ] 确认本机与 AutoDL 服务器网络可达性（可能需要 SSH 隧道转发代理）
- [ ] 在 GitHub 仓库中确保项目已推送（包括 submodule 引用）

> **网络可达性问题**：AutoDL 服务器在云端数据中心，通常无法直接访问用户家庭网络的 192.168.x.x 地址。如果本机没有公网 IP，可能需要：
> - **方案 A**：SSH 反向隧道转发代理端口（服务器通过 SSH 隧道访问本机代理）
> - **方案 B**：AutoDL 自带学术网络加速（底部有 Jupyter 链接中启动），对 pip/conda/git 一般够用
> - **方案 C**：使用 pip/conda 国内镜像 + 手动下载模型文件

### 第 1 步：SSH 连接与基础环境检查

- [ ] SSH 连接到 AutoDL 实例
- [ ] 验证基础环境：`python --version`（应为 3.10）、`nvcc --version`（CUDA 11.8）、`nvidia-smi`（RTX 4090）
- [ ] 检查 conda 环境，如有必要创建专用环境 `conda create -n mermaidflow python=3.10 -y`

### 第 2 步：配置网络代理

- [ ] 测试本机代理可达性：`curl -x http://<本机IP>:7890 https://www.google.com`
- [ ] 如不可达，建立 SSH 反向隧道：
  ```bash
  # 在服务器上执行，将服务器 7890 端口转发到本机 7890
  ssh -R 7890:localhost:7890 user@server_ip
  ```
- [ ] 设置终端代理环境变量：
  ```bash
  export http_proxy=http://localhost:7890
  export https_proxy=http://localhost:7890
  export HTTP_PROXY=http://localhost:7890
  export HTTPS_PROXY=http://localhost:7890
  ```
- [ ] 验证 `curl -x http://localhost:7890 https://github.com` 可访问

> **备选**：如果代理不可用，对 pip 使用清华/中科大镜像，git 使用 AutoDL 自带的学术加速。

### 第 3 步：克隆项目

- [ ] `git clone <用户GitHub仓库URL> --recurse-submodules`
- [ ] 如 submodule 未成功拉取，手动执行：
  ```bash
  git submodule init
  git submodule update --remote
  ```
  > `MermaidFlow_Linter` 和 `weave_version_for_mermaidflow` 是两个 submodule，必须拉取。

### 第 4 步：安装 uv 包管理器

```bash
curl -LsSf https://astral.sh/uv/0.7.7/install.sh | sh
# 或使用 pip 安装
pip install uv
```

### 第 5 步：安装 Node.js 和 Mermaid CLI

```bash
# Node.js (LTS)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
```

验证：`mmdc --version`

### 第 6 步：安装 Python 依赖

```bash
cd MermaidFlow
uv sync
# 或 uv pip install -r <(uv export)
```

如果网络问题导致失败，设置 uv/pip 镜像后再试。

### 第 7 步：安装和配置 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
# 启动服务
ollama serve &
```

**拉取模型**（推荐 Qwen2.5:14b）：
```bash
# 先尝试直接拉取
ollama pull qwen2.5:14b

# 如果网络问题，可尝试设置代理
HTTPS_PROXY=http://localhost:7890 ollama pull qwen2.5:14b
```

> 备选模型：`qwen2.5:7b`（更轻量）、`qwen2.5:32b`（更强但显存占用 ~20GB @ Q4）

验证：`ollama run qwen2.5:14b "Hello"` 确认可用。

### 第 8 步：配置项目

修改 `config/config2.yaml`，将模型配置改为 Ollama：

```yaml
models:
  "qwen2.5:14b":
    api_type: "openai"
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"  # Ollama 不需要真实 key，但不能为空
    temperature: 0

llm:
  api_type: "openai"
  model: "qwen2.5:14b"
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
```

> 原始配置文件需要完整的 API key。Ollama 不验证 key，填任意非空字符串即可，但需确认项目使用的 litellm 库是否兼容此类配置。

### 第 9 步：处理 Weave 追踪

项目在 `run.py:125` 调用 `weave.init()`，需要 Weave 账号。

- [ ] 如用户有 wandb 账号：在服务器上 `wandb login` 输入 API key
- [ ] 如果不需要追踪：`export WANDB_MODE=disabled` 或在代码中跳过 weave.init
- [ ] 可能需要修改 `run.py` 将 weave.init 包裹在 try-except 中

### 第 10 步：运行测试

```bash
uv run python run.py --dataset GSM8K --opt_model_name qwen2.5:14b --exec_model_name qwen2.5:14b --max_rounds 5 --validation_rounds 2
```

先用小参数验证流程跑通，再增加 `--max_rounds`。

### 第 11 步：Git 同步配置

- [ ] 在服务器上配置 git 用户信息：
  ```bash
  git config user.email "your-email@example.com"
  git config user.name "Your Name"
  ```
- [ ] 如需 push，配置 GitHub 认证（推荐 Personal Access Token 或 SSH Key）
- [ ] 在服务器上生成 SSH Key 并添加到 GitHub：
  ```bash
  ssh-keygen -t ed25519 -C "your-email@example.com"
  cat ~/.ssh/id_ed25519.pub  # 添加到 GitHub Settings > SSH Keys
  ```

### 第 12 步：同步更改回仓库

在服务器上修改配置后：
```bash
git add config/config2.yaml  # 或其他修改的文件
git commit -m "Adapt config for Ollama local deployment"
git push origin main
```

> **注意**：不要提交包含真实 API Key 的配置文件。建议将 `config2.yaml` 加入 `.gitignore`，仅提交 `config2.example.yaml`。

## 潜在风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Ollama 模型性能远弱于 GPT-4o-mini | 优化结果可能不收敛 | 尝试更大的模型（32B）或多个模型组合，Qwen2.5:14b 推理能力接近 GPT-4o-mini |
| 24GB 显存不足（运行大模型时） | OOM | 使用 7B/14B 模型，设置 `--max_rounds` 较小值 |
| 本机代理不可达 | 无法下载依赖 | 使用 pip 清华镜像 + 手动下载 Ollama 模型文件 |
| litellm 对 Ollama 兼容性问题 | API 调用失败 | 检查 litellm 版本是否支持 Ollama provider，或升级 litellm |
| Weave 初始化失败 | 程序崩溃 | 修改 run.py 跳过 weave.init |
| MermaidFlow_Linter submodule 依赖 | 流程图渲染失败 | 确保 git submodule update --remote 成功 |

## 验证清单

- [ ] `nvidia-smi` 显示 RTX 4090 可用
- [ ] `mmdc --version` 正常输出
- [ ] `ollama list` 显示已拉取的模型
- [ ] `curl http://localhost:11434/v1/models` 返回 Ollama 模型列表
- [ ] `uv run python run.py --dataset GSM8K ...` 成功运行且无报错
- [ ] 输出目录 `workspace/` 有优化结果生成
- [ ] `git remote -v` 指向用户 GitHub 仓库
- [ ] `git push` 能成功将更改推送到 GitHub
