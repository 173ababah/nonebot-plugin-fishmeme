"""表情包入库：感知哈希去重 + 索引（只用 Pillow，不拉 numpy / imagehash）。"""
from __future__ import annotations

import hashlib
import json
import os
import time

try:
    from PIL import Image
except Exception:                                    # pragma: no cover
    Image = None


def dhash(path: str, size: int = 8) -> str:
    """差值哈希（dHash）→ 16 位十六进制。

    原理：缩到 (size+1)×size 灰度图，比较左右相邻像素大小，得到 size² 个 bit。
    对缩放/轻微改色稳健，用来判断「同一张表情包」够用，而且不需要 numpy。
    """
    if Image is None:
        return ""
    try:
        with Image.open(path) as im:
            im = im.convert("L").resize((size + 1, size), Image.LANCZOS)
            px = list(im.getdata())
    except Exception:
        return ""
    bits = 0
    idx = 0
    for row in range(size):
        for col in range(size):
            left = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            if left > right:
                bits |= 1 << idx
            idx += 1
    return "%0*x" % ((size * size + 3) // 4, bits)


def hamming(h1: str, h2: str) -> int:
    if not h1 or not h2:
        return 99
    try:
        return bin(int(h1, 16) ^ int(h2, 16)).count("1")
    except ValueError:
        return 99


def sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class Store:
    """库里一张图一条：{file, hash, sha1, size, ts}，key = dHash。"""

    def __init__(self, root: str, index_path: str, near: int = 3):
        self.root = root
        self.index_path = index_path
        self.near = near
        self._idx: dict | None = None

    # ---------------- 索引 ----------------
    def load(self) -> dict:
        if self._idx is None:
            try:
                with open(self.index_path, "r", encoding="utf-8-sig") as f:
                    self._idx = json.load(f)
                if not isinstance(self._idx, dict):
                    self._idx = {}
            except (OSError, ValueError):
                self._idx = {}
        return self._idx

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        tmp = self.index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.load(), f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.index_path)

    # ---------------- 查重 ----------------
    def find_same(self, path: str) -> str:
        """已经收过就返回它在库里的 key，没有返回空串。"""
        idx = self.load()
        s = sha1(path)
        for key, item in idx.items():
            if item.get("sha1") == s:
                return key
        h = dhash(path)
        if not h:
            return ""
        for key, item in idx.items():
            if hamming(h, item.get("hash", "")) <= self.near:
                return key
        return ""

    def add(self, path: str, ext: str = ".jpg") -> str:
        """把 path 收进库，返回库里的文件名；重复则返回空串。"""
        if self.find_same(path):
            return ""
        os.makedirs(self.root, exist_ok=True)
        h = dhash(path)
        name = "m_%s_%s%s" % (time.strftime("%Y%m%d%H%M%S"), (h or sha1(path))[:8], ext)
        dst = os.path.join(self.root, name)
        with open(path, "rb") as src, open(dst, "wb") as out:
            out.write(src.read())
        self.load()[h or sha1(dst)] = {
            "file": name,
            "hash": h,
            "sha1": sha1(dst),
            "size": os.path.getsize(dst),
            "ts": int(time.time()),
        }
        self.save()
        return name

    def stats(self) -> dict:
        idx = self.load()
        newest = sorted(idx.values(), key=lambda x: x.get("ts", 0), reverse=True)[:3]
        return {"count": len(idx), "newest": [x.get("file") for x in newest]}
