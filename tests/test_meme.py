"""dHash 去重 + 索引自测。跑法：python tests/test_meme.py（不需要联网）"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nonebot  # noqa: E402

nonebot.init()
from PIL import Image, ImageDraw  # noqa: E402

from nonebot_plugin_fishmeme.store import Store, dhash, hamming, sha1  # noqa: E402

OK, BAD = [], []


def ck(name, cond, extra=""):
    (OK if cond else BAD).append(name)
    print("  [OK]   %s" % name if cond else "  [FAIL] %s %s" % (name, extra))


def make(path, seed=0, size=(240, 240)):
    im = Image.new("RGB", size, (30, 40, 60))
    d = ImageDraw.Draw(im)
    d.ellipse([20 + seed * 3, 40, 200, 220], fill=(240, 200, 90))
    d.rectangle([60, 60 + seed * 2, 120, 140], fill=(20, 120, 200))
    d.text((10, 10), "fish %d" % seed, fill=(255, 255, 255))
    im.save(path, quality=92)
    return path


def main():
    tmp = tempfile.mkdtemp(prefix="meme_")
    a = make(os.path.join(tmp, "a.jpg"), seed=0)
    b = make(os.path.join(tmp, "b.jpg"), seed=0)              # 同一张图重新存
    c = make(os.path.join(tmp, "c.jpg"), seed=9)              # 明显不同
    ha, hb, hc = dhash(a), dhash(b), dhash(c)
    ck("dHash 是 16 位十六进制", len(ha) == 16 and all(ch in "0123456789abcdef" for ch in ha), ha)
    ck("同一张图 hash 一样", ha == hb, "%s vs %s" % (ha, hb))
    ck("不同图 hash 不一样", ha != hc, "%s vs %s" % (ha, hc))
    ck("自己距自己 0", hamming(ha, ha) == 0)
    ck("不同图距离更大", hamming(ha, hc) > hamming(ha, hb))
    ck("sha1 稳定", sha1(a) == sha1(b))

    st = Store(os.path.join(tmp, "lib"), os.path.join(tmp, "lib", "index.json"), near=3)
    n1 = st.add(a, ".jpg")
    ck("第一次收进来成功", bool(n1), n1)
    n2 = st.add(b, ".jpg")
    ck("同一张图第二次被去重", n2 == "", n2)
    n3 = st.add(c, ".jpg")
    ck("不同的图能收进来", bool(n3), n3)
    ck("索引里 2 条", st.stats()["count"] == 2, st.stats())
    ck("落盘文件真的存在", os.path.exists(os.path.join(tmp, "lib", n1)))

    print("通过 %d 项，失败 %d 项" % (len(OK), len(BAD)))
    return 0 if not BAD else 1


if __name__ == "__main__":
    sys.exit(main())