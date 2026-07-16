# 规范文档模板索引

本目录包含 SDLC 各阶段产出的标准文档模板。

## 模板清单

| 模板文件 | 适用阶段 | 说明 | 来源 |
| --- | --- | --- | --- |
| `backend-design.md` | s-design | 后端设计文档模板，包含15项检查维度 | [internal-docs](https://internal-doc.example/pages/q0CVxuZTX641rTrQmu66) |
| `release-checklist.md` | s-deploy | 上线计划与检查清单模板 | [internal-docs](https://internal-doc.example/pages/67slwhKZdxIjfD5OBaJ9) |

## 使用方式

模板通过 stage YAML 中的 `output_template` 字段引用：

```yaml
output_template: templates/backend-design.md
```

Stage runner 在执行时会加载模板作为输出格式参考，subagent 按模板结构产出文档。

## 模板变量

模板中 `{{variable}}` 格式的占位符在运行时由上下文自动填充：

| 变量 | 说明 | 来源 |
| --- | --- | --- |
| `requirement_name` | 需求名称 | PRD |
| `author` | 作者 | 当前用户 |
| `date` | 日期 | 系统时间 |
| `doc_url` | 文档链接 | 用户输入 |
| `release_title` | 上线主题 | 用户输入 |
| `ai_review_url` | AI评审链接 | 评审工具输出 |

## 新增模板

1. 在本目录创建 `.md` 文件
2. 使用 `{{variable}}` 占位符标记动态内容
3. 在对应 stage YAML 中配置 `output_template`
4. 更新本文件的模板清单
