# 05. 支柱四 · 评估与质量闭环开发方案

> 版本：v2.0-dev-design（2026-07-16）
> 承接：[roadmap/06 支柱四](../../../roadmap/06-pillar-eval-quality.md)
> 覆盖里程碑：M-D1（冒烟门禁）、M-D2（Eval 框架+黄金集）、M-D3（跨版本回归）、M-D4（ROI 量化）、M-D5（反馈回流）
> 一句话：让"越用越好用"从口号变数据。**M-D1 与 [01 Q0] 并行启动**——它是防止"绿色单测掩盖红色主路径"的护栏，是 P0 以 GA 名义漏出的根治手段。
> 特殊使命：支柱四不是锦上添花，是飞轮的**信号源** + 支柱一三的**质量守门员**。

---

## 一、方案目标与对应里程碑

| 里程碑 | 目标 | 季度 | 主要落点 |
|---|---|---|---|
| M-D1 | 全 Profile 真实补全冒烟 CI 必绿 | Q1（与 Q0 并行） | `tests/smoke/`（新）·CI workflow |
| M-D2 | eval 框架 + 每 Stage 黄金集 ≥10 + LLM-as-judge | Q1 | `eval/`（新包）·`cli/eval_cmd.py`（新） |
| M-D3 | 跨版本回归，退化阻断发布 | Q3 | `eval/regression.py`（新） |
| M-D4 | ROI 量化（省时/降缺陷/加速发布） | Q4 | `eval/roi.py`（新）·`llm/cost.py` |
| M-D5 | 上线效果→决策效果分→agent 消费 | Q4 | `eval/feedback.py`（新）·与 [02 M-A6] 共建 |

---

## 二、现状锚点（真实代码）

| 关注点 | 文件:行 | 现状 |
|---|---|---|
| 测试 | `tests/`（45 文件 965 tests） | 验证"代码正确"，非"产物质量好" |
| 探活 | `llm/smoke.py` `smoke_test` | 已有真实最小补全；M-D1 扩为全 Profile 端到端 |
| 冒烟基础 | `cli/run_cmd.py` + `--dry-run` | 有 pipeline 编排；缺"真实补全跑完"的门禁 |
| cost 数据 | `state/schema.py:39` `llm_calls` 表 + `v_cost_daily` 视图 | ROI 成本侧数据源，依赖 [01 §3.8] pricing 修复 |
| 判据 | [02 M-A2] `acceptance_criteria` + `rule/` 548 规则 | reflect 判据 = judge 判据（复用） |
| 反馈现状 | `kb/memory.py` 反模式计数 | 计数式；M-D5 升级为效果加权（[02 M-A6] ADR.outcome） |
| 审计/Artifact | `audit/` + `artifacts` 表 | 黄金集/回归集的半自动抽取来源 |

---

## 三、逐里程碑工程方案

### 3.1 M-D1：端到端冒烟门禁（最高优先级，与 [01 Q0] 并行）

#### 3.1.1 问题直击

GA 发了主路径 100% 失败的版本，根因是**没有"真实调用 LLM 跑完一个 Pipeline"的发布门禁**。单测全绿掩盖主路径全红。

#### 3.1.2 四道门禁

| 门禁 | 内容 | 触发时机 | 落点 |
|---|---|---|---|
| 烟囱测试 | 用 Ollama（或真实）对每个 Profile 跑最小 Pipeline 到完成 | 每次 release 前 CI | `tests/smoke/test_all_profiles.py` |
| doctor 探活 | 已具备（[01] 核对表 #4） | 每次 `doctor` | `cli/doctor_cmd.py`（现状即可） |
| llm test | 已具备（[01] #5） | 用户配置后 | `cli/llm_cmd.py`（现状即可） |
| 错误可见性断言 | 断言 stage 失败时 error 冒泡终端（防"错误吞没"回归） | CI | `tests/smoke/test_error_visibility.py` |

#### 3.1.3 新增文件

| 文件 | 职责 |
|---|---|
| `tests/smoke/conftest.py` | Ollama fixture（本地零成本模型）+ 最小需求样例 |
| `tests/smoke/test_all_profiles.py` | 参数化 14 Profile，各跑一个最小 Pipeline，断言 `status==completed` |
| `tests/smoke/test_error_visibility.py` | 注入一个必失败 stage，断言终端输出含 error 首行 + 退出码 1 |
| `.github/workflows/smoke.yml` | CI：起 Ollama → 跑 smoke → 门禁 |

#### 3.1.4 关键实现

```python
# tests/smoke/test_all_profiles.py
import pytest
from sdlc.cli.deps import build_deps

PROFILES = ["new-feature", "bug-fix", "hotfix", "refactor", "test",
            "infra", "release", "doc", "migrate", "audit", ...]  # 全 14

@pytest.mark.smoke
@pytest.mark.parametrize("profile", PROFILES)
async def test_profile_completes_with_ollama(profile, ollama_env):
    deps = build_deps()  # 配置指向本地 Ollama
    result = await deps.coordinator.run(
        input_text=_minimal_input_for(profile),
        profile_id=profile,
    )
    assert result.status == "completed", (
        f"Profile {profile} failed: {result.error}"
    )
```

#### 3.1.5 关键约束

- **用本地 Ollama 做 CI 冒烟**：零成本、可复现、不依赖付费 key（完美契合开源定位）。
- 这是 [01 Q0] 修复的**验证手段**：修完 temperature/错误吞没后，冒烟保证不再回归。
- 门禁本身开源可复现，贡献者提 PR 能自己跑。

#### 3.1.6 验收

- [ ] 全 14 Profile 真实补全冒烟 CI 必过（`pytest -m smoke`）。
- [ ] 错误可见性断言通过（防错误吞没回归）。
- [ ] `sdlc doctor` 全绿 ⟺ `sdlc run` 能跑。

---

### 3.2 M-D2：Agent 产物 Eval 体系

#### 3.2.1 三层评估金字塔

```
L3 端到端 Pipeline eval    少量、真实场景、贵
L2 Stage-level eval        中量、每 Stage 产物打分（LLM-as-judge 为主）
L1 单元 eval               大量、快、便宜（规则/断言）
```

#### 3.2.2 新增文件（新包 `sdlc/eval/`）

| 文件 | 职责 |
|---|---|
| `sdlc/cli/eval_cmd.py` | `sdlc eval run/report` |
| `sdlc/eval/dataset.py` | 黄金集/回归集/对抗集加载（JSONL） |
| `sdlc/eval/judge.py` | LLM-as-judge：按维度打分（复用 [02] acceptance_criteria + Rule） |
| `sdlc/eval/runner.py` | 对数据集跑 Stage → 收集产物 → judge → 汇总 |
| `sdlc/eval/models.py` | `EvalCase`/`EvalResult`/`Score` schema |

#### 3.2.3 数据集格式

```jsonl
// eval/datasets/design.golden.jsonl  —— 每 Stage ≥10 例
{"id": "design-001", "stage": "design",
 "input": "加个订单查询接口，支持分页和按状态过滤",
 "context": {"adapter": "jd_spring_boot"},
 "ideal": {"criteria": ["接口含分页参数", "有状态过滤", "符合 REST 规范"]},
 "source": "maintainer"}
```

三类数据集（[roadmap/06 §5.2]）：
- **黄金集**：精选"输入→理想产物"对，人工标注，maintainer 维护。
- **回归集**：历史真实 Pipeline 输入 + 当时产物（审计/Artifact 半自动抽取，opt-in 脱敏）。
- **对抗集**：已知会出错的 case（P0 触发场景、边界需求，从事故/bug 沉淀）。

#### 3.2.4 LLM-as-judge

```python
# eval/judge.py
@dataclass
class Score:
    correctness: float      # 0..1
    completeness: float
    rule_compliance: float  # 遵守 Rule 库？
    kb_alignment: float     # 贴合 KB 上下文？
    overall: float
    rationale: str

class Judge:
    def __init__(self, judge_model: str): ...
    async def score(self, case: EvalCase, produced: str,
                    criteria: list[str], rules: list[dict]) -> Score: ...
```

- 用更强模型（可配 `judge_model`）按维度打分。
- **与 [02 M-A2] 复用**：reflect 判据 = judge 评分维度 = 同一套 `acceptance_criteria` + Rule 库。一次定义多处用。
- **judge 自校准**：judge 打分定期与人工标注对齐，一致率进 KPI（防"裁判也不准"）。

#### 3.2.5 向后兼容

- 全新包，不改既有代码。judge 复用 rule/stage 的现有数据，不新立标准。

#### 3.2.6 验收

- [ ] `sdlc eval run` 可跑；每 Stage 黄金集 ≥10 例。
- [ ] LLM-as-judge 打分产出"当前质量基线"报告。
- [ ] judge 与人工标注一致率 ≥ 85%。

---

### 3.3 M-D3：跨版本回归

#### 3.3.1 目标

任何改动（新版/新 prompt/新模型）都要证明"没让产物变差"。支柱一 agent 改进、支柱三市场扩展质量的**质量守门员**。

```
新版 sdlc / prompt / 模型
      ▼ 在黄金集 + 回归集跑 eval
对比基线版本分数
   ┌──────────┬───────────┐
   │ ↑或持平  │ ↓（回归）  │
   │ → 可发布 │ → 阻断+定位│
   └──────────┴───────────┘
```

#### 3.3.2 新增文件

| 文件 | 职责 |
|---|---|
| `sdlc/eval/regression.py` | 跑当前版 vs 基线版，产分数 diff + 阻断判定 |
| `sdlc/eval/baseline.py` | 基线分数存取（版本→分数快照） |
| `.github/workflows/eval-regression.yml` | release 前跑回归，退化则 fail |

#### 3.3.3 关键接口

```python
# eval/regression.py
@dataclass
class RegressionReport:
    baseline_version: str
    current_version: str
    per_stage_delta: dict[str, float]   # stage → 分数变化
    regressed: list[str]                # 显著下降的 stage
    passed: bool                        # 无显著回归

class RegressionRunner:
    def compare(self, threshold: float = -0.05) -> RegressionReport:
        """分数下降超 threshold 判定回归、阻断发布。"""
```

#### 3.3.4 验收

- [ ] 每次 release 附回归报告（100%）。
- [ ] 模拟一次质量退化能被阻断。

---

### 3.4 M-D4：ROI 量化

#### 3.4.1 目标

现有 CostTracker 只记 LLM 成本（且 [01 §3.8] 修前常为 0）。ROI 补收益侧。

| 维度 | 度量 | 数据来源 |
|---|---|---|
| 省时 | agent vs 人工基线时间差 | Stage 耗时 + 人工基线（团队标定） |
| 降缺陷 | 用 CR/test Stage 后逃逸缺陷变化 | 关联线上缺陷数 |
| 加速发布 | 需求上线周期变化 | Pipeline 时间线 + 部署记录 |
| 成本 | LLM 成本 + 人工审批时间 | `llm_calls` 表（[01 §3.8] 修复 pricing）+ Gate 耗时 |

#### 3.4.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/eval/roi.py` | 新增 | ROI 计算 + 报告 |
| `sdlc/llm/cost.py` | 依赖 | [01 §3.8] pricing 兜底必须先修，否则成本侧失真 |
| `sdlc/server/routes.py` | 扩展 | ROI 报告进 [03 M-B3] 控制台质量趋势视图 |

#### 3.4.3 关键约束

- **先决条件**：[01 §3.8] pricing 兜底修复（网关无 pricing → cost 恒 0 会让 ROI 成本侧全错）。
- ROI 数据**可脱敏共享**，让社区对比"sdlc 省了多少"（口碑/采用依据）。
- 人工基线难标定 → 团队自标 + 默认基线模板；先做相对趋势不追绝对值。

#### 3.4.4 验收

- [ ] CostTracker pricing 修复后，省时/降缺陷/加速发布可报告。
- [ ] ≥ 20 个团队能出 ROI 报告。

---

### 3.5 M-D5：反馈回流学习（与 [02 M-A6] 共建）

#### 3.5.1 目标

评估信号 + 上线效果 → 决策效果分 → 回流成 agent 改进，闭合飞轮。此处讲**信号产出**；agent **消费**见 [02 §3.6]。

```
eval 分数 + 上线效果 + 人类采纳信号
      ▼ 归因：哪个 decision/pattern/agent/prompt 导致
效果分写回 KB（ADR.outcome / 模式分）
      ▼ [02 M-A6] 消费：高分优先注入，低分规避
下一轮 eval 验证是否真变好 ──（闭环）
```

#### 3.5.2 新增文件

| 文件 | 职责 |
|---|---|
| `sdlc/eval/feedback.py` | 信号采集 + 归因 + 写 ADR.outcome/effect_score |
| `sdlc/kb/adr.py` | [02 M-A6] 定义；本里程碑负责**回写** outcome |

#### 3.5.3 信号来源

```
上线后信号（客观）        人类信号（主观）
├── 部署成功率            ├── Gate 通过/拒绝 + 理由
├── 上线后错误率变化       ├── 产物是否被采纳/改动幅度
├── 回滚事件             └── CR 中被指出的问题
└── 监控告警
        └────┬────────────┘
             ▼ 归因到 decision/pattern/agent
      ADR.outcome + effect_score（加权）
```

#### 3.5.4 关键约束（安全阀）

- **闭环必须验证**：反馈学习后必须用 M-D3 回归集验证"确实变好而非强化偏好"。
- **足够样本才生效**（[02 ADR.sample_count]）：单次信号不改行为，避免噪声驱动。
- 一次线上事故权重 > 三次无后果拒绝（effect_score 加权，非计数）。

#### 3.5.5 验收

- [ ] eval + 上线效果 → 效果分 → agent 消费全链路通。
- [ ] 回归验证产物不退化（M-D3 把关）。

---

## 四、依赖与顺序

```
M-D1 冒烟门禁 ══ 与 [01 Q0] 并行 ══ 保护 Q1+ 所有改动不回归
M-D2 eval 框架 ──→ M-D3 回归 ──→ M-D5 反馈回流（信号链）
M-D2 judge 判据 ══ 复用 ══ [02 M-A2 reflect 判据]（acceptance_criteria + Rule）
[01 §3.8 pricing] ──→ M-D4 ROI（成本侧数据源，硬前置）
M-D5 信号产出 ──→ [02 M-A6 agent 消费] ── M-D3 回归把关
```

**季度落位**：M-D1/M-D2（Q1 辅线，M-D1 与 Q0 并行）→ M-D3（Q3 辅线）→ M-D4/M-D5（Q4 主线）。

---

## 五、风险与缓解（工程视角）

| 风险 | 缓解 |
|---|---|
| LLM-as-judge 本身不准 | 定期与人工标注校准；一致率进 KPI；judge 用更强模型 |
| eval 成本高（每次烧钱） | 分层金字塔（L1 便宜量大，L3 少而精）；CI 用 Ollama |
| 回归集含敏感数据 | opt-in + 脱敏；黄金集用合成/公开数据 |
| 反馈学习强化错误偏好 | M-D3 回归验证 + sample_count 门槛（与 [02] 共守）|
| ROI 人工基线难标定 | 团队自标 + 默认基线模板；先做相对趋势 |
| pricing 未修导致 ROI 全错 | M-D4 硬依赖 [01 §3.8]，未修不启动 ROI |

---

## 六、支柱四小结

- **M-D1** 堵住 P0 漏出（GA 教训），与 Q0 并行。
- **M-D2 + M-D3** 让每次改动可度量、不退化。
- **M-D4** 向社区证明价值。
- **M-D5** 把评估信号变 agent 改进，闭合飞轮。

评估判据（acceptance_criteria + Rule）、成本数据源（llm_calls 表 + pricing）、反馈载体（ADR）三处都与其他支柱**共用**，是"一次投入多处受益"的典型。

---

返回：[00 导航](./00-README.md) · 上一篇：[04 支柱三 生态开放](./04-pillar-ecosystem.md)
