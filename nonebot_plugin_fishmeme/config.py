"""配置：全部 FISHMEME_ 前缀。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Config(BaseModel):
    fishmeme_enabled: bool = Field(default=True, description="启用表情包自动收集")
    fishmeme_dir: str = Field(default="data/fishmeme", description="收进来的图放哪（相对 nonebot 运行目录）")
    fishmeme_index: str = Field(default="data/fishmeme/index.json", description="索引文件")
    fishmeme_per_min: int = Field(default=10, description="每会话每分钟最多收几张，0=不限")
    fishmeme_max_kb: int = Field(default=2048, description="单张图上限（KB），超过不收")
    fishmeme_near: int = Field(default=3, description="dHash 汉明距离 ≤ 这个值算同一张图")
    fishmeme_group_only: bool = Field(default=False, description="只在群聊收（默认私聊也收）")
