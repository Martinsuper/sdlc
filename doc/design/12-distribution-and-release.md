# 12. 分发与发布 (v1.0)

> uv 打包 + Homebrew + PyPI + 版本策略

---

## 一、整体策略

| 渠道 | 形式 | 适用 |
|---|---|---|
| **PyPI** | `pip install sdlc` / `uv add sdlc` | 通用 Python 用户 |
| **Homebrew** | `brew install sdlc` | macOS / Linux 开发者 |
| **GitHub Release** | tar.gz / zip | 高级用户、CI |
| **Docker** | `docker run sdlc/sdlc` | 容器化环境 |
| **pipx** | `pipx install sdlc` | 隔离全局工具 |

---

## 二、Python 打包

### 2.1 pyproject.toml

```toml
[build-system]
requires = ["hatchling>=1.21"]
build-backend = "hatchling.build"

[project]
name = "sdlc"
version = "0.1.0"
description = "AI-driven full-lifecycle SDLC orchestrator"
readme = "README.md"
license = {text = "Apache-2.0"}
authors = [
    {name = "duanluyao1", email = "..."},
]
keywords = ["sdlc", "ai", "orchestration", "pipeline", "lifecycle"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development",
]
requires-python = ">=3.11"
dependencies = [
    "click>=8.1.7",
    "rich>=13.7.1",
    "pydantic>=2.6.4",
    "ruamel.yaml>=0.18.6",
    "jinja2>=3.1.3",
    "httpx>=0.27.0",
    "anthropic>=0.34.2",
    "openai>=1.30.1",
    "anthropic-sdk-helper>=0.1.0",  # 内部 SDK
    # ...
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.6",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.14.0",
    "pytest-benchmark>=4.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "freezegun>=1.5.0",
    "respx>=0.21.0",
    "hypothesis>=6.100.0",
    "syrupy>=4.6.0",
    "pre-commit>=3.7.0",
    "mutmut>=3.0.0",
    "ipython>=8.23.0",
]
docs = [
    "mkdocs>=1.6.0",
    "mkdocs-material>=9.5.0",
    "mkdocstrings[python]>=0.25.0",
]
perf = [
    "asv>=0.6.3",
    "locust>=2.26.0",
]

[project.scripts]
sdlc = "sdlc.cli:main"

[project.urls]
Homepage = "https://github.com/duanluyao1/sdlc"
Documentation = "https://sdlc.dev/docs"
Repository = "https://github.com/duanluyao1/sdlc"
Issues = "https://github.com/duanluyao1/sdlc/issues"
Changelog = "https://github.com/duanluyao1/sdlc/blob/main/CHANGELOG.md"

[tool.hatch.build.targets.wheel]
packages = ["sdlc"]

[tool.hatch.build.targets.wheel.shared-data]
"sdlc/builtin" = "sdlc/builtin"
"templates" = "templates"

[tool.hatch.build.targets.wheel.force-include]
"README.md" = "sdlc_README.md"
"LICENSE" = "sdlc_LICENSE"

[tool.hatch.build.targets.sdist]
exclude = [
    ".github",
    "tests",
    "docs",
    "*.egg-info",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    "perf-results",
]
```

### 2.2 入口点

```python
# sdlc/cli/__init__.py
from sdlc.cli.main import main

if __name__ == "__main__":
    main()
```

```python
# sdlc/cli/main.py
import click
from sdlc.cli.commands import run, init, status, resume, ...

@click.group()
@click.version_option()
@click.option("--verbose", "-v", count=True)
@click.option("--config", type=click.Path(), help="Config file path")
@click.option("--home", type=click.Path(), help="Override SDLC_HOME")
@click.option("--no-color", is_flag=True)
@click.pass_context
def main(ctx, verbose, config, home, no_color):
    """SDLC: AI-driven full-lifecycle software development orchestrator."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config
    ctx.obj["home"] = home
    ctx.obj["no_color"] = no_color
    # 初始化 context...

main.add_command(run.cmd)
main.add_command(init.cmd)
main.add_command(status.cmd)
# ... 19 命令
```

安装后：
```bash
$ which sdlc
~/.local/bin/sdlc

$ sdlc --version
sdlc 0.1.0 (Python 3.12.2)

$ sdlc run --help
Usage: sdlc run [OPTIONS]
  ...
```

### 2.3 静态文件

```python
# sdlc/__init__.py
from importlib.resources import files

BUILTIN_DIR = files("sdlc") / "builtin"
TEMPLATE_DIR = files("sdlc") / "templates"

# 加载内置
def load_builtin_subagents():
    for f in (BUILTIN_DIR / "subagents").glob("*.yaml"):
        yield Subagent.from_yaml(f.read_text())
```

---

## 三、版本策略

### 3.1 SemVer

```
<major>.<minor>.<patch>[-<pre>]
```

- `major`：breaking change
- `minor`：新功能（向后兼容）
- `patch`：bug 修复
- `pre`：alpha / beta / rc

### 3.2 版本节奏

| 阶段 | 频率 | 内容 |
|---|---|---|
| Alpha | 每周 | 新功能，API 不稳定 |
| Beta | 每 2 周 | 候选功能，API 稳定 |
| RC | 必要 | 修复 bug，准备 GA |
| GA / Patch | 必要 | 修复 bug，安全更新 |
| Minor | 每月 | 新功能 |
| Major | 半年 | breaking change |

### 3.3 当前路线

```
0.1.0 (M1) → 0.2.0 (M2) → 0.3.0 (M3) → 0.4.0 (M4) → 1.0.0 (GA)
2026-06      2026-08      2026-10      2026-12      2027-02
```

### 3.4 版本管理

`pyproject.toml` 中 `version` 用 `dynamic`：

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "sdlc/__init__.py"
pattern = "__version__ = \"{version}\""
```

`sdlc/__init__.py`：
```python
__version__ = "0.1.0"
```

---

## 四、CHANGELOG

### 4.1 格式（Keep a Changelog）

```markdown
# Changelog

## [Unreleased]

## [0.1.0] - 2026-06-XX

### Added
- 6 个内置 Stage（clarify/design/implement/test/deploy/feedback）
- 5 个内置 Subagent
- 18 个 Adapter（dongboot/python/nestjs/...）
- DongBoot 检测与自动迁移
- SQLite + JSON 状态持久化
- 12h Resume
- 审计日志
- `sdlc run` / `init` / `status` / `resume` 等 19 个 CLI 命令
- Project Profile 引擎（14 profile）
- Pipeline Builder
- Gate 引擎（10 gate）
- KB Engine（scanner + writer + reconciler）
- LLM 缓存（30%+ 命中率）
- Cost 跟踪

### Fixed
- 无（M1 首发）

### Security
- API key 走环境变量 / keyring
- DB 文件 600 权限
- 文件路径校验
```

### 4.2 自动生成

```bash
# git-cliff 风格
uv run git-cliff --tag 0.1.0 > CHANGELOG.md

# 或 conventional commits + release-please（GitHub Action）
```

### 4.3 提交规范（Conventional Commits）

```
feat: add dongboot adapter
fix: resume token validation
docs: update README
test: add e2e test for clarify stage
refactor: extract kb writer
perf: cache llm responses
chore: update deps
```

→ 自动 binternal-monitoring version（release-please） + 自动写 CHANGELOG。

---

## 五、发布流程

### 5.1 手工

```bash
# 1. 升版本
uv run binternal-monitoring-my-version binternal-monitoring minor  # 0.1.0 → 0.2.0

# 2. 跑测试
uv run pytest

# 3. 构建
uv build

# 4. 检查产物
ls dist/
# sdlc-0.2.0-py3-none-any.whl
# sdlc-0.2.0.tar.gz

# 5. 上传 PyPI（用 twine 或 uv publish）
uv publish

# 6. 创建 GitHub Release
gh release create v0.2.0 dist/*

# 7. 更新 Homebrew formula（PR 到 homebrew-core）
gh pr create --repo Homebrew/homebrew-core \
  --title "sdlc 0.2.0" \
  --body-file homebrew-pr.md

# 8. 构建 Docker
docker build -t sdlc/sdlc:0.2.0 -t sdlc/sdlc:latest .
docker push sdlc/sdlc:0.2.0
docker push sdlc/sdlc:latest
```

### 5.2 自动（推荐）

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]

permissions:
  id-token: write  # trusted publishing
  contents: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          release-type: python
          package-name: sdlc
    outputs:
      release_created: ${{ steps.release.outputs.release_created }}
      tag_name: ${{ steps.release.outputs.tag_name }}

  publish:
    needs: release-please
    if: ${{ needs.release-please.outputs.release_created }}
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install uv
      - run: uv build
      - run: uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_TOKEN }}

  docker:
    needs: release-please
    if: ${{ needs.release-please.outputs.release_created }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            sdlc/sdlc:${{ needs.release-please.outputs.tag_name }}
            sdlc/sdlc:latest

  homebrew:
    needs: release-please
    if: ${{ needs.release-please.outputs.release_created }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ./scripts/update-homebrew.sh ${{ needs.release-please.outputs.tag_name }}
        env:
          HOMEBREW_TAP_TOKEN: ${{ secrets.HOMEBREW_TAP_TOKEN }}
```

---

## 六、Homebrew Formula

### 6.1 formula

```ruby
# Formula/sdlc.rb
class Sdlc < Formula
  desc "AI-driven full-lifecycle SDLC orchestrator"
  homepage "https://github.com/duanluyao1/sdlc"
  url "https://github.com/duanluyao1/sdlc/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "..."
  license "Apache-2.0"

  depends_on "python@3.12"

  resource "pip" do
    url "https://files.pythonhosted.org/packages/source/p/pip/pip-24.0.tar.gz"
    sha256 "..."
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"sdlc", "--version"
  end
end
```

### 6.2 自动化更新

`scripts/update-homebrew.sh`：
```bash
#!/usr/bin/env bash
set -euo pipefail

TAG=$1
VERSION=${TAG#v}
URL="https://github.com/duanluyao1/sdlc/archive/refs/tags/${TAG}.tar.gz"
SHA=$(curl -sL "$URL" | shasum -a 256 | awk '{print $1}')

# 更新 homebrew-tap 仓库
git clone https://x-access-token:$HOMEBREW_TAP_TOKEN@github.com/duanluyao1/homebrew-tap.git
cd homebrew-tap
sed -i.bak "s|url \".*\"|url \"$URL\"|" Formula/sdlc.rb
sed -i.bak "s|sha256 \".*\"|sha256 \"$SHA\"|" Formula/sdlc.rb
sed -i.bak "s|v[0-9]*\.[0-9]*\.[0-9]*|v$VERSION|" Formula/sdlc.rb
git add Formula/sdlc.rb
git commit -m "sdlc $VERSION"
git push
```

---

## 七、Docker

### 7.1 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

LABEL org.opencontainers.image.title="SDLC"
LABEL org.opencontainers.image.description="AI-driven full-lifecycle SDLC orchestrator"
LABEL org.opencontainers.image.source="https://github.com/duanluyao1/sdlc"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY sdlc/ ./sdlc/
COPY templates/ ./templates/
COPY README.md LICENSE ./

# 安装（不缓存 venv，编译期完成）
RUN uv sync --no-dev --frozen

# 运行
ENTRYPOINT ["uv", "run", "sdlc"]
CMD ["--help"]
```

### 7.2 docker-compose（开发）

```yaml
# docker-compose.yml
services:
  sdlc:
    build: .
    volumes:
      - .:/workspace
      - sdlc-home:/home/sdlc/.sdlc
    working_dir: /workspace
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    env_file:
      - .env
volumes:
  sdlc-home:
```

### 7.3 多架构

```yaml
# .github/workflows/release.yml 中
- uses: docker/setup-qemu-action@v3
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v5
  with:
    platforms: linux/amd64,linux/arm64
    push: true
    tags: sdlc/sdlc:${{ tag }}
```

---

## 八、文档站

### 8.1 mkdocs

```yaml
# mkdocs.yml
site_name: SDLC
site_url: https://sdlc.dev
repo_url: https://github.com/duanluyao1/sdlc

theme:
  name: material
  palette:
    primary: indigo
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - search.suggest
    - content.code.copy

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
            show_source: true

nav:
  - Home: index.md
  - Getting Started:
    - install.md
    - quickstart.md
    - tutorial.md
  - User Guide:
    - concepts.md
    - cli.md
    - profiles.md
    - adapters.md
  - Reference:
    - stages.md
    - subagents.md
    - rules.md
    - gates.md
  - Developer Guide:
    - architecture.md
    - extending.md
    - contributing.md
  - Changelog: changelog.md
```

### 8.2 自动部署

```yaml
# .github/workflows/docs.yml
name: Docs

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install uv && uv sync --all-extras
      - run: uv run mkdocs gh-deploy --force
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

→ 部署到 `https://sdlc.dev`（GitHub Pages + 自定义域名）。

---

## 九、签名与校验

### 9.1 PyPI 签名

启用 PyPI trusted publishing（OIDC），无需手动管理 token。

### 9.2 Git Tag 签名

```bash
git tag -s v0.2.0 -m "Release 0.2.0"
```

### 9.3 Docker 签名

```yaml
- uses: sigstore/cosign-installer@v3
- uses: docker/build-push-action@v5
  with:
    provenance: true
    sbom: true
```

---

## 十、回滚

### 10.1 PyPI

```bash
# yank（不删，但默认不安装）
uv run twine yank sdlc==0.2.0

# 真正回滚：发新版本
uv run binternal-monitoring-my-version binternal-monitoring patch
```

### 10.2 Homebrew

```bash
# revert formula
git revert <commit>
```

### 10.3 Docker

```bash
# tag 旧版本
docker pull sdlc/sdlc:0.1.0
```

### 10.4 灰度

- 标记 pre-release（alpha/beta/rc），不强制
- GA 后保留 major.minor 兼容

---

## 十一、升级指南

### 11.1 自动迁移

```bash
sdlc upgrade --from 0.1.0 --to 0.2.0
```

**功能**：
- 备份 `.sdlc/` 到 `~/.sdlc/backups/<timestamp>/`
- 迁移 SQLite schema
- 迁移 KB 文件结构（如有变化）
- 迁移 config.toml 字段
- 报告迁移结果

### 11.2 手动迁移

CHANGELOG 列 breaking change + 升级命令。

---

## 十二、监控发布后

### 12.1 指标

- PyPI 下载量：`pypistats.org`
- GitHub stars / forks
- Issue 数 / close 时间
- 首次成功跑通率（通过 telemetry，可选）

### 12.2 错误监控（可选）

```python
# 集成 Sentry
# 仅在用户明确启用时
sdlc config set telemetry.sentry_dsn https://...
```

---

## 十三、版本

- v1.0 (2026-06-05): 初版
