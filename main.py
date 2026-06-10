import json
import os
import re

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.event.filter import EventMessageType, on_llm_request
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.star.star import star_map
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.core.provider.entities import ProviderRequest

# ---------- 配置 schema ----------
_CONFIG_SCHEMA = {
    "enable_qq_context": {
        "description": "在 LLM 请求中注入 QQ 号上下文（让 LLM 知道对话者是谁）",
        "type": "bool",
        "default": True,
    },
    "context_format": {
        "description": "注入到 system_prompt 的用户信息模板，可用: {name}, {qq}, {tags}, {note}",
        "type": "string",
        "default": "当前与你对话的用户信息：\n- 名称: {name}\n- QQ号: {qq}\n- 标签: {tags}\n- 备注: {note}",
    },
}

# ---------- 用户数据文件路径 ----------
def _get_users_path() -> str:
    return os.path.join(
        get_astrbot_data_path(), "config", "astrbot_plugin_qq_identifier_users.json"
    )

# ---------- 插件类 ----------
@register("astrbot_plugin_qq_identifier", "new_chara", "基于QQ号识别用户并个性化回复", "1.0.0")
class QQIdentifierPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        config_path = os.path.join(
            get_astrbot_data_path(), "config", "astrbot_plugin_qq_identifier.json"
        )
        self._cfg = AstrBotConfig(config_path=config_path, schema=_CONFIG_SCHEMA)

        md = star_map.get(self.__class__.__module__)
        if md:
            md.config = self._cfg

        self._users: dict[str, dict] = {}
        self._users_path = _get_users_path()

    # ======================== 生命周期 ========================

    async def initialize(self):
        os.makedirs(os.path.dirname(self._users_path), exist_ok=True)
        self._load_users()
        logger.info(f"[QQ号识别] 初始化完成，已加载 {len(self._users)} 个用户记录")

    async def terminate(self):
        logger.info("[QQ号识别] 插件已卸载")

    # ======================== 用户数据管理 ========================

    def _load_users(self):
        if os.path.exists(self._users_path):
            try:
                with open(self._users_path, "r", encoding="utf-8") as f:
                    self._users = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"[QQ号识别] 加载用户数据失败: {e}")
                self._users = {}
        else:
            self._users = {}

    def _save_users(self):
        os.makedirs(os.path.dirname(self._users_path), exist_ok=True)
        with open(self._users_path, "w", encoding="utf-8") as f:
            json.dump(self._users, f, ensure_ascii=False, indent=2)

    def _get_user(self, qq: str) -> dict | None:
        return self._users.get(qq)

    def _set_user(self, qq: str, **kwargs):
        if qq not in self._users:
            self._users[qq] = {}
        self._users[qq].update(kwargs)
        self._save_users()

    def _del_user(self, qq: str) -> bool:
        if qq in self._users:
            del self._users[qq]
            self._save_users()
            return True
        return False

    def _format_user(self, qq: str) -> str:
        """格式化用户信息为可读字符串"""
        user = self._get_user(qq)
        if not user:
            return f"QQ: {qq}（未记录）"

        parts = []
        if user.get("name"):
            parts.append(f"名称: {user['name']}")
        parts.append(f"QQ: {qq}")
        if user.get("tags"):
            parts.append(f"标签: {', '.join(user['tags'])}")
        if user.get("note"):
            parts.append(f"备注: {user['note']}")
        return " | ".join(parts)

    def _build_context_text(self, qq: str) -> str:
        """根据模板生成注入到 LLM prompt 的用户上下文"""
        user = self._get_user(qq) or {}
        fmt = self._cfg.context_format
        try:
            return fmt.format(
                name=user.get("name", f"QQ用户"),
                qq=qq,
                tags=", ".join(user.get("tags", [])) if user.get("tags") else "无",
                note=user.get("note", "无"),
            )
        except KeyError:
            return f"当前对话者QQ号: {qq}"

    # ======================== 消息监听 ========================

    @filter.event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，识别发送者 QQ 号并记录日志"""
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()
        message_str = event.get_message_str()

        user = self._get_user(sender_id)
        if user and user.get("name"):
            display = f"{user['name']}（QQ: {sender_id}）"
        else:
            display = f"QQ: {sender_id}（昵称: {sender_name}）"

        logger.info(f"[QQ号识别] 收到消息 | {display} | 内容: {message_str[:50]}")

    # ======================== LLM 请求钩子：注入 QQ 上下文 ========================

    @on_llm_request()
    async def inject_qq_context(self, event: AstrMessageEvent, req: ProviderRequest):
        """在 LLM 生成回复前，将 QQ 号对应的用户信息注入到 system_prompt 中"""
        if not self._cfg.enable_qq_context:
            return

        sender_id = event.get_sender_id()
        context_text = self._build_context_text(sender_id)

        # 注入到 system_prompt 开头，让 LLM 知道在和谁对话
        if req.system_prompt:
            req.system_prompt = f"{context_text}\n\n{req.system_prompt}"
        else:
            req.system_prompt = context_text

        logger.info(f"[QQ号识别] 已为 QQ {sender_id} 注入上下文到 LLM 请求")

    # ======================== 命令 ========================

    @filter.command("qqinfo")
    async def qqinfo(self, event: AstrMessageEvent, qq: str = ""):
        """查询 QQ 用户信息
        
        Args:
            qq: 要查询的 QQ 号，不填则查询发送者自己
        """
        if not qq.strip():
            qq = event.get_sender_id()

        qq = re.sub(r"\D", "", qq.strip())
        if not qq:
            yield event.plain_result("请输入有效的 QQ 号。")
            return

        info = self._format_user(qq)
        if "未记录" in info and qq == event.get_sender_id():
            info += f"\n提示：使用 /qqset <名称> {qq} 来注册你的信息。"
        
        yield event.plain_result(info)

    @filter.command("qqset")
    async def qqset(self, event: AstrMessageEvent, name: str = "", qq: str = ""):
        """为 QQ 号设置自定义名称
        
        Args:
            name: 自定义名称
            qq: QQ 号，不填则使用发送者自己的 QQ
        """
        name = name.strip()
        qq = re.sub(r"\D", "", qq.strip()) if qq.strip() else event.get_sender_id()

        if not name:
            yield event.plain_result("用法: /qqset <名称> [QQ号]\n例如: /qqset 张三 123456789")
            return

        if not qq:
            yield event.plain_result("无法获取 QQ 号。")
            return

        self._set_user(qq, name=name)
        yield event.plain_result(f"已设置 QQ {qq} 的名称为: {name}")

    @filter.command("qqtags")
    async def qqtags(self, event: AstrMessageEvent, qq: str = "", tags_str: str = ""):
        """为 QQ 号设置标签
        
        Args:
            qq: QQ 号
            tags_str: 标签，逗号分隔
        """
        qq = re.sub(r"\D", "", qq.strip()) if qq.strip() else event.get_sender_id()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        if not qq or not tags:
            yield event.plain_result("用法: /qqtags <QQ号> <标签1,标签2>\n例如: /qqtags 123456789 朋友,同学")
            return

        self._set_user(qq, tags=tags)
        yield event.plain_result(f"已设置 QQ {qq} 的标签: {', '.join(tags)}")

    @filter.command("qqnote")
    async def qqnote(self, event: AstrMessageEvent, qq: str = "", note: str = ""):
        """为 QQ 号添加备注
        
        Args:
            qq: QQ 号
            note: 备注内容
        """
        qq = re.sub(r"\D", "", qq.strip()) if qq.strip() else event.get_sender_id()

        if not qq or not note.strip():
            yield event.plain_result("用法: /qqnote <QQ号> <备注内容>\n例如: /qqnote 123456789 喜欢打游戏")
            return

        self._set_user(qq, note=note.strip())
        yield event.plain_result(f"已设置 QQ {qq} 的备注: {note.strip()}")

    @filter.command("qqlist")
    async def qqlist(self, event: AstrMessageEvent):
        """列出所有已记录的 QQ 用户"""
        if not self._users:
            yield event.plain_result("暂无已记录的用户。请使用 /qqset 添加。")
            return

        lines = [f"共 {len(self._users)} 个用户记录："]
        for qq, info in self._users.items():
            name = info.get("name", "未命名")
            tags = f" [{', '.join(info['tags'])}]" if info.get("tags") else ""
            note = f" - {info['note']}" if info.get("note") else ""
            lines.append(f"  {name} ({qq}){tags}{note}")

        yield event.plain_result("\n".join(lines))

    @filter.command("qqdel")
    async def qqdel(self, event: AstrMessageEvent, qq: str = ""):
        """删除 QQ 号记录
        
        Args:
            qq: 要删除的 QQ 号
        """
        qq = re.sub(r"\D", "", qq.strip())

        if not qq:
            yield event.plain_result("用法: /qqdel <QQ号>")
            return

        if self._del_user(qq):
            yield event.plain_result(f"已删除 QQ {qq} 的记录。")
        else:
            yield event.plain_result(f"未找到 QQ {qq} 的记录。")
