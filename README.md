# astrbot-plugin-qq-identifier

基于 QQ 号识别用户的 AstrBot 插件。通过 `on_llm_request` 钩子在 LLM 生成回复前将用户身份信息注入到 system_prompt 中，让 LLM 能够基于 QQ 号来识别对话者，而非依赖昵称。

## 核心机制

当用户发送消息时，插件会将对话者的用户信息（名称、QQ号、标签、备注）注入到 LLM 请求的 system_prompt 中。这样 LLM 在处理请求时就能"看到"对话者是谁，从而根据不同的 QQ 号给出不同的回复。

## 功能

- **QQ号识别**：收到消息时识别发送者的 QQ 号（而非昵称）
- **LLM 上下文注入**：自动将 QQ 号对应的用户信息注入到 LLM 请求中
- **用户信息管理**：通过命令为 QQ 号添加自定义名称、标签、备注
- **跨平台稳定**：QQ 号作为唯一标识，不受昵称变更影响

## 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/qqinfo [qq号]` | 查询 QQ 号对应的用户信息 | `/qqinfo` 或 `/qqinfo 123456789` |
| `/qqset 名称 qq号` | 为 QQ 号设置自定义名称 | `/qqset 张三 123456789` |
| `/qqtags qq号 标签1,标签2` | 为 QQ 号设置标签 | `/qqtags 123456789 朋友,同学` |
| `/qqnote qq号 备注内容` | 为 QQ 号添加备注 | `/qqnote 123456789 喜欢打游戏` |
| `/qqlist` | 列出所有已记录的 QQ 用户 | `/qqlist` |
| `/qqdel qq号` | 删除 QQ 号记录 | `/qqdel 123456789` |

## 配置（Web 面板）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enable_qq_context` | 是否在 LLM 请求中注入 QQ 号上下文 | true |
| `context_format` | 注入到 system_prompt 的模板 | 见下方 |

默认模板：
```
当前与你对话的用户信息：
- 名称: {name}
- QQ号: {qq}
- 标签: {tags}
- 备注: {note}
```

可用变量：`{name}`, `{qq}`, `{tags}`, `{note}`

## 支持

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)
- [插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
