# 01. Q0 主路径加固开发方案

> 版本：v2.0-dev-design（2026-07-16）
> 承接：[roadmap/07 §三](../../../roadmap/07-roadmap-4q.md)（Q0 前置门槛）、[roadmap/01 §二·五](../../../roadmap/01-product-assessment.md)（主路径断裂红线）
> 目标：让端到端 `sdlc run` 从"实测失败"变为"稳定通过"，且 `doctor`/`llm test` 不再假绿。
> 时机：Q1 前 2–3 周，是一切支柱新功能的准入门槛。

---

## 一、重要前提：先核对现状，别重复劳动

规划文档写于问题暴露时；随后 commit **`3dc05d0`（fix: thread configured temperature/max_tokens…）已落地大部分 P0/P1 修复**。动工前先对齐这张核对表，只做真正剩余的工作。

> **本节已按 main@`3dc05d0` 复核（2026-07-16）**。该 commit 把 `#1/#2/#4/#5/#6/#7` 全部实现，仅 `#3/#8` 尚有剩余；另新增了与本门槛无关的 `sdlc template` 命令（见 §一·补）。

| # | roadmap 任务 | 现状（代码核对 @`3dc05d0`） | 剩余工作 |
|---|---|---|---|
| 1 | temperature 从 config 贯穿到 provider | ✅ **已修**：`llm/client.py:64` `_prepare()` 注入；`anthropic_provider.py:63` 仅当非 None 才传；`CompletionRequest.temperature/max_tokens` 默认 None（`llm/models.py:49`） | 回归测试固化（已随 commit 加 `tests/test_llm_client_inject.py`） |
| 2 | stage error 冒泡到终端 | ✅ **已修**：`cli/run_cmd.py:154-168` 打印 failed stages 首行 + `SystemExit(1)`；coordinator 填 `PipelineResult.error`；runner 持久化 stage error | 断言化（防回归） |
| 3 | 400 类错误可重试/fallback | ⚠️ **部分**：`client.py:90` 捕获 `LLMError` 即切 fallback，但**参数类 400 会误切到另一 provider**，且无"同 provider 修正重试" | **本方案 §三.3（仍需做）** |
| 4 | doctor 真实探活 | ✅ **已修**：`cli/doctor_cmd.py:37` 调 `smoke.smoke_test()` 发真实补全 + 连通性检查（`--no-check-llm` 跳过） | — |
| 5 | llm test 发真实请求 | ✅ **已修**：`cli/llm_cmd.py` `llm_test` 调 `smoke_test()` | — |
| 6 | 配置路径统一 | ✅ **已修**：`cli/init_cmd.py` 改写 `.sdlc/ext/config.yaml`（`load_config()` 实际读取路径），废弃从未被读的 `.sdlc/config.toml` | — （§三.6 变为"实现说明/回归验证"）|
| 7 | CWD 包加载校验 | ✅ **已修**：`cli/main.py` `_warn_if_shadowed()`——用**已装版本 vs 载入版本比对**（比我原提的路径比对更稳），不匹配即 warning | — （§三.7 变为"实现说明"）|
| 8 | CostTracker pricing 缺失 | ⚠️ **半修**：`anthropic_provider.py:139` pricing 缺失时 `warning + cost=0`，**仍无兜底估算** | **本方案 §三.8（仍需做）** |

> 结论（已更新）：**真正剩余的核心工作收敛为 #3（400 分流）与 #8（pricing 兜底）两项**；#1/#2/#4/#5/#6/#7 已在 `3dc05d0` 落地，转为"补回归测试防复发"，由 [05 M-D1 冒烟门禁](./05-pillar-eval-quality.md) 承接。§三.6/§三.7 保留作**实现说明与回归验证清单**（方案与实现略有差异，见各节头注）。

### 一·补：commit `3dc05d0` 附带的非门槛变更（新增能力，需登记）

该 commit 还引入了一个**本 Q0 门槛之外**的新特性，本方案原未覆盖，登记于此以免遗漏：

- **`sdlc template` 命令**（`cli/template_cmd.py` + `builtin/templates/`）：可移植地定位/打印内置 `backend-design`/`release-checklist` 模板，替代 slash 命令里的硬编码绝对路径。模板已改为技术中立 + 适用性说明。
- 归属：这属于[04 支柱三 · 生态/贡献者工具链](./04-pillar-ecosystem.md) 的范畴（降低"照模板产出"门槛），而非 Q0 稳定性。后续若做 [M-C1 插件 SDK]，`template` 命令可并入其脚手架体系统一管理。

---

## 二、现状锚点（真实代码）

| 关注点 | 文件:行 | 现状要点 |
|---|---|---|
| 默认注入 | `sdlc/llm/client.py:64-84` `MultiLLMClient._prepare` | 路由 model；`max_tokens`/`temperature` 为 None 时注入配置默认，temperature 仍 None 则省略 |
| fallback 分支 | `sdlc/llm/client.py:86-93` | `except (LLMRateLimitError, LLMTimeoutError, LLMError)` → 有 fallback 就切，否则 raise |
| Anthropic 参数组装 | `sdlc/llm/anthropic_provider.py:57-70` | `temperature` 仅当非 None 传入；`APIError → LLMError` |
| pricing 计算 | `sdlc/llm/anthropic_provider.py:138-150` `_to_response` | pricing 缺失 → `cost=0` + warning |
| cost 记账 | `sdlc/llm/cost.py:33` `CostTracker.record` | 累加 `_session_cost`，超预算 raise `BudgetExceededError` |
| 配置模型 | `sdlc/utils/config.py:6-20` `LLMConfig` | `temperature: float\|None = 0.7`，含 fallback_* 字段 |
| 探活 | `sdlc/llm/smoke.py` `smoke_test` | 发 `max_tokens=8` 的 "ping"，返回 `(ok, detail)` |

---

## 三、逐任务工程方案

### 3.3 400 类错误：区分"可切换" vs "需修正" vs "致命"

**问题**：当前 `client.py:90` 把所有 `LLMError`（含 Anthropic `APIError` 4xx）一律当作"切 fallback"。但一个 `400 invalid temperature` 属于**参数问题**——切到另一个 provider 治标不治本，且可能把 Anthropic 的问题请求原样丢给 OpenAI 兼容端点，触发二次错误、掩盖根因。

**方案**：在 provider 层细分异常，在 client 层分流处理。

#### 3.3.1 新增异常类型（`sdlc/llm/anthropic_provider.py` 顶部，与既有 `LLMRateLimitError` 并列）

```python
class LLMBadRequestError(LLMError):
    """4xx 参数/请求错误。可能通过调整参数在同一 provider 修正，
    不应盲目切换到 fallback provider。"""
    def __init__(self, message: str, *, param: str | None = None) -> None:
        super().__init__(message)
        self.param = param  # 若能从错误体解析出冲突字段（如 "temperature"）


class LLMAuthError(LLMError):
    """401/403 鉴权错误。配置问题，不重试、不 fallback，直接失败。"""
```

映射（改 `anthropic_provider.py:76` 的 `except anthropic.APIError`）：

```python
except anthropic.AuthenticationError as e:
    raise LLMAuthError(str(e)) from e
except anthropic.BadRequestError as e:
    raise LLMBadRequestError(str(e), param=_extract_param(e)) from e
except anthropic.APIError as e:
    raise LLMError(str(e)) from e
```

`openai_compatible.py` / `openai_provider.py` 做等价映射（`openai.BadRequestError` / `openai.AuthenticationError`）。

#### 3.3.2 client 层分流（`sdlc/llm/client.py` `complete`）

```python
async def complete(self, req: CompletionRequest) -> CompletionResponse:
    prepared = self._prepare(req)
    try:
        return await self.primary.complete(prepared)
    except LLMAuthError:
        raise  # 配置错误：不重试不 fallback，让错误冒泡到终端
    except LLMBadRequestError as e:
        # 先尝试同 provider 参数修正（一次），失败再考虑 fallback
        retried = self._strip_conflicting_param(prepared, e.param)
        if retried is not None:
            return await self.primary.complete(retried)
        if self.fallback is not None:
            return await self.fallback.complete(prepared)
        raise
    except (LLMRateLimitError, LLMTimeoutError, LLMError):
        if self.fallback is not None:
            return await self.fallback.complete(prepared)
        raise
```

`_strip_conflicting_param(req, param)`：当 `param == "temperature"` 时返回 `req.model_copy(update={"temperature": None})`（让 provider 省略该字段）；无法识别的 param 返回 `None`（不盲目重试）。

#### 3.3.3 向后兼容

- 新异常均继承 `LLMError`，既有"广义捕获"逻辑不受影响。
- 未识别的 400 仍按原路径 fallback，行为不回退。

#### 3.3.4 测试要点

- `respx` mock 一个返回 `400 temperature` 的 Anthropic 响应 → 断言：**先在 primary 去掉 temperature 重试**，不直接打 fallback。
- mock `401` → 断言 `LLMAuthError` 冒泡、**未调用** fallback。
- mock `429` → 断言走 fallback（行为不变）。

---

### 3.6 配置路径统一（✅ 已在 `3dc05d0` 实现 —— 本节转为实现说明 + 回归验证）

> 状态更新：此项**已修复**。`cli/init_cmd.py` 现改写 `.sdlc/ext/config.yaml`——即 `load_config()` 项目层实际读取的路径，并废弃了从未被任何代码读取的 `.sdlc/config.toml`（旧实现写 TOML、loader 读 YAML，正是分叉根因）。

**实现要点（已落地）**：
- 写入：`init` → `.sdlc/ext/config.yaml`，用 `utils/yaml_io.save_yaml`，且 config 结构对齐 `SdlcConfig`（`profile` 为 mapping）。
- 读取：`load_config()` 的项目层就是 `.sdlc/ext/`，二者一致。

**仍建议补的回归测试**（防再次分叉）：
- `init` 后立刻 `load_config()`，断言读到的 `model`/`provider`/`adapter` == init 写入值。
- 断言 `.sdlc/config.toml` 不再生成。

> 备注：我原提议抽 `config_search_path()`/`default_config_write_path()` 单一真源函数。实现选择了更直接的"直接写正确路径"方案，已解决问题；若未来出现第三处配置读写点，仍建议按单一真源函数收口。

---

### 3.7 CWD 包加载校验（✅ 已在 `3dc05d0` 实现 —— 方案与实现有差异，记录于此）

> 状态更新：此项**已修复**，且实现比我原提议更稳。`cli/main.py` 的 `_warn_if_shadowed()` 在 `cli()` 回调开头调用。

**实现要点（已落地）**：实现用 **"已安装分发版本 vs 载入包版本"比对**，而非我原提的"包目录路径 == CWD/sdlc"比对：

```python
# 实际实现（cli/main.py）
from importlib.metadata import version as dist_version
from sdlc import __version__ as loaded_version
if dist_version("sdlc") != loaded_version:
    # 打印 warning：CWD 下 stale 'sdlc/' 正遮蔽已装版本
```

**为什么实现方案更好**：版本比对能捕获"CWD 旧包版本 ≠ 已装版本"的真实危害场景，且不会对"开发者在源码树正常工作且版本一致"误报——比路径比对更精准。**采纳实现方案，废弃我原提的路径比对版本。**

**仍建议补的回归测试**：造一个 `__version__` 不同的假 `sdlc/` 包在 CWD，断言 warning 触发；版本一致时不触发。

---

### 3.8 CostTracker pricing 缺失兜底（也服务 Q4 ROI）

**问题**：自定义网关/三方模型没有 pricing 条目时，`_to_response` 令 `cost=0`。结果：`stats` 成本恒 0、预算门控失效、ROI 成本侧失真（[roadmap/06 §六](../../../roadmap/06-pillar-eval-quality.md)）。

**方案**：三级兜底 —— 精确 pricing → 家族匹配 → token 估算。

#### 3.8.1 新增 `sdlc/llm/pricing.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Price:
    input_per_m: float   # $ / 1M input tokens
    output_per_m: float

# 家族前缀匹配（自定义网关常用 "claude-3-5-sonnet-xxxx" 这类变体名）
_FAMILY_PREFIX: dict[str, Price] = {
    "claude-opus":   Price(15.0, 75.0),
    "claude-sonnet": Price(3.0, 15.0),
    "claude-haiku":  Price(0.80, 4.0),
    "gpt-4o-mini":   Price(0.15, 0.60),
    "gpt-4o":        Price(5.0, 15.0),
}

# 未知模型的保守估算（宁可高估以触发预算保护，不低估到 0）
_FALLBACK_ESTIMATE = Price(3.0, 15.0)  # 按 sonnet 档估

def resolve_price(model: str, exact: dict[str, dict[str, float]] | None = None) -> tuple[Price, str]:
    """返回 (价格, 来源标签)。来源 ∈ {exact, family, estimate} 供审计与显示。"""
    if exact and model in exact:
        p = exact[model]
        return Price(p["in"], p["out"]), "exact"
    for prefix, price in _FAMILY_PREFIX.items():
        if model.startswith(prefix):
            return price, "family"
    return _FALLBACK_ESTIMATE, "estimate"
```

#### 3.8.2 改 `anthropic_provider._to_response`（及 openai 系）

```python
from sdlc.llm.pricing import resolve_price

price, source = resolve_price(raw.model, self.PRICING)
cost = (usage.input_tokens * price.input_per_m
        + usage.output_tokens * price.output_per_m) / 1_000_000
# source == "estimate" 时打 info 日志，并在 CompletionResponse.metadata 标注
```

`CompletionResponse` 增加可选字段 `cost_source: str = "exact"`（`llm/models.py`），供 `stats`/ROI 区分"实测成本"与"估算成本"，避免把估算当精确值误报。

#### 3.8.3 向后兼容

- 已有 `PRICING` dict 仍是第一优先级，精确命中行为不变。
- 新字段 `cost_source` 有默认值，旧序列化数据可正常反序列化。

#### 3.8.4 测试要点

- 未知模型名 → 断言 `cost > 0` 且 `cost_source == "estimate"`。
- 变体名 `claude-3-5-sonnet-20999999` → 断言命中 `family`。
- 精确名 → 断言 `exact` 且金额与旧逻辑一致（回归）。

---

## 四、验收标准（准入 Q1 的硬门槛）

对齐 [roadmap/07 §三](../../../roadmap/07-roadmap-4q.md)，逐条可勾选（勾选状态已按 main@`3dc05d0` 更新）：

- [ ] 干净测试仓库中，`sdlc run "加个订单查询接口"` 用真实模型跑到 `completed`（≥ 1 个 Profile 全流程）—— **待端到端实测确认**。
- [ ] 参数类 400 先在同 provider 修正重试，不盲目 fallback；401 直接冒泡不 fallback（§3.3，**仍需做**）。
- [ ] 自定义网关模型的 `cost_usd > 0`，`stats` 不再恒 0，预算门控生效（§3.8，**仍需做**）。
- [x] `init` 写入路径 == `load_config` 读取路径（§3.6，`3dc05d0` 已修；待补回归测试）。
- [x] CWD 包遮蔽有可见 warning（§3.7，`3dc05d0` 已修；待补回归测试）。
- [x] `sdlc doctor` 发真实补全探活（不再假绿）—— `3dc05d0` 已修；`doctor` 全绿 ⟺ `run` 能跑仍需 [05 M-D1] 冒烟门禁共同保证。
- [x] 任一 stage 失败时，终端可见根因首行 —— `3dc05d0` 已修；补断言防回归（[05 M-D1]）。

> 净剩硬门槛：**§3.3（400 分流）+ §3.8（pricing 兜底）+ 端到端实测 + 补齐回归测试**。

---

## 五、依赖与顺序

```
§3.8 pricing 兜底 ──→ 直接服务 [05 M-D4 ROI]（成本侧数据源）
§3.3 400 分流   ──→ 提升 [05 M-D1 冒烟门禁] 的错误可见性质量
§3.6/§3.7        ──→ ✅ 已在 3dc05d0 完成，仅剩补回归测试
```

- **本方案与 [05 M-D1 冒烟门禁] 并行推进**：本方案"治标"（修 bug），M-D1"防复发"（真实补全冒烟进 CI）。两者一起才算 Q0 真正通过。
- 建议提交顺序（更新后）：**§3.8（pricing，牵连 cost/stats）→ §3.3（异常分流，牵连 fallback 回归）→ 补 §3.6/§3.7 回归测试 → 端到端实测**。§3.6/§3.7 主体已由 `3dc05d0` 完成。小步提交，每步补测试。

---

## 六、风险与缓解

| 风险 | 缓解 |
|---|---|
| 异常分流改动牵连 fallback 回归 | 先补 §3.3 三个 mock 测试锁定行为，再改分支 |
| pricing 估算值与真实值偏差 | 估算标 `cost_source=estimate`，UI/报告显式区分；家族表覆盖主流模型降低落到估算的概率 |
| 家族前缀匹配误命中（如某网关用 `claude-sonnet` 前缀跑的其实是别的模型） | 前缀表仅作兜底；用户可在 config 显式配 pricing 覆盖（第一优先级） |
| §3.6/§3.7 已实现但缺回归测试，未来可能回归 | 补 §3.6/§3.7 各自的回归测试，纳入 [05 M-D1] 门禁 |

---

返回：[00 导航](./00-README.md) · 下一篇：[02 支柱一 Agent 智能化](./02-pillar-agent-intelligence.md)
