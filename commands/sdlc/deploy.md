---
description: 上线计划与检查清单生成 - 分析变更范围,产出配置修改/上线回滚步骤/上线后检查清单,按画像裁剪检查项。转调 sdlc skill 的 deploy 阶段。
---

# SDLC 上线计划

请执行 `sdlc` skill 的 **deploy（上线计划）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill。
2. 先读 `references/profiles.md` 探测画像,得出上线检查清单启用的标签。
3. 读 `references/deploy.md`,严格按其骨架执行;用 `templates/release-plan.md` 组织。
4. 用户输入 `$ARGUMENTS` 作为设计文档路径、数字前缀（如 `01`，选中 `02-design/01-*.md`）或变更说明;分析 git diff 确定变更范围。
5. 产物写入 `.sdlc/06-deploy/00-<需求名>.md`（`<需求名>` 沿用设计的需求名，勿用 `release-plan` 通用词；命名规约见 skill）。

> 本命令是薄封装:上线清单与裁剪规则以 `sdlc` skill 为**单一来源**,此文件不重复维护,也不硬编码任何模板绝对路径。
