# nonebot-plugin-fishmeme 🐟

> 群里发的表情包**自动收进库**：dHash 去重、写索引、随时能查数量。**零 LLM 开销。**

`astrbot_plugin_meme_manager` 的「自动收集」部分，按 nonebot2 重写。只做收图（去重 + 落盘 + 索引），
不打标签、不调模型 —— 这样才能做到「群里斗图再多也不花钱」。

## 特性

- **dHash 去重**：同一张图重新压缩、改尺寸也能认出来（汉明距离可配，默认 ≤3）
- **只用 Pillow**：不依赖 numpy / imagehash / opencv
- **限流**：每会话每分钟最多收 N 张（默认 10），单条消息最多收 3 张
- **体积上限**：默认 2MB，超了直接跳过
- 命令：`/表情库` 看数量，`/收图` 收被引用的那张

## 安装

```bash
nb plugin install nonebot-plugin-fishmeme
```

## 配置（`.env`）

```ini
FISHMEME_ENABLED=true
FISHMEME_DIR=data/fishmeme          # 图放哪
FISHMEME_INDEX=data/fishmeme/index.json
FISHMEME_PER_MIN=10                 # 每会话每分钟最多收几张，0=不限
FISHMEME_MAX_KB=2048                # 单张上限
FISHMEME_NEAR=3                     # dHash 汉明距离阈值，越大越宽松
FISHMEME_GROUP_ONLY=false           # 只在群里收
```

## 可选：给它打标签（不包含在本插件里）

索引里每条都有 `hash` 和文件名，你可以另写一个脚本，用视觉模型按
`情绪|画面|角色|场合` 四维批量标注，做成「斗图时按语义挑图」。那一步要花 token，
所以刻意拆出去，谁需要谁自己接。

## License

MIT © 173ababah