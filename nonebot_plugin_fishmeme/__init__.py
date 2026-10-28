"""nonebot-plugin-fishmeme —— 群里发的表情包自动入库（去重 + 索引），零 LLM 开销。

`astrbot_plugin_meme_manager` 的「自动收集」那部分，按 nonebot2 重写：
收到图片 → 下载 → dHash 去重 → 落盘 + 写索引。**不调用任何模型**（打标签是可选的外部步骤，
见 README「可选：给它打标签」）。
"""
from __future__ import annotations

import os
import re
import tempfile
import time

import httpx
from nonebot import get_driver, logger, on_command, on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .config import Config
from .store import Store

__plugin_meta__ = PluginMetadata(
    name="鱼式表情包收容所",
    description="群里发的表情包自动收进库（dHash 去重），零 LLM 开销",
    usage="/表情库 看数量；/收图 收被引用的那张",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

# nonebot 2.1 / 2.5 都能用：老版本没有 get_plugin_config
def _load_config():
    cfg = get_driver().config
    dump = getattr(cfg, "model_dump", None)
    return Config(**(dump() if callable(dump) else cfg.dict()))
plugin_config = _load_config()
store = Store(plugin_config.fishmeme_dir, plugin_config.fishmeme_index, plugin_config.fishmeme_near)
_rate: dict[str, list[float]] = {}
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) fishmeme/0.1"}


def _chat_key(event: MessageEvent) -> str:
    if getattr(event, "group_id", None):
        return "group:%s" % event.group_id
    return "private:%s" % event.user_id


def _rate_ok(event: MessageEvent) -> bool:
    if plugin_config.fishmeme_per_min <= 0:
        return True
    key = _chat_key(event)
    now = time.time()
    hits = [t for t in _rate.get(key, []) if now - t < 60]
    if len(hits) >= plugin_config.fishmeme_per_min:
        _rate[key] = hits
        return False
    hits.append(now)
    _rate[key] = hits
    return True


def _images(event: MessageEvent) -> list:
    try:
        return [seg for seg in event.get_message() if seg.type == "image"]
    except Exception:
        return []


def _img_url(seg) -> str:
    data = getattr(seg, "data", None) or {}
    return str(data.get("url") or data.get("file") or "")


async def _download(url: str) -> str | None:
    """下载到临时文件；超过大小上限就放弃。返回本地路径。"""
    if not url.startswith("http"):
        return None
    limit = plugin_config.fishmeme_max_kb * 1024
    tmp = ""
    try:
        async with httpx.AsyncClient(timeout=20, headers=_UA, follow_redirects=True) as c:
            async with c.stream("GET", url) as r:
                if r.status_code != 200:
                    return None
                got = 0
                fd, tmp = tempfile.mkstemp(suffix=".img")
                with os.fdopen(fd, "wb") as f:
                    async for chunk in r.aiter_bytes(65536):
                        got += len(chunk)
                        if got > limit:
                            return None
                        f.write(chunk)
        return tmp
    except Exception as e:
        logger.debug("[fishmeme] 下载失败 %r" % (e,))
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return None


async def _collect(event: MessageEvent, segs: list) -> int:
    """收图，返回收了几个。"""
    n = 0
    for seg in segs[:3]:                     # 一条消息最多收 3 张，别把流量吃光
        url = _img_url(seg)
        tmp = await _download(url)
        if not tmp:
            continue
        try:
            ext = os.path.splitext(url.split("?")[0])[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                ext = ".jpg"
            name = store.add(tmp, ext)
            if name:
                n += 1
                logger.info("[fishmeme] 收了 %s（%d 字节）" % (name, os.path.getsize(tmp)))
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
    return n


async def _rule_auto(event: MessageEvent) -> bool:
    if not plugin_config.fishmeme_enabled:
        return False
    if plugin_config.fishmeme_group_only and not getattr(event, "group_id", None):
        return False
    return bool(_images(event))


auto_matcher = on_message(rule=Rule(_rule_auto), priority=90, block=False)


@auto_matcher.handle()
async def _auto_collect(bot: Bot, event: MessageEvent):
    if not _rate_ok(event):
        return
    await _collect(event, _images(event))


lib_cmd = on_command("表情库", aliases={"表情数量", "memecount"}, priority=20, block=True)


@lib_cmd.handle()
async def _show_lib(bot: Bot, event: MessageEvent):
    st = store.stats()
    if not st["count"]:
        await lib_cmd.finish("库里还空着，多发点表情包喂我。")
    tail = ("，最近收了：" + "、".join(st["newest"])) if st["newest"] else ""
    await lib_cmd.finish("表情包库有 %d 张%s" % (st["count"], tail))


save_cmd = on_command("收图", aliases={"收藏表情", "memesave"}, priority=20, block=True)


@save_cmd.handle()
async def _save_one(bot: Bot, event: MessageEvent):
    if not plugin_config.fishmeme_enabled:
        await save_cmd.finish("收图功能关着呢。")
    # 优先收被引用的那条消息里的图，没有就看自己这条
    segs = _images(event)
    reply = getattr(event, "reply", None)
    if reply is not None:
        try:
            segs = [seg for seg in reply.message if seg.type == "image"] or segs
        except Exception:
            pass
    if not segs:
        await save_cmd.finish("图呢？引用一条带图片的消息再 /收图。")
    n = await _collect(event, segs)
    await save_cmd.finish("收好了，%d 张。" % n if n else "这张库里已经有了，不重复收。")
