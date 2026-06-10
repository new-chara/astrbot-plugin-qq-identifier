# astrbot-plugin-qq-identifier

基于 QQ 号识别用户的 AstrBot 插件。

## 功能

- **QQ号识别**：收到消息时识别发送者的 QQ 号（而非昵称）
- **用户信息管理**：通过命令为 QQ 号添加自定义名称、标签、备注
- **个性化回复**：在 LLM 回复时自动注入用户身份信息，让回复更个性化
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

## 配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enable_decorating` | 是否在 LLM 回复中注入用户身份信息 | true |
| `decorating_format` | 注入格式模板 | `当前对话者是 {name}（QQ: {qq}）` |

## 支持

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)
- [插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
