---
description: 测试 - 依据设计验收标准与代码变更范围产出测试计划、补齐测试代码并跑出真实结果。转调 sdlc skill 的 test 阶段。
argument-hint: [可选:代码变更范围或设计文档路径]
allowed-tools: Read, Write, Edit, Bash, Skill
---

# SDLC 测试

请执行 `sdlc` skill 的 **test（测试）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill。
2. 先读 `references/profiles.md` 了解测试框架惯例（pytest/junit/jest/go test 等），照项目已有测试模式来。
3. 读 `references/test.md`，严格按其骨架执行；用 `templates/test-plan.md` 组织测试计划。
4. 从设计的验收标准和 git diff 推导用例矩阵（正常/边界/异常/回归），补齐测试代码并**真实运行**，不谎报结果。
5. 用户输入 `$ARGUMENTS` 作为代码变更范围或设计文档路径。
6. 产物写入 `.sdlc/05-test/00-<需求名>.md`（`<需求名>` 沿用设计的需求名，勿用 `test-plan` 通用词；命名规约见 skill），含实际运行结果摘要（通过数/失败数/覆盖率）。

> 本命令是薄封装：测试范围推导与用例组织以 `sdlc` skill 为**单一来源**，此文件不重复维护。
