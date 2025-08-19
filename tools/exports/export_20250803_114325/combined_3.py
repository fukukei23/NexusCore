
# === NexusCore/openenv\Lib\site-packages\nltk\app\nemo_app.py ===
# Finding (and Replacing) Nemo, Version 1.1, Aristide Grange 2006/06/06
# https://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496783

"""
Finding (and Replacing) Nemo

Instant Regular Expressions
Created by Aristide Grange
"""
import itertools
import re
from tkinter import SEL_FIRST, SEL_LAST, Frame, Label, PhotoImage, Scrollbar, Text, Tk

windowTitle = "Finding (and Replacing) Nemo"
initialFind = r"n(.*?)e(.*?)m(.*?)o"
initialRepl = r"M\1A\2K\3I"
initialText = """\
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
"""
images = {
    "FIND": "R0lGODlhMAAiAPcAMf/////37//35//n1v97Off///f/9/f37/fexvfOvfeEQvd7QvdrQvdrKfdaKfdSMfdSIe/v9+/v7+/v5+/n3u/e1u/Wxu/Gre+1lO+tnO+thO+Ua+97Y+97Oe97Me9rOe9rMe9jOe9jMe9jIe9aMefe5+fe3ufezuece+eEWudzQudaIedSIedKMedKIedCKedCId7e1t7Wzt7Oxt7Gvd69vd69rd61pd6ljN6UjN6Ue96EY95zY95rUt5rQt5jMd5SId5KIdbn59be3tbGztbGvda1rdaEa9Z7a9Z7WtZzQtZzOdZzMdZjMdZaQtZSOdZSMdZKMdZCKdZCGNY5Ic7W1s7Oxs7Gtc69xs69tc69rc6tpc6llM6clM6cjM6Ue86EY85zWs5rSs5SKc5KKc5KGMa1tcatrcalvcalnMaUpcZ7c8ZzMcZrUsZrOcZrMcZaQsZSOcZSMcZKMcZCKcZCGMYxIcYxGL3Gxr21tb21rb2lpb2crb2cjL2UnL2UlL2UhL2Ec717Wr17Ur1zWr1rMb1jUr1KMb1KIb1CIb0xGLWlrbWlpbWcnLWEe7V7c7VzY7VzUrVSKbVKMbVCMbVCIbU5KbUxIbUxEK2lta2lpa2clK2UjK2MnK2MlK2Ea617e61za61rY61rMa1jSq1aUq1aSq1SQq1KKa0xEKWlnKWcnKWUnKWUhKWMjKWEa6Vza6VrWqVjMaVaUqVaKaVSMaVCMaU5KaUxIaUxGJyclJyMe5yElJyEhJx7e5x7c5xrOZxaQpxSOZxKQpw5IZSMhJSEjJR7c5Rre5RrY5RrUpRSQpRSKZRCOZRCKZQxKZQxIYyEhIx7hIxza4xzY4xrc4xjUoxaa4xaUoxSSoxKQoxCMYw5GIR7c4Rzc4Rre4RjY4RjWoRaa4RSWoRSUoRSMYRKQoRCOYQ5KYQxIXtra3taY3taSntKOXtCMXtCKXNCMXM5MXMxIWtSUmtKSmtKQmtCOWs5MWs5KWs5IWNCKWMxIVIxKUIQCDkhGAAAACH+AS4ALAAAAAAwACIAAAj/AAEIHEiwoMGDCBMqXMiwoUOHMqxIeEiRoZVp7cpZ29WrF4WKIAd208dGAQEVbiTVChUjZMU9+pYQmPmBZpxgvVw+nDdKwQICNVcIXQEkTgKdDdUJ+/nggVAXK1xI3TEA6UIr2uJ8iBqka1cXXTlkqGoVYRZ7iLyqBSs0iiEtZQVKiDGxBI1u3NR6lUpGDKg8MSgEQCphU7Z22vhg0dILXRCpYLuSCcYJT4wqXASBQaBzU7klHxC127OHD7ZDJFpERqRt0x5OnwQpmZmCLEhrbgg4WIHO1RY+nbQ9WRGEDJlmnXwJ+9FBgXMCIzYMVijBBgYMFxIMqJBMSc0Ht7qh/+Gjpte2rnYsYeNlasWIBgQ6yCewIoPCCp/cyP/wgUGbXVu0QcADZNBDnh98gHMLGXYQUw02w61QU3wdbNWDbQVVIIhMMwFF1DaZiPLBAy7E04kafrjSizaK3LFNNc0AAYRQDsAHHQlJ2IDQJ2zE1+EKDjiAijShkECCC8Qgw4cr7ZgyzC2WaHPNLWWoNeNWPiRAw0QFWQFMhz8C+QQ20yAiVSrY+MGOJCsccsst2GCzoHFxxEGGC+8hgs0MB2kyCpgzrUDCbs1Es41UdtATHFFkWELMOtsoQsYcgvRRQw5RSDgGOjZMR1AvPQIq6KCo9AKOJWDd48owQlHR4DXEKP9iyRrK+DNNBTu4RwIPFeTAGUG7hAomkA84gEg1m6ADljy9PBKGGJY4ig0xlsTBRSn98FOFDUC8pwQOPkgHbCGAzhTkA850s0c7j6Hjix9+gBIrMXLeAccWXUCyiRBcBEECdEJ98KtAqtBCYQc/OvDENnl4gYpUxISCIjjzylkGGV9okYUVNogRhAOBuuAEhjG08wOgDYzAgA5bCjIoCe5uwUk80RKTTSppPREGGGCIISOQ9AXBg6cC6WIywvCpoMHAocRBwhP4bHLFLujYkV42xNxBRhAyGrc113EgYtRBerDDDHMoDCyQEL5sE083EkgwQyBhxGFHMM206DUixGxmE0wssbQjCQ4JCaFKFwgQTVAVVhQUwAVPIFJKrHfYYRwi6OCDzzuIJIFhXAD0EccPsYRiSyqKSDpFcWSMIcZRoBMkQyA2BGZDIKSYcggih8TRRg4VxM5QABVYYLxgwiev/PLMCxQQADs=",
    "find": "R0lGODlhMAAiAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OSkpKRgYGAAAAAAAAAAAAAAAAAAAACH+AS4ALAAAAAAwACIAAAX/ICCOZGmeaKquY2AGLiuvMCAUBuHWc48Kh0iFInEYCb4kSQCxPBiMxkMigRQEgJiSFVBYHNGG0RiZOHjblWAiiY4fkDhEYoBp06dAWfyAQyKAgAwDaHgnB0RwgYASgQ0IhDuGJDAIFhMRVFSLEX8QCJJ4AQM5AgQHTZqqjBAOCQQEkWkCDRMUFQsICQ4Vm5maEwwHOAsPDTpKMAsUDlO4CssTcb+2DAp8YGCyNFoCEsZwFQ3QDRTTVBRS0g1QbgsCd5QAAwgIBwYFAwStzQ8UEdCKVchky0yVBw7YuXkAKt4IAg74vXHVagqFBRgXSCAyYWAVCH0SNhDTitCJfSL5/4RbAPKPhQYYjVCYYAvCP0BxEDaD8CheAAHNwqh8MMGPSwgLeJWhwHSjqkYI+xg4MMCEgQjtRvZ7UAYCpghMF7CxONOWJkYR+rCpY4JlVpVxKDwYWEactKW9mhYRtqCTgwgWEMArERSK1j5q//6T8KXonFsShpiJkAECgQYVjykooCVA0JGHEWNiYCHThTFeb3UkoiCCBgwGEKQ1kuAJlhFwhA71h5SukwUM5qqeCSGBgicEWkfNiWSERtBad4JNIBaQBaQah1ToyGZBAnsIuIJs1qnqiAIVjIE2gnAB1T5x0icgzXT79ipgMOOEH6HBbREBMJCeGEY08IoLAkzB1YYFwjxwSUGSNULQJnNUwRYlCcyEkALIxECAP9cNMMABYpRhy3ZsSLDaR70oUAiABGCkAxowCGCAAfDYIQACXoElGRsdXWDBdg2Y90IWktDYGYAB9PWHP0PMdFZaF07SQgAFNDAMAQg0QA1UC8xoZQl22JGFPgWkOUCOL1pZQyhjxinnnCWEAAA7",
    "REPL": "R0lGODlhMAAjAPcAMf/////3//+lOf+UKf+MEPf///f39/f35/fv7/ecQvecOfecKfeUIfeUGPeUEPeUCPeMAO/37+/v9+/v3u/n3u/n1u+9jO+9c++1hO+ta++tY++tWu+tUu+tSu+lUu+lQu+lMe+UMe+UKe+UGO+UEO+UAO+MCOfv5+fvxufn7+fn5+fnzue9lOe9c+e1jOe1e+e1c+e1a+etWuetUuelQuecOeeUUueUCN7e597e3t7e1t7ezt7evd7Wzt7Oxt7Ovd7Otd7Opd7OnN7Gtd7Gpd69lN61hN6ta96lStbextberdbW3tbWztbWxtbOvdbOrda1hNalUtaECM7W1s7Ozs7Oxs7Otc7Gxs7Gvc69tc69rc69pc61jM6lc8bWlMbOvcbGxsbGpca9tca9pca1nMaMAL3OhL3Gtb21vb21tb2tpb2tnL2tlLW9tbW9pbW9e7W1pbWtjLWcKa21nK2tra2tnK2tlK2lpa2llK2ljK2le6WlnKWljKWUe6WUc6WUY5y1QpyclJycjJychJyUc5yMY5StY5SUe5SMhJSMe5SMc5SMWpSEa5SESoyUe4yMhIyEY4SlKYScWoSMe4SEe4SEa4R7c4R7Y3uMY3uEe3t7e3t7c3tza3tzY3trKXtjIXOcAHOUMXOEY3Nzc3NzWnNrSmulCGuUMWuMGGtzWmtrY2taMWtaGGOUOWOMAGNzUmNjWmNjSmNaUmNaQmNaOWNaIWNSCFqcAFpjUlpSMVpSIVpSEFpKKVKMAFJSUlJSSlJSMVJKMVJKGFJKAFI5CEqUAEqEAEpzQkpKIUpCQkpCGEpCAEo5EEoxAEJjOUJCOUJCAEI5IUIxADl7ADlaITlCOTkxMTkxKTkxEDkhADFzADFrGDE5OTExADEpEClrCCkxKSkpKSkpISkpACkhCCkhACkYACFzACFrACEhCCEYGBhjEBhjABghABgYCBgYABgQEBgQABAQABAIAAhjAAhSAAhKAAgIEAgICABaAABCAAAhAAAQAAAIAAAAAAAAACH+AS4ALAAAAAAwACMAAAj/AAEIHEiwoMGDCBMqXMiwocOHAA4cgEixIIIJO3JMmAjADIqKFU/8MHIkg5EgYXx4iaTkI0iHE6wE2TCggYILQayEAgXIy8uGCKz8sDCAQAMRG3iEcXULlJkJPwli3OFjh9UdYYLE6NBhA04UXHoVA2XoTZgfPKBWlOBDphAWOdfMcfMDLloeO3hIMjbWVCQ5Fn6E2UFxgpsgFjYIEBADrZU6luqEEfqjTqpt54z1uuWqTIcgWAk7PECGzIUQDRosDmxlUrVJkwQJkqVuX71v06YZcyUlROAdbnLAJKPFyAYFAhoMwFlnEh0rWkpz8raPHm7dqKKc/KFFkBUrVn1M/ziBcEIeLUEQI8/AYk0i9Be4sqjsrN66c9/OnbobhpR3HkIUoZ0WVnBE0AGLFKKFD0HAFUQe77HQgQI1hRBDEHMcY0899bBzihZuCPILJD8EccEGGzwAQhFaUHHQH82sUkgeNHISDBk8WCCCcsqFUEQWmOyzjz3sUGNNOO5Y48YOEgowAAQhnBScQV00k82V47jzjy9CXZBcjziFoco//4CDiSOyhPMPLkJZkEBqJmRQxA9uZGEQD8Ncmc044/zzDF2IZQBCCDYE8QMZz/iiCSx0neHGI7BIhhhNn+1gxRpokEcQAp7seWU7/PwTyxqG/iCEEVzQmUombnDRxRExzP9nBR2PCKLFD3UJwcMPa/SRqUGNWJmNOVn+M44ukMRB4KGcWDNLVhuUMEIJAlzwA3DJBHMJIXm4sQYhqyxCRQQGLSIsn1qac2UzysQSyzX/hLMGD0F0IMCODYAQBA9W/PKPOcRiw0wzwxTiokF9dLMnuv/Mo+fCZF7jBr0xbDDCACWEYKgb1vzjDp/jZNOMLX0IZxAKq2TZTjtaOjwOsXyG+s8sZJTIQsUdIGHoJPf8w487QI/TDSt5mGwQFZxc406o8HiDJchk/ltLHpSlJwSvz5DpTjvmuGNOM57koelBOaAhiCaaPBLL0wwbm003peRBnBZqJMJL1ECz/HXYYx/NdAIOOVCxQyLorswymU93o0wuwfAiTDNR/xz0MLXU0XdCE+UwSTRZAq2lsSATu+4wkGvt+TjNzPLrQyegAUku2Hij5cd8LhxyM8QIg4w18HgcdC6BTBFSDmfQqsovttveDcG7lFLHI75cE841sARCxeWsnxC4G9HADPK6ywzDCRqBo0EHHWhMgT1IJzziNci1N7PMKnSYfML96/90AiJKey/0KtbLX1QK0rrNnQ541xugQ7SHhkXBghN0SKACWRc4KlAhBwKcIOYymJCAAAA7",
    "repl": "R0lGODlhMAAjAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OTExMSkpKSEhIRgYGBAQEAgICAAAACH+AS4ALAAAAAAwACMAAAX/ICCOZGmeaKqubOu+gCDANBkIQ1EMQhAghFptYEAkEgjEwXBo7ISvweGgWCwUysPjwTgEoCafTySYIhYMxgLBjEQgCULvCw0QdAZdoVhUIJUFChISEAxYeQM1N1OMTAp+UwZ5eA4TEhFbDWYFdC4ECVMJjwl5BwsQa0umEhUVlhESDgqlBp0rAn5nVpBMDxeZDRQbHBgWFBSWDgtLBnFjKwRYCI9VqQsPs0YKEcMXFq0UEalFDWx4BAO2IwPjppAKDkrTWKYUGd7fEJJFEZpM00cOzCgh4EE8SaoWxKNixQooBRMyZMBwAYIRBhUgLDGS4MoBJeoANMhAgQsaCRZm/5lqaCUJhA4cNHjDoKEDBlJUHqkBlYBTiQUZNGjYMMxDhY3VWk6R4MEDBoMUak5AqoYBqANIBo4wcGGDUKIeLlzVZmWJggsVIkwAZaQSA3kdZzlKkIiEAAlDvW5oOkEBs488JTw44oeUIwdvVTFTUK7uiAAPgubt8GFDhQepqETAQCFU1UMGzlqAgFhUsAcCS0AO6lUDhw8xNRSbENGDhgWSHjWUe6ACbKITizmopZoBa6KvOwj9uuHDhwxyj3xekgDDhw5EvWKo0IB4iQLCOCC/njc7ZQ8UeGvza+ABZZgcxJNc4FO1gc0cOsCUrHevc8tdIMTIAhc4F198G2Qwwd8CBIQUAwEINABBBJUwR9R5wElgVRLwWODBBx4cGB8GEzDQIAo33CGJA8gh+JoH/clUgQU0YvDhdfmJdwEFC6Sjgg8yEPAABsPkh2F22cl2AQbn6QdTghTQ5eAJAQyQAAQV0MSBB9gRVZ4GE1mw5JZOAmiAVi1UWcAZDrDyZXYTeaOhA/bIVuIBPtKQ4h7ViYekUPdcEAEbzTzCRp5CADmAAwj+ORGPBcgwAAHo9ABGCYtm0ChwFHShlRiXhmHlkAcCiOeUodqQw5W0oXLAiamy4MOkjOyAaqxUymApDCEAADs=",
}
colors = ["#FF7B39", "#80F121"]
emphColors = ["#DAFC33", "#F42548"]
fieldParams = {
    "height": 3,
    "width": 70,
    "font": ("monaco", 14),
    "highlightthickness": 0,
    "borderwidth": 0,
    "background": "white",
}
textParams = {
    "bg": "#F7E0D4",
    "fg": "#2321F1",
    "highlightthickness": 0,
    "width": 1,
    "height": 10,
    "font": ("verdana", 16),
    "wrap": "word",
}


class Zone:
    def __init__(self, image, initialField, initialText):
        frm = Frame(root)
        frm.config(background="white")
        self.image = PhotoImage(format="gif", data=images[image.upper()])
        self.imageDimmed = PhotoImage(format="gif", data=images[image])
        self.img = Label(frm)
        self.img.config(borderwidth=0)
        self.img.pack(side="left")
        self.fld = Text(frm, **fieldParams)
        self.initScrollText(frm, self.fld, initialField)
        frm = Frame(root)
        self.txt = Text(frm, **textParams)
        self.initScrollText(frm, self.txt, initialText)
        for i in range(2):
            self.txt.tag_config(colors[i], background=colors[i])
            self.txt.tag_config("emph" + colors[i], foreground=emphColors[i])

    def initScrollText(self, frm, txt, contents):
        scl = Scrollbar(frm)
        scl.config(command=txt.yview)
        scl.pack(side="right", fill="y")
        txt.pack(side="left", expand=True, fill="x")
        txt.config(yscrollcommand=scl.set)
        txt.insert("1.0", contents)
        frm.pack(fill="x")
        Frame(height=2, bd=1, relief="ridge").pack(fill="x")

    def refresh(self):
        self.colorCycle = itertools.cycle(colors)
        try:
            self.substitute()
            self.img.config(image=self.image)
        except re.error:
            self.img.config(image=self.imageDimmed)


class FindZone(Zone):
    def addTags(self, m):
        color = next(self.colorCycle)
        self.txt.tag_add(color, "1.0+%sc" % m.start(), "1.0+%sc" % m.end())
        try:
            self.txt.tag_add(
                "emph" + color, "1.0+%sc" % m.start("emph"), "1.0+%sc" % m.end("emph")
            )
        except:
            pass

    def substitute(self, *args):
        for color in colors:
            self.txt.tag_remove(color, "1.0", "end")
            self.txt.tag_remove("emph" + color, "1.0", "end")
        self.rex = re.compile("")  # default value in case of malformed regexp
        self.rex = re.compile(self.fld.get("1.0", "end")[:-1], re.MULTILINE)
        try:
            re.compile("(?P<emph>%s)" % self.fld.get(SEL_FIRST, SEL_LAST))
            self.rexSel = re.compile(
                "%s(?P<emph>%s)%s"
                % (
                    self.fld.get("1.0", SEL_FIRST),
                    self.fld.get(SEL_FIRST, SEL_LAST),
                    self.fld.get(SEL_LAST, "end")[:-1],
                ),
                re.MULTILINE,
            )
        except:
            self.rexSel = self.rex
        self.rexSel.sub(self.addTags, self.txt.get("1.0", "end"))


class ReplaceZone(Zone):
    def addTags(self, m):
        s = sz.rex.sub(self.repl, m.group())
        self.txt.delete(
            "1.0+%sc" % (m.start() + self.diff), "1.0+%sc" % (m.end() + self.diff)
        )
        self.txt.insert("1.0+%sc" % (m.start() + self.diff), s, next(self.colorCycle))
        self.diff += len(s) - (m.end() - m.start())

    def substitute(self):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", sz.txt.get("1.0", "end")[:-1])
        self.diff = 0
        self.repl = rex0.sub(r"\\g<\1>", self.fld.get("1.0", "end")[:-1])
        sz.rex.sub(self.addTags, sz.txt.get("1.0", "end")[:-1])


def launchRefresh(_):
    sz.fld.after_idle(sz.refresh)
    rz.fld.after_idle(rz.refresh)


def app():
    global root, sz, rz, rex0
    root = Tk()
    root.resizable(height=False, width=True)
    root.title(windowTitle)
    root.minsize(width=250, height=0)
    sz = FindZone("find", initialFind, initialText)
    sz.fld.bind("<Button-1>", launchRefresh)
    sz.fld.bind("<ButtonRelease-1>", launchRefresh)
    sz.fld.bind("<B1-Motion>", launchRefresh)
    sz.rexSel = re.compile("")
    rz = ReplaceZone("repl", initialRepl, "")
    rex0 = re.compile(r"(?<!\\)\\([0-9]+)")
    root.bind_all("<Key>", launchRefresh)
    launchRefresh(None)
    root.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/exported_projects\app_20250703_223016\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/src\gradio_app\interactive_generator.py ===
# src/gradio_app/interactive_generator.py
import gradio as gr
import os
import re
import difflib
import subprocess
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_OUTPUT_DIR = "../sandbox_output"
DEFAULT_FILENAME = "sample.py"
LOG_FILE = "../logs/save_log.txt"
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
os.makedirs("../logs", exist_ok=True)

# === GPT呼び出し ===
def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# === コードと理由の抽出 ===
def extract_code_and_reason(full_response):
    code_match = re.search(r"```(?:python)?\n(.*?)```", full_response, re.DOTALL)
    reason_match = re.split(r"```.*?```", full_response, maxsplit=1)
    code = code_match.group(1).strip() if code_match else ""
    reason = reason_match[1].strip() if len(reason_match) > 1 else ""
    return code, reason

# === ファイルパス抽出 ===
def extract_file_path_from_code(code: str, default_path: str = os.path.join(DEFAULT_OUTPUT_DIR, DEFAULT_FILENAME)) -> str:
    match = re.search(r"#\s*filepath\s*:\s*(.+\.py)", code)
    if match:
        return match.group(1).strip()
    return default_path

# === 差分取得 ===
def get_diff(old, new):
    diff = difflib.HtmlDiff().make_file(old.splitlines(), new.splitlines(), context=True)
    return diff

# === バージョン番号付与 ===
def get_versioned_path(path):
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(path):
        path = f"{base}_v{i}{ext}"
        i += 1
    return path

# === ファイル保存 ===
def save_code_with_backup_and_diff(code: str, user_path: str):
    try:
        save_path = extract_file_path_from_code(code, default_path=user_path)
        full_path = os.path.join("..", save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        diff_html = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                old_code = f.read()
            diff_html = get_diff(old_code, code)
            backup_path = full_path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(old_code)
            save_path = get_versioned_path(full_path)  # avoid overwrite

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now()} - Saved: {save_path}\n")

        return f"✅ 保存成功: {save_path}", diff_html

    except Exception as e:
        return f"❌ 保存失敗: {str(e)}", ""

# === Gradio UI ===
with gr.Blocks() as app:
    gr.Markdown("### 🧐 自然文からAI補足付き 初期コード自動生成")

    initial_input = gr.Textbox(label="📝 やりたいこと（自然文）")
    output_path_input = gr.Textbox(label="📂 保存先（例: src/utils/my_func.py）", value="src/generated/sample.py")
    submit_btn = gr.Button("🔍 質問を開始")
    gpt_question = gr.Textbox(label="🤠 GPTの補足質問", lines=2)
    user_reply = gr.Textbox(label="✍️ 回答を記入")
    loop_again_btn = gr.Button("🔁 さらに質問してほしい")
    generate_code_btn = gr.Button("✅ これでコード生成してよい")
    code_output = gr.Code(label="📄 GPTによる初期コード", language="python")
    save_result = gr.Textbox(label="✅ 保存結果メッセージ", interactive=False)
    file_list = gr.Dropdown(label="🗂 保存済みファイル一覧", choices=[])
    open_in_vscode_btn = gr.Button("🖥 VSCodeで開く")
    diff_output = gr.HTML(label="📌 差分表示（HTML強調）")
    history = gr.State("")

    def ask_gpt_question(user_goal, prev_answers):
        prompt = f"""
以下はユーザーの目的です。
これに基づいて、実装前に補足確認すべき点を最大3点、質問形式で出力してください。
すでに以下の回答が得られています：
{prev_answers}

【ユーザー目的】
{user_goal}
"""
        return call_gpt(prompt)

    def update_history(history_text, question, answer):
        return history_text + f"【GPTの質問】\n{question}\n【ユーザーの回答】\n{answer}\n\n"

    def ask_more_questions(user_goal, current_answer, prev_q, hist):
        new_hist = update_history(hist, prev_q, current_answer)
        next_q = ask_gpt_question(user_goal, new_hist)
        return next_q, new_hist

    def generate_final_code(user_goal, hist, output_path):
        final_prompt = f"""
以下はユーザーの実施目的と、事前の質問・回答のやりとり履歴です。
この情報に基づき、docstring付きのPython関数を一つ作成してください。

【目的】
{user_goal}

【補足内容】
{hist}
"""
        response = call_gpt(final_prompt)
        code, _ = extract_code_and_reason(response)
        result, diff = save_code_with_backup_and_diff(code, output_path)
        return code, result, diff

    def list_saved_files():
        file_paths = []
        for root, _, files in os.walk("../src"):
            for f in files:
                if f.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, f), "../")
                    file_paths.append(rel_path)
        return sorted(file_paths)

    def open_file_in_vscode(file_path):
        try:
            subprocess.Popen(["code", os.path.join("..", file_path)])
            return f"🖥 VSCodeで開きました: {file_path}"
        except Exception as e:
            return f"❌ VSCode起動失敗: {str(e)}"

    submit_btn.click(fn=ask_gpt_question, inputs=[initial_input, history], outputs=[gpt_question])
    loop_again_btn.click(fn=ask_more_questions, inputs=[initial_input, user_reply, gpt_question, history], outputs=[gpt_question, history])
    generate_code_btn.click(fn=generate_final_code, inputs=[initial_input, history, output_path_input], outputs=[code_output, save_result, diff_output])
    generate_code_btn.click(fn=list_saved_files, inputs=[], outputs=[file_list])
    open_in_vscode_btn.click(fn=open_file_in_vscode, inputs=[file_list], outputs=[save_result])

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32con.py ===
# Generated by h2py from commdlg.h (plus modifications 4jan98)
WINVER = 1280
WM_USER = 1024
PY_0U = 0
OFN_READONLY = 1
OFN_OVERWRITEPROMPT = 2
OFN_HIDEREADONLY = 4
OFN_NOCHANGEDIR = 8
OFN_SHOWHELP = 16
OFN_ENABLEHOOK = 32
OFN_ENABLETEMPLATE = 64
OFN_ENABLETEMPLATEHANDLE = 128
OFN_NOVALIDATE = 256
OFN_ALLOWMULTISELECT = 512
OFN_EXTENSIONDIFFERENT = 1024
OFN_PATHMUSTEXIST = 2048
OFN_FILEMUSTEXIST = 4096
OFN_CREATEPROMPT = 8192
OFN_SHAREAWARE = 16384
OFN_NOREADONLYRETURN = 32768
OFN_NOTESTFILECREATE = 65536
OFN_NONETWORKBUTTON = 131072
OFN_NOLONGNAMES = 262144
OFN_EXPLORER = 524288  # new look commdlg
OFN_NODEREFERENCELINKS = 1048576
OFN_LONGNAMES = 2097152  # force long names for Python 3 modules
OFN_ENABLEINCLUDENOTIFY = 4194304  # send include message to callback
OFN_ENABLESIZING = 8388608
OFN_DONTADDTORECENT = 33554432
OFN_FORCESHOWHIDDEN = 268435456  # Show All files including System and hidden files
OFN_EX_NOPLACESBAR = 1
OFN_SHAREFALLTHROUGH = 2
OFN_SHARENOWARN = 1
OFN_SHAREWARN = 0
CDN_FIRST = PY_0U - 601
CDN_LAST = PY_0U - 699
CDN_INITDONE = CDN_FIRST - 0
CDN_SELCHANGE = CDN_FIRST - 1
CDN_FOLDERCHANGE = CDN_FIRST - 2
CDN_SHAREVIOLATION = CDN_FIRST - 3
CDN_HELP = CDN_FIRST - 4
CDN_FILEOK = CDN_FIRST - 5
CDN_TYPECHANGE = CDN_FIRST - 6
CDN_INCLUDEITEM = CDN_FIRST - 7
CDM_FIRST = WM_USER + 100
CDM_LAST = WM_USER + 200
CDM_GETSPEC = CDM_FIRST + 0
CDM_GETFILEPATH = CDM_FIRST + 1
CDM_GETFOLDERPATH = CDM_FIRST + 2
CDM_GETFOLDERIDLIST = CDM_FIRST + 3
CDM_SETCONTROLTEXT = CDM_FIRST + 4
CDM_HIDECONTROL = CDM_FIRST + 5
CDM_SETDEFEXT = CDM_FIRST + 6
CC_RGBINIT = 1
CC_FULLOPEN = 2
CC_PREVENTFULLOPEN = 4
CC_SHOWHELP = 8
CC_ENABLEHOOK = 16
CC_ENABLETEMPLATE = 32
CC_ENABLETEMPLATEHANDLE = 64
CC_SOLIDCOLOR = 128
CC_ANYCOLOR = 256
FR_DOWN = 1
FR_WHOLEWORD = 2
FR_MATCHCASE = 4
FR_FINDNEXT = 8
FR_REPLACE = 16
FR_REPLACEALL = 32
FR_DIALOGTERM = 64
FR_SHOWHELP = 128
FR_ENABLEHOOK = 256
FR_ENABLETEMPLATE = 512
FR_NOUPDOWN = 1024
FR_NOMATCHCASE = 2048
FR_NOWHOLEWORD = 4096
FR_ENABLETEMPLATEHANDLE = 8192
FR_HIDEUPDOWN = 16384
FR_HIDEMATCHCASE = 32768
FR_HIDEWHOLEWORD = 65536
CF_SCREENFONTS = 1
CF_PRINTERFONTS = 2
CF_BOTH = CF_SCREENFONTS | CF_PRINTERFONTS
CF_SHOWHELP = 4
CF_ENABLEHOOK = 8
CF_ENABLETEMPLATE = 16
CF_ENABLETEMPLATEHANDLE = 32
CF_INITTOLOGFONTSTRUCT = 64
CF_USESTYLE = 128
CF_EFFECTS = 256
CF_APPLY = 512
CF_ANSIONLY = 1024
CF_SCRIPTSONLY = CF_ANSIONLY
CF_NOVECTORFONTS = 2048
CF_NOOEMFONTS = CF_NOVECTORFONTS
CF_NOSIMULATIONS = 4096
CF_LIMITSIZE = 8192
CF_FIXEDPITCHONLY = 16384
CF_WYSIWYG = 32768  # must also have CF_SCREENFONTS & CF_PRINTERFONTS
CF_FORCEFONTEXIST = 65536
CF_SCALABLEONLY = 131072
CF_TTONLY = 262144
CF_NOFACESEL = 524288
CF_NOSTYLESEL = 1048576
CF_NOSIZESEL = 2097152
CF_SELECTSCRIPT = 4194304
CF_NOSCRIPTSEL = 8388608
CF_NOVERTFONTS = 16777216
SIMULATED_FONTTYPE = 32768
PRINTER_FONTTYPE = 16384
SCREEN_FONTTYPE = 8192
BOLD_FONTTYPE = 256
ITALIC_FONTTYPE = 512
REGULAR_FONTTYPE = 1024
OPENTYPE_FONTTYPE = 65536
TYPE1_FONTTYPE = 131072
DSIG_FONTTYPE = 262144
WM_CHOOSEFONT_GETLOGFONT = WM_USER + 1
WM_CHOOSEFONT_SETLOGFONT = WM_USER + 101
WM_CHOOSEFONT_SETFLAGS = WM_USER + 102
LBSELCHSTRINGA = "commdlg_LBSelChangedNotify"
SHAREVISTRINGA = "commdlg_ShareViolation"
FILEOKSTRINGA = "commdlg_FileNameOK"
COLOROKSTRINGA = "commdlg_ColorOK"
SETRGBSTRINGA = "commdlg_SetRGBColor"
HELPMSGSTRINGA = "commdlg_help"
FINDMSGSTRINGA = "commdlg_FindReplace"
LBSELCHSTRING = LBSELCHSTRINGA
SHAREVISTRING = SHAREVISTRINGA
FILEOKSTRING = FILEOKSTRINGA
COLOROKSTRING = COLOROKSTRINGA
SETRGBSTRING = SETRGBSTRINGA
HELPMSGSTRING = HELPMSGSTRINGA
FINDMSGSTRING = FINDMSGSTRINGA
CD_LBSELNOITEMS = -1
CD_LBSELCHANGE = 0
CD_LBSELSUB = 1
CD_LBSELADD = 2
PD_ALLPAGES = 0
PD_SELECTION = 1
PD_PAGENUMS = 2
PD_NOSELECTION = 4
PD_NOPAGENUMS = 8
PD_COLLATE = 16
PD_PRINTTOFILE = 32
PD_PRINTSETUP = 64
PD_NOWARNING = 128
PD_RETURNDC = 256
PD_RETURNIC = 512
PD_RETURNDEFAULT = 1024
PD_SHOWHELP = 2048
PD_ENABLEPRINTHOOK = 4096
PD_ENABLESETUPHOOK = 8192
PD_ENABLEPRINTTEMPLATE = 16384
PD_ENABLESETUPTEMPLATE = 32768
PD_ENABLEPRINTTEMPLATEHANDLE = 65536
PD_ENABLESETUPTEMPLATEHANDLE = 131072
PD_USEDEVMODECOPIES = 262144
PD_DISABLEPRINTTOFILE = 524288
PD_HIDEPRINTTOFILE = 1048576
PD_NONETWORKBUTTON = 2097152
DN_DEFAULTPRN = 1
WM_PSD_PAGESETUPDLG = WM_USER
WM_PSD_FULLPAGERECT = WM_USER + 1
WM_PSD_MINMARGINRECT = WM_USER + 2
WM_PSD_MARGINRECT = WM_USER + 3
WM_PSD_GREEKTEXTRECT = WM_USER + 4
WM_PSD_ENVSTAMPRECT = WM_USER + 5
WM_PSD_YAFULLPAGERECT = WM_USER + 6
PSD_DEFAULTMINMARGINS = 0  # default (printer's)
PSD_INWININIINTLMEASURE = 0  # 1st of 4 possible
PSD_MINMARGINS = 1  # use caller's
PSD_MARGINS = 2  # use caller's
PSD_INTHOUSANDTHSOFINCHES = 4  # 2nd of 4 possible
PSD_INHUNDREDTHSOFMILLIMETERS = 8  # 3rd of 4 possible
PSD_DISABLEMARGINS = 16
PSD_DISABLEPRINTER = 32
PSD_NOWARNING = 128  # must be same as PD_*
PSD_DISABLEORIENTATION = 256
PSD_RETURNDEFAULT = 1024  # must be same as PD_*
PSD_DISABLEPAPER = 512
PSD_SHOWHELP = 2048  # must be same as PD_*
PSD_ENABLEPAGESETUPHOOK = 8192  # must be same as PD_*
PSD_ENABLEPAGESETUPTEMPLATE = 32768  # must be same as PD_*
PSD_ENABLEPAGESETUPTEMPLATEHANDLE = 131072  # must be same as PD_*
PSD_ENABLEPAGEPAINTHOOK = 262144
PSD_DISABLEPAGEPAINTING = 524288
PSD_NONETWORKBUTTON = 2097152  # must be same as PD_*

# Generated by h2py from winreg.h
HKEY_CLASSES_ROOT = -2147483648
HKEY_CURRENT_USER = -2147483647
HKEY_LOCAL_MACHINE = -2147483646
HKEY_USERS = -2147483645
HKEY_PERFORMANCE_DATA = -2147483644
HKEY_CURRENT_CONFIG = -2147483643
HKEY_DYN_DATA = -2147483642
HKEY_PERFORMANCE_TEXT = -2147483568  # ?? 4Jan98
HKEY_PERFORMANCE_NLSTEXT = -2147483552  # ?? 4Jan98

# Generated by h2py from winuser.h
HWND_BROADCAST = 65535
HWND_DESKTOP = 0
HWND_TOP = 0
HWND_BOTTOM = 1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_MESSAGE = -3

# winuser.h line 4601
SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_CXVSCROLL = 2
SM_CYHSCROLL = 3
SM_CYCAPTION = 4
SM_CXBORDER = 5
SM_CYBORDER = 6
SM_CXDLGFRAME = 7
SM_CYDLGFRAME = 8
SM_CYVTHUMB = 9
SM_CXHTHUMB = 10
SM_CXICON = 11
SM_CYICON = 12
SM_CXCURSOR = 13
SM_CYCURSOR = 14
SM_CYMENU = 15
SM_CXFULLSCREEN = 16
SM_CYFULLSCREEN = 17
SM_CYKANJIWINDOW = 18
SM_MOUSEPRESENT = 19
SM_CYVSCROLL = 20
SM_CXHSCROLL = 21
SM_DEBUG = 22
SM_SWAPBUTTON = 23
SM_RESERVED1 = 24
SM_RESERVED2 = 25
SM_RESERVED3 = 26
SM_RESERVED4 = 27
SM_CXMIN = 28
SM_CYMIN = 29
SM_CXSIZE = 30
SM_CYSIZE = 31
SM_CXFRAME = 32
SM_CYFRAME = 33
SM_CXMINTRACK = 34
SM_CYMINTRACK = 35
SM_CXDOUBLECLK = 36
SM_CYDOUBLECLK = 37
SM_CXICONSPACING = 38
SM_CYICONSPACING = 39
SM_MENUDROPALIGNMENT = 40
SM_PENWINDOWS = 41
SM_DBCSENABLED = 42
SM_CMOUSEBUTTONS = 43
SM_CXFIXEDFRAME = SM_CXDLGFRAME
SM_CYFIXEDFRAME = SM_CYDLGFRAME
SM_CXSIZEFRAME = SM_CXFRAME
SM_CYSIZEFRAME = SM_CYFRAME
SM_SECURE = 44
SM_CXEDGE = 45
SM_CYEDGE = 46
SM_CXMINSPACING = 47
SM_CYMINSPACING = 48
SM_CXSMICON = 49
SM_CYSMICON = 50
SM_CYSMCAPTION = 51
SM_CXSMSIZE = 52
SM_CYSMSIZE = 53
SM_CXMENUSIZE = 54
SM_CYMENUSIZE = 55
SM_ARRANGE = 56
SM_CXMINIMIZED = 57
SM_CYMINIMIZED = 58
SM_CXMAXTRACK = 59
SM_CYMAXTRACK = 60
SM_CXMAXIMIZED = 61
SM_CYMAXIMIZED = 62
SM_NETWORK = 63
SM_CLEANBOOT = 67
SM_CXDRAG = 68
SM_CYDRAG = 69
SM_SHOWSOUNDS = 70
SM_CXMENUCHECK = 71
SM_CYMENUCHECK = 72
SM_SLOWMACHINE = 73
SM_MIDEASTENABLED = 74
SM_MOUSEWHEELPRESENT = 75
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80
SM_SAMEDISPLAYFORMAT = 81
SM_CMETRICS = 83
MNC_IGNORE = 0
MNC_CLOSE = 1
MNC_EXECUTE = 2
MNC_SELECT = 3
MNS_NOCHECK = -2147483648
MNS_MODELESS = 1073741824
MNS_DRAGDROP = 536870912
MNS_AUTODISMISS = 268435456
MNS_NOTIFYBYPOS = 134217728
MNS_CHECKORBMP = 67108864
MIM_MAXHEIGHT = 1
MIM_BACKGROUND = 2
MIM_HELPID = 4
MIM_MENUDATA = 8
MIM_STYLE = 16
MIM_APPLYTOSUBMENUS = -2147483648
MND_CONTINUE = 0
MND_ENDMENU = 1
MNGOF_GAP = 3
MNGO_NOINTERFACE = 0
MNGO_NOERROR = 1
MIIM_STATE = 1
MIIM_ID = 2
MIIM_SUBMENU = 4
MIIM_CHECKMARKS = 8
MIIM_TYPE = 16
MIIM_DATA = 32
MIIM_STRING = 64
MIIM_BITMAP = 128
MIIM_FTYPE = 256
HBMMENU_CALLBACK = -1
HBMMENU_SYSTEM = 1
HBMMENU_MBAR_RESTORE = 2
HBMMENU_MBAR_MINIMIZE = 3
HBMMENU_MBAR_CLOSE = 5
HBMMENU_MBAR_CLOSE_D = 6
HBMMENU_MBAR_MINIMIZE_D = 7
HBMMENU_POPUP_CLOSE = 8
HBMMENU_POPUP_RESTORE = 9
HBMMENU_POPUP_MAXIMIZE = 10
HBMMENU_POPUP_MINIMIZE = 11
GMDI_USEDISABLED = 1
GMDI_GOINTOPOPUPS = 2
TPM_LEFTBUTTON = 0
TPM_RIGHTBUTTON = 2
TPM_LEFTALIGN = 0
TPM_CENTERALIGN = 4
TPM_RIGHTALIGN = 8
TPM_TOPALIGN = 0
TPM_VCENTERALIGN = 16
TPM_BOTTOMALIGN = 32
TPM_HORIZONTAL = 0
TPM_VERTICAL = 64
TPM_NONOTIFY = 128
TPM_RETURNCMD = 256
TPM_RECURSE = 1
DOF_EXECUTABLE = 32769
DOF_DOCUMENT = 32770
DOF_DIRECTORY = 32771
DOF_MULTIPLE = 32772
DOF_PROGMAN = 1
DOF_SHELLDATA = 2
DO_DROPFILE = 1162627398
DO_PRINTFILE = 1414419024
DT_TOP = 0
DT_LEFT = 0
DT_CENTER = 1
DT_RIGHT = 2
DT_VCENTER = 4
DT_BOTTOM = 8
DT_WORDBREAK = 16
DT_SINGLELINE = 32
DT_EXPANDTABS = 64
DT_TABSTOP = 128
DT_NOCLIP = 256
DT_EXTERNALLEADING = 512
DT_CALCRECT = 1024
DT_NOPREFIX = 2048
DT_INTERNAL = 4096
DT_EDITCONTROL = 8192
DT_PATH_ELLIPSIS = 16384
DT_END_ELLIPSIS = 32768
DT_MODIFYSTRING = 65536
DT_RTLREADING = 131072
DT_WORD_ELLIPSIS = 262144
DST_COMPLEX = 0
DST_TEXT = 1
DST_PREFIXTEXT = 2
DST_ICON = 3
DST_BITMAP = 4
DSS_NORMAL = 0
DSS_UNION = 16
DSS_DISABLED = 32
DSS_MONO = 128
DSS_RIGHT = 32768
DCX_WINDOW = 1
DCX_CACHE = 2
DCX_NORESETATTRS = 4
DCX_CLIPCHILDREN = 8
DCX_CLIPSIBLINGS = 16
DCX_PARENTCLIP = 32
DCX_EXCLUDERGN = 64
DCX_INTERSECTRGN = 128
DCX_EXCLUDEUPDATE = 256
DCX_INTERSECTUPDATE = 512
DCX_LOCKWINDOWUPDATE = 1024
DCX_VALIDATE = 2097152
CUDR_NORMAL = 0
CUDR_NOSNAPTOGRID = 1
CUDR_NORESOLVEPOSITIONS = 2
CUDR_NOCLOSEGAPS = 4
CUDR_NEGATIVECOORDS = 8
CUDR_NOPRIMARY = 16
RDW_INVALIDATE = 1
RDW_INTERNALPAINT = 2
RDW_ERASE = 4
RDW_VALIDATE = 8
RDW_NOINTERNALPAINT = 16
RDW_NOERASE = 32
RDW_NOCHILDREN = 64
RDW_ALLCHILDREN = 128
RDW_UPDATENOW = 256
RDW_ERASENOW = 512
RDW_FRAME = 1024
RDW_NOFRAME = 2048
SW_SCROLLCHILDREN = 1
SW_INVALIDATE = 2
SW_ERASE = 4
SW_SMOOTHSCROLL = 16  # Use smooth scrolling
ESB_ENABLE_BOTH = 0
ESB_DISABLE_BOTH = 3
ESB_DISABLE_LEFT = 1
ESB_DISABLE_RIGHT = 2
ESB_DISABLE_UP = 1
ESB_DISABLE_DOWN = 2
ESB_DISABLE_LTUP = ESB_DISABLE_LEFT
ESB_DISABLE_RTDN = ESB_DISABLE_RIGHT
HELPINFO_WINDOW = 1
HELPINFO_MENUITEM = 2
MB_OK = 0
MB_OKCANCEL = 1
MB_ABORTRETRYIGNORE = 2
MB_YESNOCANCEL = 3
MB_YESNO = 4
MB_RETRYCANCEL = 5
MB_ICONHAND = 16
MB_ICONQUESTION = 32
MB_ICONEXCLAMATION = 48
MB_ICONASTERISK = 64
MB_ICONWARNING = MB_ICONEXCLAMATION
MB_ICONERROR = MB_ICONHAND
MB_ICONINFORMATION = MB_ICONASTERISK
MB_ICONSTOP = MB_ICONHAND
MB_DEFBUTTON1 = 0
MB_DEFBUTTON2 = 256
MB_DEFBUTTON3 = 512
MB_DEFBUTTON4 = 768
MB_APPLMODAL = 0
MB_SYSTEMMODAL = 4096
MB_TASKMODAL = 8192
MB_HELP = 16384
MB_NOFOCUS = 32768
MB_SETFOREGROUND = 65536
MB_DEFAULT_DESKTOP_ONLY = 131072
MB_TOPMOST = 262144
MB_RIGHT = 524288
MB_RTLREADING = 1048576
MB_SERVICE_NOTIFICATION = 2097152
MB_TYPEMASK = 15
MB_USERICON = 128
MB_ICONMASK = 240
MB_DEFMASK = 3840
MB_MODEMASK = 12288
MB_MISCMASK = 49152
# winuser.h line 6373
CWP_ALL = 0
CWP_SKIPINVISIBLE = 1
CWP_SKIPDISABLED = 2
CWP_SKIPTRANSPARENT = 4
CTLCOLOR_MSGBOX = 0
CTLCOLOR_EDIT = 1
CTLCOLOR_LISTBOX = 2
CTLCOLOR_BTN = 3
CTLCOLOR_DLG = 4
CTLCOLOR_SCROLLBAR = 5
CTLCOLOR_STATIC = 6
CTLCOLOR_MAX = 7
COLOR_SCROLLBAR = 0
COLOR_BACKGROUND = 1
COLOR_ACTIVECAPTION = 2
COLOR_INACTIVECAPTION = 3
COLOR_MENU = 4
COLOR_WINDOW = 5
COLOR_WINDOWFRAME = 6
COLOR_MENUTEXT = 7
COLOR_WINDOWTEXT = 8
COLOR_CAPTIONTEXT = 9
COLOR_ACTIVEBORDER = 10
COLOR_INACTIVEBORDER = 11
COLOR_APPWORKSPACE = 12
COLOR_HIGHLIGHT = 13
COLOR_HIGHLIGHTTEXT = 14
COLOR_BTNFACE = 15
COLOR_BTNSHADOW = 16
COLOR_GRAYTEXT = 17
COLOR_BTNTEXT = 18
COLOR_INACTIVECAPTIONTEXT = 19
COLOR_BTNHIGHLIGHT = 20
COLOR_3DDKSHADOW = 21
COLOR_3DLIGHT = 22
COLOR_INFOTEXT = 23
COLOR_INFOBK = 24
COLOR_HOTLIGHT = 26
COLOR_GRADIENTACTIVECAPTION = 27
COLOR_GRADIENTINACTIVECAPTION = 28
COLOR_DESKTOP = COLOR_BACKGROUND
COLOR_3DFACE = COLOR_BTNFACE
COLOR_3DSHADOW = COLOR_BTNSHADOW
COLOR_3DHIGHLIGHT = COLOR_BTNHIGHLIGHT
COLOR_3DHILIGHT = COLOR_BTNHIGHLIGHT
COLOR_BTNHILIGHT = COLOR_BTNHIGHLIGHT
GW_HWNDFIRST = 0
GW_HWNDLAST = 1
GW_HWNDNEXT = 2
GW_HWNDPREV = 3
GW_OWNER = 4
GW_CHILD = 5
GW_ENABLEDPOPUP = 6
GW_MAX = 6
MF_INSERT = 0
MF_CHANGE = 128
MF_APPEND = 256
MF_DELETE = 512
MF_REMOVE = 4096
MF_BYCOMMAND = 0
MF_BYPOSITION = 1024
MF_SEPARATOR = 2048
MF_ENABLED = 0
MF_GRAYED = 1
MF_DISABLED = 2
MF_UNCHECKED = 0
MF_CHECKED = 8
MF_USECHECKBITMAPS = 512
MF_STRING = 0
MF_BITMAP = 4
MF_OWNERDRAW = 256
MF_POPUP = 16
MF_MENUBARBREAK = 32
MF_MENUBREAK = 64
MF_UNHILITE = 0
MF_HILITE = 128
MF_DEFAULT = 4096
MF_SYSMENU = 8192
MF_HELP = 16384
MF_RIGHTJUSTIFY = 16384
MF_MOUSESELECT = 32768
MF_END = 128
MFT_STRING = MF_STRING
MFT_BITMAP = MF_BITMAP
MFT_MENUBARBREAK = MF_MENUBARBREAK
MFT_MENUBREAK = MF_MENUBREAK
MFT_OWNERDRAW = MF_OWNERDRAW
MFT_RADIOCHECK = 512
MFT_SEPARATOR = MF_SEPARATOR
MFT_RIGHTORDER = 8192
MFT_RIGHTJUSTIFY = MF_RIGHTJUSTIFY
MFS_GRAYED = 3
MFS_DISABLED = MFS_GRAYED
MFS_CHECKED = MF_CHECKED
MFS_HILITE = MF_HILITE
MFS_ENABLED = MF_ENABLED
MFS_UNCHECKED = MF_UNCHECKED
MFS_UNHILITE = MF_UNHILITE
MFS_DEFAULT = MF_DEFAULT
MFS_MASK = 4235
MFS_HOTTRACKDRAWN = 268435456
MFS_CACHEDBMP = 536870912
MFS_BOTTOMGAPDROP = 1073741824
MFS_TOPGAPDROP = -2147483648
MFS_GAPDROP = -1073741824
SC_SIZE = 61440
SC_MOVE = 61456
SC_MINIMIZE = 61472
SC_MAXIMIZE = 61488
SC_NEXTWINDOW = 61504
SC_PREVWINDOW = 61520
SC_CLOSE = 61536
SC_VSCROLL = 61552
SC_HSCROLL = 61568
SC_MOUSEMENU = 61584
SC_KEYMENU = 61696
SC_ARRANGE = 61712
SC_RESTORE = 61728
SC_TASKLIST = 61744
SC_SCREENSAVE = 61760
SC_HOTKEY = 61776
SC_DEFAULT = 61792
SC_MONITORPOWER = 61808
SC_CONTEXTHELP = 61824
SC_SEPARATOR = 61455
SC_ICON = SC_MINIMIZE
SC_ZOOM = SC_MAXIMIZE
IDC_ARROW = 32512
IDC_IBEAM = 32513
IDC_WAIT = 32514
IDC_CROSS = 32515
IDC_UPARROW = 32516
IDC_SIZE = 32640  # OBSOLETE: use IDC_SIZEALL
IDC_ICON = 32641  # OBSOLETE: use IDC_ARROW
IDC_SIZENWSE = 32642
IDC_SIZENESW = 32643
IDC_SIZEWE = 32644
IDC_SIZENS = 32645
IDC_SIZEALL = 32646
IDC_NO = 32648
IDC_HAND = 32649
IDC_APPSTARTING = 32650
IDC_HELP = 32651
IMAGE_BITMAP = 0
IMAGE_ICON = 1
IMAGE_CURSOR = 2
IMAGE_ENHMETAFILE = 3
LR_DEFAULTCOLOR = 0
LR_MONOCHROME = 1
LR_COLOR = 2
LR_COPYRETURNORG = 4
LR_COPYDELETEORG = 8
LR_LOADFROMFILE = 16
LR_LOADTRANSPARENT = 32
LR_DEFAULTSIZE = 64
LR_LOADREALSIZE = 128
LR_LOADMAP3DCOLORS = 4096
LR_CREATEDIBSECTION = 8192
LR_COPYFROMRESOURCE = 16384
LR_SHARED = 32768
DI_MASK = 1
DI_IMAGE = 2
DI_NORMAL = 3
DI_COMPAT = 4
DI_DEFAULTSIZE = 8
RES_ICON = 1
RES_CURSOR = 2
OBM_CLOSE = 32754
OBM_UPARROW = 32753
OBM_DNARROW = 32752
OBM_RGARROW = 32751
OBM_LFARROW = 32750
OBM_REDUCE = 32749
OBM_ZOOM = 32748
OBM_RESTORE = 32747
OBM_REDUCED = 32746
OBM_ZOOMD = 32745
OBM_RESTORED = 32744
OBM_UPARROWD = 32743
OBM_DNARROWD = 32742
OBM_RGARROWD = 32741
OBM_LFARROWD = 32740
OBM_MNARROW = 32739
OBM_COMBO = 32738
OBM_UPARROWI = 32737
OBM_DNARROWI = 32736
OBM_RGARROWI = 32735
OBM_LFARROWI = 32734
OBM_OLD_CLOSE = 32767
OBM_SIZE = 32766
OBM_OLD_UPARROW = 32765
OBM_OLD_DNARROW = 32764
OBM_OLD_RGARROW = 32763
OBM_OLD_LFARROW = 32762
OBM_BTSIZE = 32761
OBM_CHECK = 32760
OBM_CHECKBOXES = 32759
OBM_BTNCORNERS = 32758
OBM_OLD_REDUCE = 32757
OBM_OLD_ZOOM = 32756
OBM_OLD_RESTORE = 32755
OCR_NORMAL = 32512
OCR_IBEAM = 32513
OCR_WAIT = 32514
OCR_CROSS = 32515
OCR_UP = 32516
OCR_SIZE = 32640
OCR_ICON = 32641
OCR_SIZENWSE = 32642
OCR_SIZENESW = 32643
OCR_SIZEWE = 32644
OCR_SIZENS = 32645
OCR_SIZEALL = 32646
OCR_ICOCUR = 32647
OCR_NO = 32648
OCR_HAND = 32649
OCR_APPSTARTING = 32650
# winuser.h line 7455
OIC_SAMPLE = 32512
OIC_HAND = 32513
OIC_QUES = 32514
OIC_BANG = 32515
OIC_NOTE = 32516
OIC_WINLOGO = 32517
OIC_WARNING = OIC_BANG
OIC_ERROR = OIC_HAND
OIC_INFORMATION = OIC_NOTE
ORD_LANGDRIVER = 1
IDI_APPLICATION = 32512
IDI_HAND = 32513
IDI_QUESTION = 32514
IDI_EXCLAMATION = 32515
IDI_ASTERISK = 32516
IDI_WINLOGO = 32517
IDI_WARNING = IDI_EXCLAMATION
IDI_ERROR = IDI_HAND
IDI_INFORMATION = IDI_ASTERISK
IDOK = 1
IDCANCEL = 2
IDABORT = 3
IDRETRY = 4
IDIGNORE = 5
IDYES = 6
IDNO = 7
IDCLOSE = 8
IDHELP = 9
ES_LEFT = 0
ES_CENTER = 1
ES_RIGHT = 2
ES_MULTILINE = 4
ES_UPPERCASE = 8
ES_LOWERCASE = 16
ES_PASSWORD = 32
ES_AUTOVSCROLL = 64
ES_AUTOHSCROLL = 128
ES_NOHIDESEL = 256
ES_OEMCONVERT = 1024
ES_READONLY = 2048
ES_WANTRETURN = 4096
ES_NUMBER = 8192
EN_SETFOCUS = 256
EN_KILLFOCUS = 512
EN_CHANGE = 768
EN_UPDATE = 1024
EN_ERRSPACE = 1280
EN_MAXTEXT = 1281
EN_HSCROLL = 1537
EN_VSCROLL = 1538
EC_LEFTMARGIN = 1
EC_RIGHTMARGIN = 2
EC_USEFONTINFO = 65535
EMSIS_COMPOSITIONSTRING = 1
EIMES_GETCOMPSTRATONCE = 1
EIMES_CANCELCOMPSTRINFOCUS = 2
EIMES_COMPLETECOMPSTRKILLFOCUS = 4
EM_GETSEL = 176
EM_SETSEL = 177
EM_GETRECT = 178
EM_SETRECT = 179
EM_SETRECTNP = 180
EM_SCROLL = 181
EM_LINESCROLL = 182
EM_SCROLLCARET = 183
EM_GETMODIFY = 184
EM_SETMODIFY = 185
EM_GETLINECOUNT = 186
EM_LINEINDEX = 187
EM_SETHANDLE = 188
EM_GETHANDLE = 189
EM_GETTHUMB = 190
EM_LINELENGTH = 193
EM_REPLACESEL = 194
EM_GETLINE = 196
EM_LIMITTEXT = 197
EM_CANUNDO = 198
EM_UNDO = 199
EM_FMTLINES = 200
EM_LINEFROMCHAR = 201
EM_SETTABSTOPS = 203
EM_SETPASSWORDCHAR = 204
EM_EMPTYUNDOBUFFER = 205
EM_GETFIRSTVISIBLELINE = 206
EM_SETREADONLY = 207
EM_SETWORDBREAKPROC = 208
EM_GETWORDBREAKPROC = 209
EM_GETPASSWORDCHAR = 210
EM_SETMARGINS = 211
EM_GETMARGINS = 212
EM_SETLIMITTEXT = EM_LIMITTEXT
EM_GETLIMITTEXT = 213
EM_POSFROMCHAR = 214
EM_CHARFROMPOS = 215
EM_SETIMESTATUS = 216
EM_GETIMESTATUS = 217
WB_LEFT = 0
WB_RIGHT = 1
WB_ISDELIMITER = 2
BS_PUSHBUTTON = 0
BS_DEFPUSHBUTTON = 1
BS_CHECKBOX = 2
BS_AUTOCHECKBOX = 3
BS_RADIOBUTTON = 4
BS_3STATE = 5
BS_AUTO3STATE = 6
BS_GROUPBOX = 7
BS_USERBUTTON = 8
BS_AUTORADIOBUTTON = 9
BS_OWNERDRAW = 11
BS_LEFTTEXT = 32
BS_TEXT = 0
BS_ICON = 64
BS_BITMAP = 128
BS_LEFT = 256
BS_RIGHT = 512
BS_CENTER = 768
BS_TOP = 1024
BS_BOTTOM = 2048
BS_VCENTER = 3072
BS_PUSHLIKE = 4096
BS_MULTILINE = 8192
BS_NOTIFY = 16384
BS_FLAT = 32768
BS_RIGHTBUTTON = BS_LEFTTEXT
BN_CLICKED = 0
BN_PAINT = 1
BN_HILITE = 2
BN_UNHILITE = 3
BN_DISABLE = 4
BN_DOUBLECLICKED = 5
BN_PUSHED = BN_HILITE
BN_UNPUSHED = BN_UNHILITE
BN_DBLCLK = BN_DOUBLECLICKED
BN_SETFOCUS = 6
BN_KILLFOCUS = 7
BM_GETCHECK = 240
BM_SETCHECK = 241
BM_GETSTATE = 242
BM_SETSTATE = 243
BM_SETSTYLE = 244
BM_CLICK = 245
BM_GETIMAGE = 246
BM_SETIMAGE = 247
BST_UNCHECKED = 0
BST_CHECKED = 1
BST_INDETERMINATE = 2
BST_PUSHED = 4
BST_FOCUS = 8
SS_LEFT = 0
SS_CENTER = 1
SS_RIGHT = 2
SS_ICON = 3
SS_BLACKRECT = 4
SS_GRAYRECT = 5
SS_WHITERECT = 6
SS_BLACKFRAME = 7
SS_GRAYFRAME = 8
SS_WHITEFRAME = 9
SS_USERITEM = 10
SS_SIMPLE = 11
SS_LEFTNOWORDWRAP = 12
SS_BITMAP = 14
SS_OWNERDRAW = 13
SS_ENHMETAFILE = 15
SS_ETCHEDHORZ = 16
SS_ETCHEDVERT = 17
SS_ETCHEDFRAME = 18
SS_TYPEMASK = 31
SS_NOPREFIX = 128
SS_NOTIFY = 256
SS_CENTERIMAGE = 512
SS_RIGHTJUST = 1024
SS_REALSIZEIMAGE = 2048
SS_SUNKEN = 4096
SS_ENDELLIPSIS = 16384
SS_PATHELLIPSIS = 32768
SS_WORDELLIPSIS = 49152
SS_ELLIPSISMASK = 49152
STM_SETICON = 368
STM_GETICON = 369
STM_SETIMAGE = 370
STM_GETIMAGE = 371
STN_CLICKED = 0
STN_DBLCLK = 1
STN_ENABLE = 2
STN_DISABLE = 3
STM_MSGMAX = 372
DWL_MSGRESULT = 0
DWL_DLGPROC = 4
DWL_USER = 8
DDL_READWRITE = 0
DDL_READONLY = 1
DDL_HIDDEN = 2
DDL_SYSTEM = 4
DDL_DIRECTORY = 16
DDL_ARCHIVE = 32
DDL_POSTMSGS = 8192
DDL_DRIVES = 16384
DDL_EXCLUSIVE = 32768

# from winuser.h line 153
RT_CURSOR = 1
RT_BITMAP = 2
RT_ICON = 3
RT_MENU = 4
RT_DIALOG = 5
RT_STRING = 6
RT_FONTDIR = 7
RT_FONT = 8
RT_ACCELERATOR = 9
RT_RCDATA = 10
RT_MESSAGETABLE = 11
DIFFERENCE = 11
RT_GROUP_CURSOR = RT_CURSOR + DIFFERENCE
RT_GROUP_ICON = RT_ICON + DIFFERENCE
RT_VERSION = 16
RT_DLGINCLUDE = 17
RT_PLUGPLAY = 19
RT_VXD = 20
RT_ANICURSOR = 21
RT_ANIICON = 22
RT_HTML = 23
# from winuser.h line 218
SB_HORZ = 0
SB_VERT = 1
SB_CTL = 2
SB_BOTH = 3
SB_LINEUP = 0
SB_LINELEFT = 0
SB_LINEDOWN = 1
SB_LINERIGHT = 1
SB_PAGEUP = 2
SB_PAGELEFT = 2
SB_PAGEDOWN = 3
SB_PAGERIGHT = 3
SB_THUMBPOSITION = 4
SB_THUMBTRACK = 5
SB_TOP = 6
SB_LEFT = 6
SB_BOTTOM = 7
SB_RIGHT = 7
SB_ENDSCROLL = 8
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_NORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_MAXIMIZE = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_SHOWMINNOACTIVE = 7
SW_SHOWNA = 8
SW_RESTORE = 9
SW_SHOWDEFAULT = 10
SW_FORCEMINIMIZE = 11
SW_MAX = 11
HIDE_WINDOW = 0
SHOW_OPENWINDOW = 1
SHOW_ICONWINDOW = 2
SHOW_FULLSCREEN = 3
SHOW_OPENNOACTIVATE = 4
SW_PARENTCLOSING = 1
SW_OTHERZOOM = 2
SW_PARENTOPENING = 3
SW_OTHERUNZOOM = 4
AW_HOR_POSITIVE = 1
AW_HOR_NEGATIVE = 2
AW_VER_POSITIVE = 4
AW_VER_NEGATIVE = 8
AW_CENTER = 16
AW_HIDE = 65536
AW_ACTIVATE = 131072
AW_SLIDE = 262144
AW_BLEND = 524288
KF_EXTENDED = 256
KF_DLGMODE = 2048
KF_MENUMODE = 4096
KF_ALTDOWN = 8192
KF_REPEAT = 16384
KF_UP = 32768
VK_LBUTTON = 1
VK_RBUTTON = 2
VK_CANCEL = 3
VK_MBUTTON = 4
VK_BACK = 8
VK_TAB = 9
VK_CLEAR = 12
VK_RETURN = 13
VK_SHIFT = 16
VK_CONTROL = 17
VK_MENU = 18
VK_PAUSE = 19
VK_CAPITAL = 20
VK_KANA = 21
VK_HANGEUL = 21  # old name - should be here for compatibility
VK_HANGUL = 21
VK_JUNJA = 23
VK_FINAL = 24
VK_HANJA = 25
VK_KANJI = 25
VK_ESCAPE = 27
VK_CONVERT = 28
VK_NONCONVERT = 29
VK_ACCEPT = 30
VK_MODECHANGE = 31
VK_SPACE = 32
VK_PRIOR = 33
VK_NEXT = 34
VK_END = 35
VK_HOME = 36
VK_LEFT = 37
VK_UP = 38
VK_RIGHT = 39
VK_DOWN = 40
VK_SELECT = 41
VK_PRINT = 42
VK_EXECUTE = 43
VK_SNAPSHOT = 44
VK_INSERT = 45
VK_DELETE = 46
VK_HELP = 47
VK_LWIN = 91
VK_RWIN = 92
VK_APPS = 93
VK_NUMPAD0 = 96
VK_NUMPAD1 = 97
VK_NUMPAD2 = 98
VK_NUMPAD3 = 99
VK_NUMPAD4 = 100
VK_NUMPAD5 = 101
VK_NUMPAD6 = 102
VK_NUMPAD7 = 103
VK_NUMPAD8 = 104
VK_NUMPAD9 = 105
VK_MULTIPLY = 106
VK_ADD = 107
VK_SEPARATOR = 108
VK_SUBTRACT = 109
VK_DECIMAL = 110
VK_DIVIDE = 111
VK_F1 = 112
VK_F2 = 113
VK_F3 = 114
VK_F4 = 115
VK_F5 = 116
VK_F6 = 117
VK_F7 = 118
VK_F8 = 119
VK_F9 = 120
VK_F10 = 121
VK_F11 = 122
VK_F12 = 123
VK_F13 = 124
VK_F14 = 125
VK_F15 = 126
VK_F16 = 127
VK_F17 = 128
VK_F18 = 129
VK_F19 = 130
VK_F20 = 131
VK_F21 = 132
VK_F22 = 133
VK_F23 = 134
VK_F24 = 135
VK_NUMLOCK = 144
VK_SCROLL = 145
VK_LSHIFT = 160
VK_RSHIFT = 161
VK_LCONTROL = 162
VK_RCONTROL = 163
VK_LMENU = 164
VK_RMENU = 165
VK_PROCESSKEY = 229
VK_ATTN = 246
VK_CRSEL = 247
VK_EXSEL = 248
VK_EREOF = 249
VK_PLAY = 250
VK_ZOOM = 251
VK_NONAME = 252
VK_PA1 = 253
VK_OEM_CLEAR = 254
# multi-media related "keys"
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_BROWSER_BACK = 0xA6
VK_BROWSER_FORWARD = 0xA7
WH_MIN = -1
WH_MSGFILTER = -1
WH_JOURNALRECORD = 0
WH_JOURNALPLAYBACK = 1
WH_KEYBOARD = 2
WH_GETMESSAGE = 3
WH_CALLWNDPROC = 4
WH_CBT = 5
WH_SYSMSGFILTER = 6
WH_MOUSE = 7
WH_HARDWARE = 8
WH_DEBUG = 9
WH_SHELL = 10
WH_FOREGROUNDIDLE = 11
WH_CALLWNDPROCRET = 12
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WH_MAX = 14
WH_MINHOOK = WH_MIN
WH_MAXHOOK = WH_MAX
HC_ACTION = 0
HC_GETNEXT = 1
HC_SKIP = 2
HC_NOREMOVE = 3
HC_NOREM = HC_NOREMOVE
HC_SYSMODALON = 4
HC_SYSMODALOFF = 5
HCBT_MOVESIZE = 0
HCBT_MINMAX = 1
HCBT_QS = 2
HCBT_CREATEWND = 3
HCBT_DESTROYWND = 4
HCBT_ACTIVATE = 5
HCBT_CLICKSKIPPED = 6
HCBT_KEYSKIPPED = 7
HCBT_SYSCOMMAND = 8
HCBT_SETFOCUS = 9
MSGF_DIALOGBOX = 0
MSGF_MESSAGEBOX = 1
MSGF_MENU = 2
# MSGF_MOVE = 3
# MSGF_SIZE = 4
MSGF_SCROLLBAR = 5
MSGF_NEXTWINDOW = 6
# MSGF_MAINLOOP = 8
MSGF_MAX = 8
MSGF_USER = 4096
HSHELL_WINDOWCREATED = 1
HSHELL_WINDOWDESTROYED = 2
HSHELL_ACTIVATESHELLWINDOW = 3
HSHELL_WINDOWACTIVATED = 4
HSHELL_GETMINRECT = 5
HSHELL_REDRAW = 6
HSHELL_TASKMAN = 7
HSHELL_LANGUAGE = 8
HSHELL_ACCESSIBILITYSTATE = 11
ACCESS_STICKYKEYS = 1
ACCESS_FILTERKEYS = 2
ACCESS_MOUSEKEYS = 3
# winuser.h line 624
LLKHF_EXTENDED = 1
LLKHF_INJECTED = 16
LLKHF_ALTDOWN = 32
LLKHF_UP = 128
LLKHF_LOWER_IL_INJECTED = 2
LLMHF_INJECTED = 1
LLMHF_LOWER_IL_INJECTED = 2
# line 692
HKL_PREV = 0
HKL_NEXT = 1
KLF_ACTIVATE = 1
KLF_SUBSTITUTE_OK = 2
KLF_UNLOADPREVIOUS = 4
KLF_REORDER = 8
KLF_REPLACELANG = 16
KLF_NOTELLSHELL = 128
KLF_SETFORPROCESS = 256
KL_NAMELENGTH = 9
DESKTOP_READOBJECTS = 1
DESKTOP_CREATEWINDOW = 2
DESKTOP_CREATEMENU = 4
DESKTOP_HOOKCONTROL = 8
DESKTOP_JOURNALRECORD = 16
DESKTOP_JOURNALPLAYBACK = 32
DESKTOP_ENUMERATE = 64
DESKTOP_WRITEOBJECTS = 128
DESKTOP_SWITCHDESKTOP = 256
DF_ALLOWOTHERACCOUNTHOOK = 1
WINSTA_ENUMDESKTOPS = 1
WINSTA_READATTRIBUTES = 2
WINSTA_ACCESSCLIPBOARD = 4
WINSTA_CREATEDESKTOP = 8
WINSTA_WRITEATTRIBUTES = 16
WINSTA_ACCESSGLOBALATOMS = 32
WINSTA_EXITWINDOWS = 64
WINSTA_ENUMERATE = 256
WINSTA_READSCREEN = 512
WSF_VISIBLE = 1
UOI_FLAGS = 1
UOI_NAME = 2
UOI_TYPE = 3
UOI_USER_SID = 4
GWL_WNDPROC = -4
GWL_HINSTANCE = -6
GWL_HWNDPARENT = -8
GWL_STYLE = -16
GWL_EXSTYLE = -20
GWL_USERDATA = -21
GWL_ID = -12
GCL_MENUNAME = -8
GCL_HBRBACKGROUND = -10
GCL_HCURSOR = -12
GCL_HICON = -14
GCL_HMODULE = -16
GCL_CBWNDEXTRA = -18
GCL_CBCLSEXTRA = -20
GCL_WNDPROC = -24
GCL_STYLE = -26
GCW_ATOM = -32
GCL_HICONSM = -34
# line 1291
WM_NULL = 0
WM_CREATE = 1
WM_DESTROY = 2
WM_MOVE = 3
WM_SIZE = 5
WM_ACTIVATE = 6
WA_INACTIVE = 0
WA_ACTIVE = 1
WA_CLICKACTIVE = 2
WM_SETFOCUS = 7
WM_KILLFOCUS = 8
WM_ENABLE = 10
WM_SETREDRAW = 11
WM_SETTEXT = 12
WM_GETTEXT = 13
WM_GETTEXTLENGTH = 14
WM_PAINT = 15
WM_CLOSE = 16
WM_QUERYENDSESSION = 17
WM_QUIT = 18
WM_QUERYOPEN = 19
WM_ERASEBKGND = 20
WM_SYSCOLORCHANGE = 21
WM_ENDSESSION = 22
WM_SHOWWINDOW = 24
WM_WININICHANGE = 26
WM_SETTINGCHANGE = WM_WININICHANGE
WM_DEVMODECHANGE = 27
WM_ACTIVATEAPP = 28
WM_FONTCHANGE = 29
WM_TIMECHANGE = 30
WM_CANCELMODE = 31
WM_SETCURSOR = 32
WM_MOUSEACTIVATE = 33
WM_CHILDACTIVATE = 34
WM_QUEUESYNC = 35
WM_GETMINMAXINFO = 36
WM_PAINTICON = 38
WM_ICONERASEBKGND = 39
WM_NEXTDLGCTL = 40
WM_SPOOLERSTATUS = 42
WM_DRAWITEM = 43
WM_MEASUREITEM = 44
WM_DELETEITEM = 45
WM_VKEYTOITEM = 46
WM_CHARTOITEM = 47
WM_SETFONT = 48
WM_GETFONT = 49
WM_SETHOTKEY = 50
WM_GETHOTKEY = 51
WM_QUERYDRAGICON = 55
WM_COMPAREITEM = 57
WM_GETOBJECT = 61
WM_COMPACTING = 65
WM_COMMNOTIFY = 68
WM_WINDOWPOSCHANGING = 70
WM_WINDOWPOSCHANGED = 71
WM_POWER = 72
PWR_OK = 1
PWR_FAIL = -1
PWR_SUSPENDREQUEST = 1
PWR_SUSPENDRESUME = 2
PWR_CRITICALRESUME = 3
WM_COPYDATA = 74
WM_CANCELJOURNAL = 75
WM_INPUTLANGCHANGEREQUEST = 80
WM_INPUTLANGCHANGE = 81
WM_TCARD = 82
WM_HELP = 83
WM_USERCHANGED = 84
WM_NOTIFYFORMAT = 85
NFR_ANSI = 1
NFR_UNICODE = 2
NF_QUERY = 3
NF_REQUERY = 4
WM_STYLECHANGING = 124
WM_STYLECHANGED = 125
WM_DISPLAYCHANGE = 126
WM_GETICON = 127
WM_SETICON = 128
WM_NCCREATE = 129
WM_NCDESTROY = 130
WM_NCCALCSIZE = 131
WM_NCHITTEST = 132
WM_NCPAINT = 133
WM_NCACTIVATE = 134
WM_GETDLGCODE = 135
WM_SYNCPAINT = 136
WM_NCMOUSEMOVE = 160
WM_NCLBUTTONDOWN = 161
WM_NCLBUTTONUP = 162
WM_NCLBUTTONDBLCLK = 163
WM_NCRBUTTONDOWN = 164
WM_NCRBUTTONUP = 165
WM_NCRBUTTONDBLCLK = 166
WM_NCMBUTTONDOWN = 167
WM_NCMBUTTONUP = 168
WM_NCMBUTTONDBLCLK = 169
WM_KEYFIRST = 256
WM_KEYDOWN = 256
WM_KEYUP = 257
WM_CHAR = 258
WM_DEADCHAR = 259
WM_SYSKEYDOWN = 260
WM_SYSKEYUP = 261
WM_SYSCHAR = 262
WM_SYSDEADCHAR = 263
WM_KEYLAST = 264
WM_IME_STARTCOMPOSITION = 269
WM_IME_ENDCOMPOSITION = 270
WM_IME_COMPOSITION = 271
WM_IME_KEYLAST = 271
WM_INITDIALOG = 272
WM_COMMAND = 273
WM_SYSCOMMAND = 274
WM_TIMER = 275
WM_HSCROLL = 276
WM_VSCROLL = 277
WM_INITMENU = 278
WM_INITMENUPOPUP = 279
WM_MENUSELECT = 287
WM_MENUCHAR = 288
WM_ENTERIDLE = 289
WM_MENURBUTTONUP = 290
WM_MENUDRAG = 291
WM_MENUGETOBJECT = 292
WM_UNINITMENUPOPUP = 293
WM_MENUCOMMAND = 294
WM_CTLCOLORMSGBOX = 306
WM_CTLCOLOREDIT = 307
WM_CTLCOLORLISTBOX = 308
WM_CTLCOLORBTN = 309
WM_CTLCOLORDLG = 310
WM_CTLCOLORSCROLLBAR = 311
WM_CTLCOLORSTATIC = 312
WM_MOUSEFIRST = 512
WM_MOUSEMOVE = 512
WM_LBUTTONDOWN = 513
WM_LBUTTONUP = 514
WM_LBUTTONDBLCLK = 515
WM_RBUTTONDOWN = 516
WM_RBUTTONUP = 517
WM_RBUTTONDBLCLK = 518
WM_MBUTTONDOWN = 519
WM_MBUTTONUP = 520
WM_MBUTTONDBLCLK = 521
WM_MOUSEWHEEL = 522
WM_MOUSELAST = 522
WHEEL_DELTA = 120  # Value for rolling one detent
WHEEL_PAGESCROLL = -1  # Scroll one page
WM_PARENTNOTIFY = 528
MENULOOP_WINDOW = 0
MENULOOP_POPUP = 1
WM_ENTERMENULOOP = 529
WM_EXITMENULOOP = 530
WM_NEXTMENU = 531
WM_SIZING = 532
WM_CAPTURECHANGED = 533
WM_MOVING = 534
WM_POWERBROADCAST = 536
PBT_APMQUERYSUSPEND = 0
PBT_APMQUERYSTANDBY = 1
PBT_APMQUERYSUSPENDFAILED = 2
PBT_APMQUERYSTANDBYFAILED = 3
PBT_APMSUSPEND = 4
PBT_APMSTANDBY = 5
PBT_APMRESUMECRITICAL = 6
PBT_APMRESUMESUSPEND = 7
PBT_APMRESUMESTANDBY = 8
PBTF_APMRESUMEFROMFAILURE = 1
PBT_APMBATTERYLOW = 9
PBT_APMPOWERSTATUSCHANGE = 10
PBT_APMOEMEVENT = 11
PBT_APMRESUMEAUTOMATIC = 18
WM_MDICREATE = 544
WM_MDIDESTROY = 545
WM_MDIACTIVATE = 546
WM_MDIRESTORE = 547
WM_MDINEXT = 548
WM_MDIMAXIMIZE = 549
WM_MDITILE = 550
WM_MDICASCADE = 551
WM_MDIICONARRANGE = 552
WM_MDIGETACTIVE = 553
WM_MDISETMENU = 560
WM_ENTERSIZEMOVE = 561
WM_EXITSIZEMOVE = 562
WM_DROPFILES = 563
WM_MDIREFRESHMENU = 564
WM_IME_SETCONTEXT = 641
WM_IME_NOTIFY = 642
WM_IME_CONTROL = 643
WM_IME_COMPOSITIONFULL = 644
WM_IME_SELECT = 645
WM_IME_CHAR = 646
WM_IME_REQUEST = 648
WM_IME_KEYDOWN = 656
WM_IME_KEYUP = 657
WM_MOUSEHOVER = 673
WM_MOUSELEAVE = 675
WM_CUT = 768
WM_COPY = 769
WM_PASTE = 770
WM_CLEAR = 771
WM_UNDO = 772
WM_RENDERFORMAT = 773
WM_RENDERALLFORMATS = 774
WM_DESTROYCLIPBOARD = 775
WM_DRAWCLIPBOARD = 776
WM_PAINTCLIPBOARD = 777
WM_VSCROLLCLIPBOARD = 778
WM_SIZECLIPBOARD = 779
WM_ASKCBFORMATNAME = 780
WM_CHANGECBCHAIN = 781
WM_HSCROLLCLIPBOARD = 782
WM_QUERYNEWPALETTE = 783
WM_PALETTEISCHANGING = 784
WM_PALETTECHANGED = 785
WM_HOTKEY = 786
WM_PRINT = 791
WM_HANDHELDFIRST = 856
WM_HANDHELDLAST = 863
WM_AFXFIRST = 864
WM_AFXLAST = 895
WM_PENWINFIRST = 896
WM_PENWINLAST = 911
WM_APP = 32768
WMSZ_LEFT = 1
WMSZ_RIGHT = 2
WMSZ_TOP = 3
WMSZ_TOPLEFT = 4
WMSZ_TOPRIGHT = 5
WMSZ_BOTTOM = 6
WMSZ_BOTTOMLEFT = 7
WMSZ_BOTTOMRIGHT = 8
# ST_BEGINSWP = 0
# ST_ENDSWP = 1
HTERROR = -2
HTTRANSPARENT = -1
HTNOWHERE = 0
HTCLIENT = 1
HTCAPTION = 2
HTSYSMENU = 3
HTGROWBOX = 4
HTSIZE = HTGROWBOX
HTMENU = 5
HTHSCROLL = 6
HTVSCROLL = 7
HTMINBUTTON = 8
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
HTBORDER = 18
HTREDUCE = HTMINBUTTON
HTZOOM = HTMAXBUTTON
HTSIZEFIRST = HTLEFT
HTSIZELAST = HTBOTTOMRIGHT
HTOBJECT = 19
HTCLOSE = 20
HTHELP = 21
SMTO_NORMAL = 0
SMTO_BLOCK = 1
SMTO_ABORTIFHUNG = 2
SMTO_NOTIMEOUTIFNOTHUNG = 8
MA_ACTIVATE = 1
MA_ACTIVATEANDEAT = 2
MA_NOACTIVATE = 3
MA_NOACTIVATEANDEAT = 4
ICON_SMALL = 0
ICON_BIG = 1
SIZE_RESTORED = 0
SIZE_MINIMIZED = 1
SIZE_MAXIMIZED = 2
SIZE_MAXSHOW = 3
SIZE_MAXHIDE = 4
SIZENORMAL = SIZE_RESTORED
SIZEICONIC = SIZE_MINIMIZED
SIZEFULLSCREEN = SIZE_MAXIMIZED
SIZEZOOMSHOW = SIZE_MAXSHOW
SIZEZOOMHIDE = SIZE_MAXHIDE
WVR_ALIGNTOP = 16
WVR_ALIGNLEFT = 32
WVR_ALIGNBOTTOM = 64
WVR_ALIGNRIGHT = 128
WVR_HREDRAW = 256
WVR_VREDRAW = 512
WVR_REDRAW = WVR_HREDRAW | WVR_VREDRAW
WVR_VALIDRECTS = 1024
MK_LBUTTON = 1
MK_RBUTTON = 2
MK_SHIFT = 4
MK_CONTROL = 8
MK_MBUTTON = 16
TME_HOVER = 1
TME_LEAVE = 2
TME_QUERY = 1073741824
TME_CANCEL = -2147483648
HOVER_DEFAULT = -1
WS_OVERLAPPED = 0
WS_POPUP = -2147483648
WS_CHILD = 1073741824
WS_MINIMIZE = 536870912
WS_VISIBLE = 268435456
WS_DISABLED = 134217728
WS_CLIPSIBLINGS = 67108864
WS_CLIPCHILDREN = 33554432
WS_MAXIMIZE = 16777216
WS_CAPTION = 12582912
WS_BORDER = 8388608
WS_DLGFRAME = 4194304
WS_VSCROLL = 2097152
WS_HSCROLL = 1048576
WS_SYSMENU = 524288
WS_THICKFRAME = 262144
WS_GROUP = 131072
WS_TABSTOP = 65536
WS_MINIMIZEBOX = 131072
WS_MAXIMIZEBOX = 65536
WS_TILED = WS_OVERLAPPED
WS_ICONIC = WS_MINIMIZE
WS_SIZEBOX = WS_THICKFRAME
WS_OVERLAPPEDWINDOW = (
    WS_OVERLAPPED
    | WS_CAPTION
    | WS_SYSMENU
    | WS_THICKFRAME
    | WS_MINIMIZEBOX
    | WS_MAXIMIZEBOX
)
WS_POPUPWINDOW = WS_POPUP | WS_BORDER | WS_SYSMENU
WS_CHILDWINDOW = WS_CHILD
WS_TILEDWINDOW = WS_OVERLAPPEDWINDOW
WS_EX_DLGMODALFRAME = 1
WS_EX_NOPARENTNOTIFY = 4
WS_EX_TOPMOST = 8
WS_EX_ACCEPTFILES = 16
WS_EX_TRANSPARENT = 32
WS_EX_MDICHILD = 64
WS_EX_TOOLWINDOW = 128
WS_EX_WINDOWEDGE = 256
WS_EX_CLIENTEDGE = 512
WS_EX_CONTEXTHELP = 1024
WS_EX_RIGHT = 4096
WS_EX_LEFT = 0
WS_EX_RTLREADING = 8192
WS_EX_LTRREADING = 0
WS_EX_LEFTSCROLLBAR = 16384
WS_EX_RIGHTSCROLLBAR = 0
WS_EX_CONTROLPARENT = 65536
WS_EX_STATICEDGE = 131072
WS_EX_APPWINDOW = 262144
WS_EX_OVERLAPPEDWINDOW = WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE
WS_EX_PALETTEWINDOW = WS_EX_WINDOWEDGE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
WS_EX_LAYERED = 0x00080000
WS_EX_NOINHERITLAYOUT = 0x00100000
WS_EX_LAYOUTRTL = 0x00400000
WS_EX_COMPOSITED = 0x02000000
WS_EX_NOACTIVATE = 0x08000000

CS_VREDRAW = 1
CS_HREDRAW = 2
# CS_KEYCVTWINDOW = 0x0004
CS_DBLCLKS = 8
CS_OWNDC = 32
CS_CLASSDC = 64
CS_PARENTDC = 128
# CS_NOKEYCVT = 0x0100
CS_NOCLOSE = 512
CS_SAVEBITS = 2048
CS_BYTEALIGNCLIENT = 4096
CS_BYTEALIGNWINDOW = 8192
CS_GLOBALCLASS = 16384
CS_IME = 65536
PRF_CHECKVISIBLE = 1
PRF_NONCLIENT = 2
PRF_CLIENT = 4
PRF_ERASEBKGND = 8
PRF_CHILDREN = 16
PRF_OWNED = 32
BDR_RAISEDOUTER = 1
BDR_SUNKENOUTER = 2
BDR_RAISEDINNER = 4
BDR_SUNKENINNER = 8
BDR_OUTER = 3
BDR_INNER = 12
# BDR_RAISED = 0x0005
# BDR_SUNKEN = 0x000a
EDGE_RAISED = BDR_RAISEDOUTER | BDR_RAISEDINNER
EDGE_SUNKEN = BDR_SUNKENOUTER | BDR_SUNKENINNER
EDGE_ETCHED = BDR_SUNKENOUTER | BDR_RAISEDINNER
EDGE_BUMP = BDR_RAISEDOUTER | BDR_SUNKENINNER

# winuser.h line 2879
ISMEX_NOSEND = 0
ISMEX_SEND = 1
ISMEX_NOTIFY = 2
ISMEX_CALLBACK = 4
ISMEX_REPLIED = 8
CW_USEDEFAULT = -2147483648
FLASHW_STOP = 0
FLASHW_CAPTION = 1
FLASHW_TRAY = 2
FLASHW_ALL = FLASHW_CAPTION | FLASHW_TRAY
FLASHW_TIMER = 4
FLASHW_TIMERNOFG = 12

# winuser.h line 7963
DS_ABSALIGN = 1
DS_SYSMODAL = 2
DS_LOCALEDIT = 32
DS_SETFONT = 64
DS_MODALFRAME = 128
DS_NOIDLEMSG = 256
DS_SETFOREGROUND = 512
DS_3DLOOK = 4
DS_FIXEDSYS = 8
DS_NOFAILCREATE = 16
DS_CONTROL = 1024
DS_CENTER = 2048
DS_CENTERMOUSE = 4096
DS_CONTEXTHELP = 8192
DM_GETDEFID = WM_USER + 0
DM_SETDEFID = WM_USER + 1
DM_REPOSITION = WM_USER + 2
# PSM_PAGEINFO = (WM_USER+100)
# PSM_SHEETINFO = (WM_USER+101)
# PSI_SETACTIVE = 0x0001
# PSI_KILLACTIVE = 0x0002
# PSI_APPLY = 0x0003
# PSI_RESET = 0x0004
# PSI_HASHELP = 0x0005
# PSI_HELP = 0x0006
# PSI_CHANGED = 0x0001
# PSI_GUISTART = 0x0002
# PSI_REBOOT = 0x0003
# PSI_GETSIBLINGS = 0x0004
DC_HASDEFID = 21323
DLGC_WANTARROWS = 1
DLGC_WANTTAB = 2
DLGC_WANTALLKEYS = 4
DLGC_WANTMESSAGE = 4
DLGC_HASSETSEL = 8
DLGC_DEFPUSHBUTTON = 16
DLGC_UNDEFPUSHBUTTON = 32
DLGC_RADIOBUTTON = 64
DLGC_WANTCHARS = 128
DLGC_STATIC = 256
DLGC_BUTTON = 8192
LB_CTLCODE = 0
LB_OKAY = 0
LB_ERR = -1
LB_ERRSPACE = -2
LBN_ERRSPACE = -2
LBN_SELCHANGE = 1
LBN_DBLCLK = 2
LBN_SELCANCEL = 3
LBN_SETFOCUS = 4
LBN_KILLFOCUS = 5
LB_ADDSTRING = 384
LB_INSERTSTRING = 385
LB_DELETESTRING = 386
LB_SELITEMRANGEEX = 387
LB_RESETCONTENT = 388
LB_SETSEL = 389
LB_SETCURSEL = 390
LB_GETSEL = 391
LB_GETCURSEL = 392
LB_GETTEXT = 393
LB_GETTEXTLEN = 394
LB_GETCOUNT = 395
LB_SELECTSTRING = 396
LB_DIR = 397
LB_GETTOPINDEX = 398
LB_FINDSTRING = 399
LB_GETSELCOUNT = 400
LB_GETSELITEMS = 401
LB_SETTABSTOPS = 402
LB_GETHORIZONTALEXTENT = 403
LB_SETHORIZONTALEXTENT = 404
LB_SETCOLUMNWIDTH = 405
LB_ADDFILE = 406
LB_SETTOPINDEX = 407
LB_GETITEMRECT = 408
LB_GETITEMDATA = 409
LB_SETITEMDATA = 410
LB_SELITEMRANGE = 411
LB_SETANCHORINDEX = 412
LB_GETANCHORINDEX = 413
LB_SETCARETINDEX = 414
LB_GETCARETINDEX = 415
LB_SETITEMHEIGHT = 416
LB_GETITEMHEIGHT = 417
LB_FINDSTRINGEXACT = 418
LB_SETLOCALE = 421
LB_GETLOCALE = 422
LB_SETCOUNT = 423
LB_INITSTORAGE = 424
LB_ITEMFROMPOINT = 425
LB_MSGMAX = 432
LBS_NOTIFY = 1
LBS_SORT = 2
LBS_NOREDRAW = 4
LBS_MULTIPLESEL = 8
LBS_OWNERDRAWFIXED = 16
LBS_OWNERDRAWVARIABLE = 32
LBS_HASSTRINGS = 64
LBS_USETABSTOPS = 128
LBS_NOINTEGRALHEIGHT = 256
LBS_MULTICOLUMN = 512
LBS_WANTKEYBOARDINPUT = 1024
LBS_EXTENDEDSEL = 2048
LBS_DISABLENOSCROLL = 4096
LBS_NODATA = 8192
LBS_NOSEL = 16384
LBS_STANDARD = LBS_NOTIFY | LBS_SORT | WS_VSCROLL | WS_BORDER
CB_OKAY = 0
CB_ERR = -1
CB_ERRSPACE = -2
CBN_ERRSPACE = -1
CBN_SELCHANGE = 1
CBN_DBLCLK = 2
CBN_SETFOCUS = 3
CBN_KILLFOCUS = 4
CBN_EDITCHANGE = 5
CBN_EDITUPDATE = 6
CBN_DROPDOWN = 7
CBN_CLOSEUP = 8
CBN_SELENDOK = 9
CBN_SELENDCANCEL = 10
CBS_SIMPLE = 1
CBS_DROPDOWN = 2
CBS_DROPDOWNLIST = 3
CBS_OWNERDRAWFIXED = 16
CBS_OWNERDRAWVARIABLE = 32
CBS_AUTOHSCROLL = 64
CBS_OEMCONVERT = 128
CBS_SORT = 256
CBS_HASSTRINGS = 512
CBS_NOINTEGRALHEIGHT = 1024
CBS_DISABLENOSCROLL = 2048
CBS_UPPERCASE = 8192
CBS_LOWERCASE = 16384
CB_GETEDITSEL = 320
CB_LIMITTEXT = 321
CB_SETEDITSEL = 322
CB_ADDSTRING = 323
CB_DELETESTRING = 324
CB_DIR = 325
CB_GETCOUNT = 326
CB_GETCURSEL = 327
CB_GETLBTEXT = 328
CB_GETLBTEXTLEN = 329
CB_INSERTSTRING = 330
CB_RESETCONTENT = 331
CB_FINDSTRING = 332
CB_SELECTSTRING = 333
CB_SETCURSEL = 334
CB_SHOWDROPDOWN = 335
CB_GETITEMDATA = 336
CB_SETITEMDATA = 337
CB_GETDROPPEDCONTROLRECT = 338
CB_SETITEMHEIGHT = 339
CB_GETITEMHEIGHT = 340
CB_SETEXTENDEDUI = 341
CB_GETEXTENDEDUI = 342
CB_GETDROPPEDSTATE = 343
CB_FINDSTRINGEXACT = 344
CB_SETLOCALE = 345
CB_GETLOCALE = 346
CB_GETTOPINDEX = 347
CB_SETTOPINDEX = 348
CB_GETHORIZONTALEXTENT = 349
CB_SETHORIZONTALEXTENT = 350
CB_GETDROPPEDWIDTH = 351
CB_SETDROPPEDWIDTH = 352
CB_INITSTORAGE = 353
CB_MSGMAX = 354
SBS_HORZ = 0
SBS_VERT = 1
SBS_TOPALIGN = 2
SBS_LEFTALIGN = 2
SBS_BOTTOMALIGN = 4
SBS_RIGHTALIGN = 4
SBS_SIZEBOXTOPLEFTALIGN = 2
SBS_SIZEBOXBOTTOMRIGHTALIGN = 4
SBS_SIZEBOX = 8
SBS_SIZEGRIP = 16
SBM_SETPOS = 224
SBM_GETPOS = 225
SBM_SETRANGE = 226
SBM_SETRANGEREDRAW = 230
SBM_GETRANGE = 227
SBM_ENABLE_ARROWS = 228
SBM_SETSCROLLINFO = 233
SBM_GETSCROLLINFO = 234
SIF_RANGE = 1
SIF_PAGE = 2
SIF_POS = 4
SIF_DISABLENOSCROLL = 8
SIF_TRACKPOS = 16
SIF_ALL = SIF_RANGE | SIF_PAGE | SIF_POS | SIF_TRACKPOS
MDIS_ALLCHILDSTYLES = 1
MDITILE_VERTICAL = 0
MDITILE_HORIZONTAL = 1
MDITILE_SKIPDISABLED = 2
MDITILE_ZORDER = 4

IMC_GETCANDIDATEPOS = 7
IMC_SETCANDIDATEPOS = 8
IMC_GETCOMPOSITIONFONT = 9
IMC_SETCOMPOSITIONFONT = 10
IMC_GETCOMPOSITIONWINDOW = 11
IMC_SETCOMPOSITIONWINDOW = 12
IMC_GETSTATUSWINDOWPOS = 15
IMC_SETSTATUSWINDOWPOS = 16
IMC_CLOSESTATUSWINDOW = 33
IMC_OPENSTATUSWINDOW = 34
# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
DELETE = 65536
READ_CONTROL = 131072
WRITE_DAC = 262144
WRITE_OWNER = 524288
SYNCHRONIZE = 1048576
STANDARD_RIGHTS_REQUIRED = 983040
STANDARD_RIGHTS_READ = READ_CONTROL
STANDARD_RIGHTS_WRITE = READ_CONTROL
STANDARD_RIGHTS_EXECUTE = READ_CONTROL
STANDARD_RIGHTS_ALL = 2031616
SPECIFIC_RIGHTS_ALL = 65535
ACCESS_SYSTEM_SECURITY = 16777216
MAXIMUM_ALLOWED = 33554432
GENERIC_READ = -2147483648
GENERIC_WRITE = 1073741824
GENERIC_EXECUTE = 536870912
GENERIC_ALL = 268435456

SERVICE_KERNEL_DRIVER = 1
SERVICE_FILE_SYSTEM_DRIVER = 2
SERVICE_ADAPTER = 4
SERVICE_RECOGNIZER_DRIVER = 8
SERVICE_DRIVER = (
    SERVICE_KERNEL_DRIVER | SERVICE_FILE_SYSTEM_DRIVER | SERVICE_RECOGNIZER_DRIVER
)
SERVICE_WIN32_OWN_PROCESS = 16
SERVICE_WIN32_SHARE_PROCESS = 32
SERVICE_WIN32 = SERVICE_WIN32_OWN_PROCESS | SERVICE_WIN32_SHARE_PROCESS
SERVICE_INTERACTIVE_PROCESS = 256
SERVICE_TYPE_ALL = (
    SERVICE_WIN32 | SERVICE_ADAPTER | SERVICE_DRIVER | SERVICE_INTERACTIVE_PROCESS
)
SERVICE_BOOT_START = 0
SERVICE_SYSTEM_START = 1
SERVICE_AUTO_START = 2
SERVICE_DEMAND_START = 3
SERVICE_DISABLED = 4
SERVICE_ERROR_IGNORE = 0
SERVICE_ERROR_NORMAL = 1
SERVICE_ERROR_SEVERE = 2
SERVICE_ERROR_CRITICAL = 3
TAPE_ERASE_SHORT = 0
TAPE_ERASE_LONG = 1
TAPE_LOAD = 0
TAPE_UNLOAD = 1
TAPE_TENSION = 2
TAPE_LOCK = 3
TAPE_UNLOCK = 4
TAPE_FORMAT = 5
TAPE_SETMARKS = 0
TAPE_FILEMARKS = 1
TAPE_SHORT_FILEMARKS = 2
TAPE_LONG_FILEMARKS = 3
TAPE_ABSOLUTE_POSITION = 0
TAPE_LOGICAL_POSITION = 1
TAPE_PSEUDO_LOGICAL_POSITION = 2
TAPE_REWIND = 0
TAPE_ABSOLUTE_BLOCK = 1
TAPE_LOGICAL_BLOCK = 2
TAPE_PSEUDO_LOGICAL_BLOCK = 3
TAPE_SPACE_END_OF_DATA = 4
TAPE_SPACE_RELATIVE_BLOCKS = 5
TAPE_SPACE_FILEMARKS = 6
TAPE_SPACE_SEQUENTIAL_FMKS = 7
TAPE_SPACE_SETMARKS = 8
TAPE_SPACE_SEQUENTIAL_SMKS = 9
TAPE_DRIVE_FIXED = 1
TAPE_DRIVE_SELECT = 2
TAPE_DRIVE_INITIATOR = 4
TAPE_DRIVE_ERASE_SHORT = 16
TAPE_DRIVE_ERASE_LONG = 32
TAPE_DRIVE_ERASE_BOP_ONLY = 64
TAPE_DRIVE_ERASE_IMMEDIATE = 128
TAPE_DRIVE_TAPE_CAPACITY = 256
TAPE_DRIVE_TAPE_REMAINING = 512
TAPE_DRIVE_FIXED_BLOCK = 1024
TAPE_DRIVE_VARIABLE_BLOCK = 2048
TAPE_DRIVE_WRITE_PROTECT = 4096
TAPE_DRIVE_EOT_WZ_SIZE = 8192
TAPE_DRIVE_ECC = 65536
TAPE_DRIVE_COMPRESSION = 131072
TAPE_DRIVE_PADDING = 262144
TAPE_DRIVE_REPORT_SMKS = 524288
TAPE_DRIVE_GET_ABSOLUTE_BLK = 1048576
TAPE_DRIVE_GET_LOGICAL_BLK = 2097152
TAPE_DRIVE_SET_EOT_WZ_SIZE = 4194304
TAPE_DRIVE_LOAD_UNLOAD = -2147483647
TAPE_DRIVE_TENSION = -2147483646
TAPE_DRIVE_LOCK_UNLOCK = -2147483644
TAPE_DRIVE_REWIND_IMMEDIATE = -2147483640
TAPE_DRIVE_SET_BLOCK_SIZE = -2147483632
TAPE_DRIVE_LOAD_UNLD_IMMED = -2147483616
TAPE_DRIVE_TENSION_IMMED = -2147483584
TAPE_DRIVE_LOCK_UNLK_IMMED = -2147483520
TAPE_DRIVE_SET_ECC = -2147483392
TAPE_DRIVE_SET_COMPRESSION = -2147483136
TAPE_DRIVE_SET_PADDING = -2147482624
TAPE_DRIVE_SET_REPORT_SMKS = -2147481600
TAPE_DRIVE_ABSOLUTE_BLK = -2147479552
TAPE_DRIVE_ABS_BLK_IMMED = -2147475456
TAPE_DRIVE_LOGICAL_BLK = -2147467264
TAPE_DRIVE_LOG_BLK_IMMED = -2147450880
TAPE_DRIVE_END_OF_DATA = -2147418112
TAPE_DRIVE_RELATIVE_BLKS = -2147352576
TAPE_DRIVE_FILEMARKS = -2147221504
TAPE_DRIVE_SEQUENTIAL_FMKS = -2146959360
TAPE_DRIVE_SETMARKS = -2146435072
TAPE_DRIVE_SEQUENTIAL_SMKS = -2145386496
TAPE_DRIVE_REVERSE_POSITION = -2143289344
TAPE_DRIVE_SPACE_IMMEDIATE = -2139095040
TAPE_DRIVE_WRITE_SETMARKS = -2130706432
TAPE_DRIVE_WRITE_FILEMARKS = -2113929216
TAPE_DRIVE_WRITE_SHORT_FMKS = -2080374784
TAPE_DRIVE_WRITE_LONG_FMKS = -2013265920
TAPE_DRIVE_WRITE_MARK_IMMED = -1879048192
TAPE_DRIVE_FORMAT = -1610612736
TAPE_DRIVE_FORMAT_IMMEDIATE = -1073741824
TAPE_FIXED_PARTITIONS = 0
TAPE_SELECT_PARTITIONS = 1
TAPE_INITIATOR_PARTITIONS = 2
# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.

APPLICATION_ERROR_MASK = 536870912
ERROR_SEVERITY_SUCCESS = 0
ERROR_SEVERITY_INFORMATIONAL = 1073741824
ERROR_SEVERITY_WARNING = -2147483648
ERROR_SEVERITY_ERROR = -1073741824
MINCHAR = 128
MAXCHAR = 127
MINSHORT = 32768
MAXSHORT = 32767
MINLONG = -2147483648
MAXLONG = 2147483647
MAXBYTE = 255
MAXWORD = 65535
MAXDWORD = -1
LANG_NEUTRAL = 0
LANG_BULGARIAN = 2
LANG_CHINESE = 4
LANG_CROATIAN = 26
LANG_CZECH = 5
LANG_DANISH = 6
LANG_DUTCH = 19
LANG_ENGLISH = 9
LANG_FINNISH = 11
LANG_FRENCH = 12
LANG_GERMAN = 7
LANG_GREEK = 8
LANG_HUNGARIAN = 14
LANG_ICELANDIC = 15
LANG_ITALIAN = 16
LANG_JAPANESE = 17
LANG_KOREAN = 18
LANG_NORWEGIAN = 20
LANG_POLISH = 21
LANG_PORTUGUESE = 22
LANG_ROMANIAN = 24
LANG_RUSSIAN = 25
LANG_SLOVAK = 27
LANG_SLOVENIAN = 36
LANG_SPANISH = 10
LANG_SWEDISH = 29
LANG_TURKISH = 31
SUBLANG_NEUTRAL = 0
SUBLANG_DEFAULT = 1
SUBLANG_SYS_DEFAULT = 2
SUBLANG_CHINESE_TRADITIONAL = 1
SUBLANG_CHINESE_SIMPLIFIED = 2
SUBLANG_CHINESE_HONGKONG = 3
SUBLANG_CHINESE_SINGAPORE = 4
SUBLANG_DUTCH = 1
SUBLANG_DUTCH_BELGIAN = 2
SUBLANG_ENGLISH_US = 1
SUBLANG_ENGLISH_UK = 2
SUBLANG_ENGLISH_AUS = 3
SUBLANG_ENGLISH_CAN = 4
SUBLANG_ENGLISH_NZ = 5
SUBLANG_ENGLISH_EIRE = 6
SUBLANG_FRENCH = 1
SUBLANG_FRENCH_BELGIAN = 2
SUBLANG_FRENCH_CANADIAN = 3
SUBLANG_FRENCH_SWISS = 4
SUBLANG_GERMAN = 1
SUBLANG_GERMAN_SWISS = 2
SUBLANG_GERMAN_AUSTRIAN = 3
SUBLANG_ITALIAN = 1
SUBLANG_ITALIAN_SWISS = 2
SUBLANG_NORWEGIAN_BOKMAL = 1
SUBLANG_NORWEGIAN_NYNORSK = 2
SUBLANG_PORTUGUESE = 2
SUBLANG_PORTUGUESE_BRAZILIAN = 1
SUBLANG_SPANISH = 1
SUBLANG_SPANISH_MEXICAN = 2
SUBLANG_SPANISH_MODERN = 3
SORT_DEFAULT = 0
SORT_JAPANESE_XJIS = 0
SORT_JAPANESE_UNICODE = 1
SORT_CHINESE_BIG5 = 0
SORT_CHINESE_UNICODE = 1
SORT_KOREAN_KSC = 0
SORT_KOREAN_UNICODE = 1


def PRIMARYLANGID(lgid):
    return (lgid) & 1023


def SUBLANGID(lgid):
    return (lgid) >> 10


NLS_VALID_LOCALE_MASK = 1048575
CONTEXT_PORTABLE_32BIT = 1048576
CONTEXT_ALPHA = 131072
SIZE_OF_80387_REGISTERS = 80
CONTEXT_CONTROL = 1
CONTEXT_FLOATING_POINT = 2
CONTEXT_INTEGER = 4
CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_FLOATING_POINT | CONTEXT_INTEGER
PROCESS_TERMINATE = 1
PROCESS_CREATE_THREAD = 2
PROCESS_VM_OPERATION = 8
PROCESS_VM_READ = 16
PROCESS_VM_WRITE = 32
PROCESS_DUP_HANDLE = 64
PROCESS_CREATE_PROCESS = 128
PROCESS_SET_QUOTA = 256
PROCESS_SET_INFORMATION = 512
PROCESS_QUERY_INFORMATION = 1024
PROCESS_SUSPEND_RESUME = 2048
PROCESS_QUERY_LIMITED_INFORMATION = 4096
PROCESS_SET_LIMITED_INFORMATION = 8192
PROCESS_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 4095
THREAD_TERMINATE = 1
THREAD_SUSPEND_RESUME = 2
THREAD_GET_CONTEXT = 8
THREAD_SET_CONTEXT = 16
THREAD_SET_INFORMATION = 32
THREAD_QUERY_INFORMATION = 64
THREAD_SET_THREAD_TOKEN = 128
THREAD_IMPERSONATE = 256
THREAD_DIRECT_IMPERSONATION = 512
THREAD_SET_LIMITED_INFORMATION = 1024
THREAD_QUERY_LIMITED_INFORMATION = 2048
THREAD_RESUME = 4096
TLS_MINIMUM_AVAILABLE = 64
EVENT_MODIFY_STATE = 2
MUTANT_QUERY_STATE = 1
SEMAPHORE_MODIFY_STATE = 2
TIME_ZONE_ID_UNKNOWN = 0
TIME_ZONE_ID_STANDARD = 1
TIME_ZONE_ID_DAYLIGHT = 2
PROCESSOR_INTEL_386 = 386
PROCESSOR_INTEL_486 = 486
PROCESSOR_INTEL_PENTIUM = 586
PROCESSOR_INTEL_860 = 860
PROCESSOR_MIPS_R2000 = 2000
PROCESSOR_MIPS_R3000 = 3000
PROCESSOR_MIPS_R4000 = 4000
PROCESSOR_ALPHA_21064 = 21064
PROCESSOR_PPC_601 = 601
PROCESSOR_PPC_603 = 603
PROCESSOR_PPC_604 = 604
PROCESSOR_PPC_620 = 620
SECTION_QUERY = 1
SECTION_MAP_WRITE = 2
SECTION_MAP_READ = 4
SECTION_MAP_EXECUTE = 8
SECTION_EXTEND_SIZE = 16
PAGE_NOACCESS = 1
PAGE_READONLY = 2
PAGE_READWRITE = 4
PAGE_WRITECOPY = 8
PAGE_EXECUTE = 16
PAGE_EXECUTE_READ = 32
PAGE_EXECUTE_READWRITE = 64
PAGE_EXECUTE_WRITECOPY = 128
PAGE_GUARD = 256
PAGE_NOCACHE = 512
MEM_COMMIT = 4096
MEM_RESERVE = 8192
MEM_DECOMMIT = 16384
MEM_RELEASE = 32768
MEM_FREE = 65536
MEM_PRIVATE = 131072
MEM_MAPPED = 262144
MEM_TOP_DOWN = 1048576

# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
SEC_FILE = 8388608
SEC_IMAGE = 16777216
SEC_RESERVE = 67108864
SEC_COMMIT = 134217728
SEC_NOCACHE = 268435456
MEM_IMAGE = SEC_IMAGE
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
FILE_ATTRIBUTE_READONLY = 1
FILE_ATTRIBUTE_HIDDEN = 2
FILE_ATTRIBUTE_SYSTEM = 4
FILE_ATTRIBUTE_DIRECTORY = 16
FILE_ATTRIBUTE_ARCHIVE = 32
FILE_ATTRIBUTE_DEVICE = 64
FILE_ATTRIBUTE_NORMAL = 128
FILE_ATTRIBUTE_TEMPORARY = 256
FILE_ATTRIBUTE_SPARSE_FILE = 512
FILE_ATTRIBUTE_REPARSE_POINT = 1024
FILE_ATTRIBUTE_COMPRESSED = 2048
FILE_ATTRIBUTE_OFFLINE = 4096
FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 8192
FILE_ATTRIBUTE_ENCRYPTED = 16384
FILE_ATTRIBUTE_VIRTUAL = 65536
# These FILE_ATTRIBUTE_* flags  are apparently old definitions from Windows 95
# and conflict with current values above - but they live on for b/w compat...
FILE_ATTRIBUTE_ATOMIC_WRITE = 512
FILE_ATTRIBUTE_XACTION_WRITE = 1024

FILE_NOTIFY_CHANGE_FILE_NAME = 1
FILE_NOTIFY_CHANGE_DIR_NAME = 2
FILE_NOTIFY_CHANGE_ATTRIBUTES = 4
FILE_NOTIFY_CHANGE_SIZE = 8
FILE_NOTIFY_CHANGE_LAST_WRITE = 16
FILE_NOTIFY_CHANGE_SECURITY = 256
FILE_CASE_SENSITIVE_SEARCH = 1
FILE_CASE_PRESERVED_NAMES = 2
FILE_FILE_COMPRESSION = 16
FILE_NAMED_STREAMS = 262144
FILE_PERSISTENT_ACLS = 0x00000008
FILE_READ_ONLY_VOLUME = 0x00080000
FILE_SEQUENTIAL_WRITE_ONCE = 0x00100000
FILE_SUPPORTS_ENCRYPTION = 0x00020000
FILE_SUPPORTS_EXTENDED_ATTRIBUTES = 0x00800000
FILE_SUPPORTS_HARD_LINKS = 0x00400000
FILE_SUPPORTS_OBJECT_IDS = 0x00010000
FILE_SUPPORTS_OPEN_BY_FILE_ID = 0x01000000
FILE_SUPPORTS_REPARSE_POINTS = 0x00000080
FILE_SUPPORTS_SPARSE_FILES = 0x00000040
FILE_SUPPORTS_TRANSACTIONS = 0x00200000
FILE_SUPPORTS_USN_JOURNAL = 0x02000000
FILE_UNICODE_ON_DISK = 0x00000004
FILE_VOLUME_QUOTAS = 0x00000020
FILE_VOLUME_IS_COMPRESSED = 32768
IO_COMPLETION_MODIFY_STATE = 2
DUPLICATE_CLOSE_SOURCE = 1
DUPLICATE_SAME_ACCESS = 2
SID_MAX_SUB_AUTHORITIES = 15
SECURITY_NULL_RID = 0
SECURITY_WORLD_RID = 0
SECURITY_LOCAL_RID = 0x00000000
SECURITY_CREATOR_OWNER_RID = 0
SECURITY_CREATOR_GROUP_RID = 1
SECURITY_DIALUP_RID = 1
SECURITY_NETWORK_RID = 2
SECURITY_BATCH_RID = 3
SECURITY_INTERACTIVE_RID = 4
SECURITY_SERVICE_RID = 6
SECURITY_ANONYMOUS_LOGON_RID = 7
SECURITY_LOGON_IDS_RID = 5
SECURITY_LOGON_IDS_RID_COUNT = 3
SECURITY_LOCAL_SYSTEM_RID = 18
SECURITY_NT_NON_UNIQUE = 21
SECURITY_BUILTIN_DOMAIN_RID = 32
DOMAIN_USER_RID_ADMIN = 500
DOMAIN_USER_RID_GUEST = 501
DOMAIN_GROUP_RID_ADMINS = 512
DOMAIN_GROUP_RID_USERS = 513
DOMAIN_GROUP_RID_GUESTS = 514
DOMAIN_ALIAS_RID_ADMINS = 544
DOMAIN_ALIAS_RID_USERS = 545
DOMAIN_ALIAS_RID_GUESTS = 546
DOMAIN_ALIAS_RID_POWER_USERS = 547
DOMAIN_ALIAS_RID_ACCOUNT_OPS = 548
DOMAIN_ALIAS_RID_SYSTEM_OPS = 549
DOMAIN_ALIAS_RID_PRINT_OPS = 550
DOMAIN_ALIAS_RID_BACKUP_OPS = 551
DOMAIN_ALIAS_RID_REPLICATOR = 552
SE_GROUP_MANDATORY = 1
SE_GROUP_ENABLED_BY_DEFAULT = 2
SE_GROUP_ENABLED = 4
SE_GROUP_OWNER = 8
SE_GROUP_LOGON_ID = -1073741824
ACL_REVISION = 2
ACL_REVISION1 = 1
ACL_REVISION2 = 2
ACCESS_ALLOWED_ACE_TYPE = 0
ACCESS_DENIED_ACE_TYPE = 1
SYSTEM_AUDIT_ACE_TYPE = 2
SYSTEM_ALARM_ACE_TYPE = 3
OBJECT_INHERIT_ACE = 1
CONTAINER_INHERIT_ACE = 2
NO_PROPAGATE_INHERIT_ACE = 4
INHERIT_ONLY_ACE = 8
VALID_INHERIT_FLAGS = 15
SUCCESSFUL_ACCESS_ACE_FLAG = 64
FAILED_ACCESS_ACE_FLAG = 128
SECURITY_DESCRIPTOR_REVISION = 1
SECURITY_DESCRIPTOR_REVISION1 = 1
SECURITY_DESCRIPTOR_MIN_LENGTH = 20
SE_OWNER_DEFAULTED = 1
SE_GROUP_DEFAULTED = 2
SE_DACL_PRESENT = 4
SE_DACL_DEFAULTED = 8
SE_SACL_PRESENT = 16
SE_SACL_DEFAULTED = 32
SE_SELF_RELATIVE = 32768
SE_PRIVILEGE_ENABLED_BY_DEFAULT = 1
SE_PRIVILEGE_ENABLED = 2
SE_PRIVILEGE_USED_FOR_ACCESS = -2147483648
PRIVILEGE_SET_ALL_NECESSARY = 1
SE_CREATE_TOKEN_NAME = "SeCreateTokenPrivilege"
SE_ASSIGNPRIMARYTOKEN_NAME = "SeAssignPrimaryTokenPrivilege"
SE_LOCK_MEMORY_NAME = "SeLockMemoryPrivilege"
SE_INCREASE_QUOTA_NAME = "SeIncreaseQuotaPrivilege"
SE_UNSOLICITED_INPUT_NAME = "SeUnsolicitedInputPrivilege"
SE_MACHINE_ACCOUNT_NAME = "SeMachineAccountPrivilege"
SE_TCB_NAME = "SeTcbPrivilege"
SE_SECURITY_NAME = "SeSecurityPrivilege"
SE_TAKE_OWNERSHIP_NAME = "SeTakeOwnershipPrivilege"
SE_LOAD_DRIVER_NAME = "SeLoadDriverPrivilege"
SE_SYSTEM_PROFILE_NAME = "SeSystemProfilePrivilege"
SE_SYSTEMTIME_NAME = "SeSystemtimePrivilege"
SE_PROF_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"
SE_INC_BASE_PRIORITY_NAME = "SeIncreaseBasePriorityPrivilege"
SE_CREATE_PAGEFILE_NAME = "SeCreatePagefilePrivilege"
SE_CREATE_PERMANENT_NAME = "SeCreatePermanentPrivilege"
SE_BACKUP_NAME = "SeBackupPrivilege"
SE_RESTORE_NAME = "SeRestorePrivilege"
SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
SE_DEBUG_NAME = "SeDebugPrivilege"
SE_AUDIT_NAME = "SeAuditPrivilege"
SE_SYSTEM_ENVIRONMENT_NAME = "SeSystemEnvironmentPrivilege"
SE_CHANGE_NOTIFY_NAME = "SeChangeNotifyPrivilege"
SE_REMOTE_SHUTDOWN_NAME = "SeRemoteShutdownPrivilege"

TOKEN_ASSIGN_PRIMARY = 1
TOKEN_DUPLICATE = 2
TOKEN_IMPERSONATE = 4
TOKEN_QUERY = 8
TOKEN_QUERY_SOURCE = 16
TOKEN_ADJUST_PRIVILEGES = 32
TOKEN_ADJUST_GROUPS = 64
TOKEN_ADJUST_DEFAULT = 128
TOKEN_ADJUST_SESSIONID = 256
TOKEN_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TOKEN_ASSIGN_PRIMARY
    | TOKEN_DUPLICATE
    | TOKEN_IMPERSONATE
    | TOKEN_QUERY
    | TOKEN_QUERY_SOURCE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
    | TOKEN_ADJUST_SESSIONID
)
TOKEN_READ = STANDARD_RIGHTS_READ | TOKEN_QUERY
TOKEN_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)
TOKEN_EXECUTE = STANDARD_RIGHTS_EXECUTE
TOKEN_SOURCE_LENGTH = 8

KEY_QUERY_VALUE = 1
KEY_SET_VALUE = 2
KEY_CREATE_SUB_KEY = 4
KEY_ENUMERATE_SUB_KEYS = 8
KEY_NOTIFY = 16
KEY_CREATE_LINK = 32
KEY_WOW64_32KEY = 512
KEY_WOW64_64KEY = 256
KEY_WOW64_RES = 768
KEY_READ = (
    STANDARD_RIGHTS_READ | KEY_QUERY_VALUE | KEY_ENUMERATE_SUB_KEYS | KEY_NOTIFY
) & (~SYNCHRONIZE)
KEY_WRITE = (STANDARD_RIGHTS_WRITE | KEY_SET_VALUE | KEY_CREATE_SUB_KEY) & (
    ~SYNCHRONIZE
)
KEY_EXECUTE = (KEY_READ) & (~SYNCHRONIZE)
KEY_ALL_ACCESS = (
    STANDARD_RIGHTS_ALL
    | KEY_QUERY_VALUE
    | KEY_SET_VALUE
    | KEY_CREATE_SUB_KEY
    | KEY_ENUMERATE_SUB_KEYS
    | KEY_NOTIFY
    | KEY_CREATE_LINK
) & (~SYNCHRONIZE)
REG_NOTIFY_CHANGE_ATTRIBUTES = 2
REG_NOTIFY_CHANGE_SECURITY = 8
REG_NONE = 0  # No value type
REG_SZ = 1  # Unicode nul terminated string
REG_EXPAND_SZ = 2  # Unicode nul terminated string
# (with environment variable references)
REG_BINARY = 3  # Free form binary
REG_DWORD = 4  # 32-bit number
REG_DWORD_LITTLE_ENDIAN = 4  # 32-bit number (same as REG_DWORD)
REG_DWORD_BIG_ENDIAN = 5  # 32-bit number
REG_LINK = 6  # Symbolic Link (unicode)
REG_MULTI_SZ = 7  # Multiple Unicode strings
REG_RESOURCE_LIST = 8  # Resource list in the resource map
REG_FULL_RESOURCE_DESCRIPTOR = 9  # Resource list in the hardware description
REG_RESOURCE_REQUIREMENTS_LIST = 10
REG_QWORD = 11  # 64-bit number
REG_QWORD_LITTLE_ENDIAN = 11  # 64-bit number (same as REG_QWORD)


# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
# Included from string.h
_NLSCMPERROR = 2147483647
NULL = 0
HEAP_NO_SERIALIZE = 1
HEAP_GROWABLE = 2
HEAP_GENERATE_EXCEPTIONS = 4
HEAP_ZERO_MEMORY = 8
HEAP_REALLOC_IN_PLACE_ONLY = 16
HEAP_TAIL_CHECKING_ENABLED = 32
HEAP_FREE_CHECKING_ENABLED = 64
HEAP_DISABLE_COALESCE_ON_FREE = 128
IS_TEXT_UNICODE_ASCII16 = 1
IS_TEXT_UNICODE_REVERSE_ASCII16 = 16
IS_TEXT_UNICODE_STATISTICS = 2
IS_TEXT_UNICODE_REVERSE_STATISTICS = 32
IS_TEXT_UNICODE_CONTROLS = 4
IS_TEXT_UNICODE_REVERSE_CONTROLS = 64
IS_TEXT_UNICODE_SIGNATURE = 8
IS_TEXT_UNICODE_REVERSE_SIGNATURE = 128
IS_TEXT_UNICODE_ILLEGAL_CHARS = 256
IS_TEXT_UNICODE_ODD_LENGTH = 512
IS_TEXT_UNICODE_DBCS_LEADBYTE = 1024
IS_TEXT_UNICODE_NULL_BYTES = 4096
IS_TEXT_UNICODE_UNICODE_MASK = 15
IS_TEXT_UNICODE_REVERSE_MASK = 240
IS_TEXT_UNICODE_NOT_UNICODE_MASK = 3840
IS_TEXT_UNICODE_NOT_ASCII_MASK = 61440
COMPRESSION_FORMAT_NONE = 0
COMPRESSION_FORMAT_DEFAULT = 1
COMPRESSION_FORMAT_LZNT1 = 2
COMPRESSION_ENGINE_STANDARD = 0
COMPRESSION_ENGINE_MAXIMUM = 256
MESSAGE_RESOURCE_UNICODE = 1
RTL_CRITSECT_TYPE = 0
RTL_RESOURCE_TYPE = 1
DLL_PROCESS_ATTACH = 1
DLL_THREAD_ATTACH = 2
DLL_THREAD_DETACH = 3
DLL_PROCESS_DETACH = 0
EVENTLOG_SEQUENTIAL_READ = 0x0001
EVENTLOG_SEEK_READ = 0x0002
EVENTLOG_FORWARDS_READ = 0x0004
EVENTLOG_BACKWARDS_READ = 0x0008
EVENTLOG_SUCCESS = 0x0000
EVENTLOG_ERROR_TYPE = 1
EVENTLOG_WARNING_TYPE = 2
EVENTLOG_INFORMATION_TYPE = 4
EVENTLOG_AUDIT_SUCCESS = 8
EVENTLOG_AUDIT_FAILURE = 16
EVENTLOG_START_PAIRED_EVENT = 1
EVENTLOG_END_PAIRED_EVENT = 2
EVENTLOG_END_ALL_PAIRED_EVENTS = 4
EVENTLOG_PAIRED_EVENT_ACTIVE = 8
EVENTLOG_PAIRED_EVENT_INACTIVE = 16
# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
OWNER_SECURITY_INFORMATION = 0x00000001
GROUP_SECURITY_INFORMATION = 0x00000002
DACL_SECURITY_INFORMATION = 0x00000004
SACL_SECURITY_INFORMATION = 0x00000008
IMAGE_SIZEOF_FILE_HEADER = 20
IMAGE_FILE_MACHINE_UNKNOWN = 0
IMAGE_NUMBEROF_DIRECTORY_ENTRIES = 16
IMAGE_SIZEOF_ROM_OPTIONAL_HEADER = 56
IMAGE_SIZEOF_STD_OPTIONAL_HEADER = 28
IMAGE_SIZEOF_NT_OPTIONAL_HEADER = 224
IMAGE_NT_OPTIONAL_HDR_MAGIC = 267
IMAGE_ROM_OPTIONAL_HDR_MAGIC = 263
IMAGE_SIZEOF_SHORT_NAME = 8
IMAGE_SIZEOF_SECTION_HEADER = 40
IMAGE_SIZEOF_SYMBOL = 18
IMAGE_SYM_CLASS_NULL = 0
IMAGE_SYM_CLASS_AUTOMATIC = 1
IMAGE_SYM_CLASS_EXTERNAL = 2
IMAGE_SYM_CLASS_STATIC = 3
IMAGE_SYM_CLASS_REGISTER = 4
IMAGE_SYM_CLASS_EXTERNAL_DEF = 5
IMAGE_SYM_CLASS_LABEL = 6
IMAGE_SYM_CLASS_UNDEFINED_LABEL = 7
IMAGE_SYM_CLASS_MEMBER_OF_STRUCT = 8
IMAGE_SYM_CLASS_ARGUMENT = 9
IMAGE_SYM_CLASS_STRUCT_TAG = 10
IMAGE_SYM_CLASS_MEMBER_OF_UNION = 11
IMAGE_SYM_CLASS_UNION_TAG = 12
IMAGE_SYM_CLASS_TYPE_DEFINITION = 13
IMAGE_SYM_CLASS_UNDEFINED_STATIC = 14
IMAGE_SYM_CLASS_ENUM_TAG = 15
IMAGE_SYM_CLASS_MEMBER_OF_ENUM = 16
IMAGE_SYM_CLASS_REGISTER_PARAM = 17
IMAGE_SYM_CLASS_BIT_FIELD = 18
IMAGE_SYM_CLASS_BLOCK = 100
IMAGE_SYM_CLASS_FUNCTION = 101
IMAGE_SYM_CLASS_END_OF_STRUCT = 102
IMAGE_SYM_CLASS_FILE = 103
IMAGE_SYM_CLASS_SECTION = 104
IMAGE_SYM_CLASS_WEAK_EXTERNAL = 105
N_BTMASK = 15
N_TMASK = 48
N_TMASK1 = 192
N_TMASK2 = 240
N_BTSHFT = 4
N_TSHIFT = 2
IMAGE_SIZEOF_AUX_SYMBOL = 18
IMAGE_COMDAT_SELECT_NODUPLICATES = 1
IMAGE_COMDAT_SELECT_ANY = 2
IMAGE_COMDAT_SELECT_SAME_SIZE = 3
IMAGE_COMDAT_SELECT_EXACT_MATCH = 4
IMAGE_COMDAT_SELECT_ASSOCIATIVE = 5
IMAGE_WEAK_EXTERN_SEARCH_NOLIBRARY = 1
IMAGE_WEAK_EXTERN_SEARCH_LIBRARY = 2
IMAGE_WEAK_EXTERN_SEARCH_ALIAS = 3
IMAGE_SIZEOF_RELOCATION = 10
IMAGE_REL_I386_SECTION = 10
IMAGE_REL_I386_SECREL = 11
IMAGE_REL_MIPS_REFHALF = 1
IMAGE_REL_MIPS_REFWORD = 2
IMAGE_REL_MIPS_JMPADDR = 3
IMAGE_REL_MIPS_REFHI = 4
IMAGE_REL_MIPS_REFLO = 5
IMAGE_REL_MIPS_GPREL = 6
IMAGE_REL_MIPS_LITERAL = 7
IMAGE_REL_MIPS_SECTION = 10
IMAGE_REL_MIPS_SECREL = 11
IMAGE_REL_MIPS_REFWORDNB = 34
IMAGE_REL_MIPS_PAIR = 37
IMAGE_REL_ALPHA_ABSOLUTE = 0
IMAGE_REL_ALPHA_REFLONG = 1
IMAGE_REL_ALPHA_REFQUAD = 2
IMAGE_REL_ALPHA_GPREL32 = 3
IMAGE_REL_ALPHA_LITERAL = 4
IMAGE_REL_ALPHA_LITUSE = 5
IMAGE_REL_ALPHA_GPDISP = 6
IMAGE_REL_ALPHA_BRADDR = 7
IMAGE_REL_ALPHA_HINT = 8
IMAGE_REL_ALPHA_INLINE_REFLONG = 9
IMAGE_REL_ALPHA_REFHI = 10
IMAGE_REL_ALPHA_REFLO = 11
IMAGE_REL_ALPHA_PAIR = 12
IMAGE_REL_ALPHA_MATCH = 13
IMAGE_REL_ALPHA_SECTION = 14
IMAGE_REL_ALPHA_SECREL = 15
IMAGE_REL_ALPHA_REFLONGNB = 16
IMAGE_SIZEOF_BASE_RELOCATION = 8
IMAGE_REL_BASED_ABSOLUTE = 0
IMAGE_REL_BASED_HIGH = 1
IMAGE_REL_BASED_LOW = 2
IMAGE_REL_BASED_HIGHLOW = 3
IMAGE_REL_BASED_HIGHADJ = 4
IMAGE_REL_BASED_MIPS_JMPADDR = 5
IMAGE_SIZEOF_LINENUMBER = 6
IMAGE_ARCHIVE_START_SIZE = 8
IMAGE_ARCHIVE_START = "!<arch>\n"
IMAGE_ARCHIVE_END = "`\n"
IMAGE_ARCHIVE_PAD = "\n"
IMAGE_ARCHIVE_LINKER_MEMBER = "/               "
IMAGE_ARCHIVE_LONGNAMES_MEMBER = "//              "
IMAGE_SIZEOF_ARCHIVE_MEMBER_HDR = 60
IMAGE_ORDINAL_FLAG = -2147483648


def IMAGE_SNAP_BY_ORDINAL(Ordinal):
    return (Ordinal & IMAGE_ORDINAL_FLAG) != 0


def IMAGE_ORDINAL(Ordinal):
    return Ordinal & 65535


IMAGE_RESOURCE_NAME_IS_STRING = -2147483648
IMAGE_RESOURCE_DATA_IS_DIRECTORY = -2147483648
IMAGE_DEBUG_TYPE_UNKNOWN = 0
IMAGE_DEBUG_TYPE_COFF = 1
IMAGE_DEBUG_TYPE_CODEVIEW = 2
IMAGE_DEBUG_TYPE_FPO = 3
IMAGE_DEBUG_TYPE_MISC = 4
IMAGE_DEBUG_TYPE_EXCEPTION = 5
IMAGE_DEBUG_TYPE_FIXUP = 6
IMAGE_DEBUG_TYPE_OMAP_TO_SRC = 7
IMAGE_DEBUG_TYPE_OMAP_FROM_SRC = 8
FRAME_FPO = 0
FRAME_TRAP = 1
FRAME_TSS = 2
SIZEOF_RFPO_DATA = 16
IMAGE_DEBUG_MISC_EXENAME = 1
IMAGE_SEPARATE_DEBUG_SIGNATURE = 18756
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
NEWFRAME = 1
ABORTDOC = 2
NEXTBAND = 3
SETCOLORTABLE = 4
GETCOLORTABLE = 5
FLUSHOUTPUT = 6
DRAFTMODE = 7
QUERYESCSUPPORT = 8
SETABORTPROC = 9
STARTDOC = 10
ENDDOC = 11
GETPHYSPAGESIZE = 12
GETPRINTINGOFFSET = 13
GETSCALINGFACTOR = 14
MFCOMMENT = 15
GETPENWIDTH = 16
SETCOPYCOUNT = 17
SELECTPAPERSOURCE = 18
DEVICEDATA = 19
PASSTHROUGH = 19
GETTECHNOLGY = 20
GETTECHNOLOGY = 20
SETLINECAP = 21
SETLINEJOIN = 22
SETMITERLIMIT = 23
BANDINFO = 24
DRAWPATTERNRECT = 25
GETVECTORPENSIZE = 26
GETVECTORBRUSHSIZE = 27
ENABLEDUPLEX = 28
GETSETPAPERBINS = 29
GETSETPRINTORIENT = 30
ENUMPAPERBINS = 31
SETDIBSCALING = 32
EPSPRINTING = 33
ENUMPAPERMETRICS = 34
GETSETPAPERMETRICS = 35
POSTSCRIPT_DATA = 37
POSTSCRIPT_IGNORE = 38
MOUSETRAILS = 39
GETDEVICEUNITS = 42
GETEXTENDEDTEXTMETRICS = 256
GETEXTENTTABLE = 257
GETPAIRKERNTABLE = 258
GETTRACKKERNTABLE = 259
EXTTEXTOUT = 512
GETFACENAME = 513
DOWNLOADFACE = 514
ENABLERELATIVEWIDTHS = 768
ENABLEPAIRKERNING = 769
SETKERNTRACK = 770
SETALLJUSTVALUES = 771
SETCHARSET = 772
STRETCHBLT = 2048
GETSETSCREENPARAMS = 3072
BEGIN_PATH = 4096
CLIP_TO_PATH = 4097
END_PATH = 4098
EXT_DEVICE_CAPS = 4099
RESTORE_CTM = 4100
SAVE_CTM = 4101
SET_ARC_DIRECTION = 4102
SET_BACKGROUND_COLOR = 4103
SET_POLY_MODE = 4104
SET_SCREEN_ANGLE = 4105
SET_SPREAD = 4106
TRANSFORM_CTM = 4107
SET_CLIP_BOX = 4108
SET_BOUNDS = 4109
SET_MIRROR_MODE = 4110
OPENCHANNEL = 4110
DOWNLOADHEADER = 4111
CLOSECHANNEL = 4112
POSTSCRIPT_PASSTHROUGH = 4115
ENCAPSULATED_POSTSCRIPT = 4116
SP_NOTREPORTED = 16384
SP_ERROR = -1
SP_APPABORT = -2
SP_USERABORT = -3
SP_OUTOFDISK = -4
SP_OUTOFMEMORY = -5
PR_JOBSTATUS = 0

## GDI object types
OBJ_PEN = 1
OBJ_BRUSH = 2
OBJ_DC = 3
OBJ_METADC = 4
OBJ_PAL = 5
OBJ_FONT = 6
OBJ_BITMAP = 7
OBJ_REGION = 8
OBJ_METAFILE = 9
OBJ_MEMDC = 10
OBJ_EXTPEN = 11
OBJ_ENHMETADC = 12
OBJ_ENHMETAFILE = 13
OBJ_COLORSPACE = 14

MWT_IDENTITY = 1
MWT_LEFTMULTIPLY = 2
MWT_RIGHTMULTIPLY = 3
MWT_MIN = MWT_IDENTITY
MWT_MAX = MWT_RIGHTMULTIPLY
BI_RGB = 0
BI_RLE8 = 1
BI_RLE4 = 2
BI_BITFIELDS = 3
TMPF_FIXED_PITCH = 1
TMPF_VECTOR = 2
TMPF_DEVICE = 8
TMPF_TRUETYPE = 4
NTM_REGULAR = 64
NTM_BOLD = 32
NTM_ITALIC = 1
LF_FACESIZE = 32
LF_FULLFACESIZE = 64
OUT_DEFAULT_PRECIS = 0
OUT_STRING_PRECIS = 1
OUT_CHARACTER_PRECIS = 2
OUT_STROKE_PRECIS = 3
OUT_TT_PRECIS = 4
OUT_DEVICE_PRECIS = 5
OUT_RASTER_PRECIS = 6
OUT_TT_ONLY_PRECIS = 7
OUT_OUTLINE_PRECIS = 8
CLIP_DEFAULT_PRECIS = 0
CLIP_CHARACTER_PRECIS = 1
CLIP_STROKE_PRECIS = 2
CLIP_MASK = 15
CLIP_LH_ANGLES = 1 << 4
CLIP_TT_ALWAYS = 2 << 4
CLIP_EMBEDDED = 8 << 4
DEFAULT_QUALITY = 0
DRAFT_QUALITY = 1
PROOF_QUALITY = 2
NONANTIALIASED_QUALITY = 3
ANTIALIASED_QUALITY = 4
CLEARTYPE_QUALITY = 5
CLEARTYPE_NATURAL_QUALITY = 6
DEFAULT_PITCH = 0
FIXED_PITCH = 1
VARIABLE_PITCH = 2
ANSI_CHARSET = 0
DEFAULT_CHARSET = 1
SYMBOL_CHARSET = 2
SHIFTJIS_CHARSET = 128
HANGEUL_CHARSET = 129
CHINESEBIG5_CHARSET = 136
OEM_CHARSET = 255
JOHAB_CHARSET = 130
HEBREW_CHARSET = 177
ARABIC_CHARSET = 178
GREEK_CHARSET = 161
TURKISH_CHARSET = 162
VIETNAMESE_CHARSET = 163
THAI_CHARSET = 222
EASTEUROPE_CHARSET = 238
RUSSIAN_CHARSET = 204
MAC_CHARSET = 77
BALTIC_CHARSET = 186
FF_DONTCARE = 0 << 4
FF_ROMAN = 1 << 4
FF_SWISS = 2 << 4
FF_MODERN = 3 << 4
FF_SCRIPT = 4 << 4
FF_DECORATIVE = 5 << 4
FW_DONTCARE = 0
FW_THIN = 100
FW_EXTRALIGHT = 200
FW_LIGHT = 300
FW_NORMAL = 400
FW_MEDIUM = 500
FW_SEMIBOLD = 600
FW_BOLD = 700
FW_EXTRABOLD = 800
FW_HEAVY = 900
FW_ULTRALIGHT = FW_EXTRALIGHT
FW_REGULAR = FW_NORMAL
FW_DEMIBOLD = FW_SEMIBOLD
FW_ULTRABOLD = FW_EXTRABOLD
FW_BLACK = FW_HEAVY
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
BS_SOLID = 0
BS_NULL = 1
BS_HOLLOW = BS_NULL
BS_HATCHED = 2
BS_PATTERN = 3
BS_INDEXED = 4
BS_DIBPATTERN = 5
BS_DIBPATTERNPT = 6
BS_PATTERN8X8 = 7
BS_DIBPATTERN8X8 = 8
HS_HORIZONTAL = 0
HS_VERTICAL = 1
HS_FDIAGONAL = 2
HS_BDIAGONAL = 3
HS_CROSS = 4
HS_DIAGCROSS = 5
HS_FDIAGONAL1 = 6
HS_BDIAGONAL1 = 7
HS_SOLID = 8
HS_DENSE1 = 9
HS_DENSE2 = 10
HS_DENSE3 = 11
HS_DENSE4 = 12
HS_DENSE5 = 13
HS_DENSE6 = 14
HS_DENSE7 = 15
HS_DENSE8 = 16
HS_NOSHADE = 17
HS_HALFTONE = 18
HS_SOLIDCLR = 19
HS_DITHEREDCLR = 20
HS_SOLIDTEXTCLR = 21
HS_DITHEREDTEXTCLR = 22
HS_SOLIDBKCLR = 23
HS_DITHEREDBKCLR = 24
HS_API_MAX = 25
PS_SOLID = 0
PS_DASH = 1
PS_DOT = 2
PS_DASHDOT = 3
PS_DASHDOTDOT = 4
PS_NULL = 5
PS_INSIDEFRAME = 6
PS_USERSTYLE = 7
PS_ALTERNATE = 8
PS_STYLE_MASK = 15
PS_ENDCAP_ROUND = 0
PS_ENDCAP_SQUARE = 256
PS_ENDCAP_FLAT = 512
PS_ENDCAP_MASK = 3840
PS_JOIN_ROUND = 0
PS_JOIN_BEVEL = 4096
PS_JOIN_MITER = 8192
PS_JOIN_MASK = 61440
PS_COSMETIC = 0
PS_GEOMETRIC = 65536
PS_TYPE_MASK = 983040
AD_COUNTERCLOCKWISE = 1
AD_CLOCKWISE = 2
DRIVERVERSION = 0
TECHNOLOGY = 2
HORZSIZE = 4
VERTSIZE = 6
HORZRES = 8
VERTRES = 10
BITSPIXEL = 12
PLANES = 14
NUMBRUSHES = 16
NUMPENS = 18
NUMMARKERS = 20
NUMFONTS = 22
NUMCOLORS = 24
PDEVICESIZE = 26
CURVECAPS = 28
LINECAPS = 30
POLYGONALCAPS = 32
TEXTCAPS = 34
CLIPCAPS = 36
RASTERCAPS = 38
ASPECTX = 40
ASPECTY = 42
ASPECTXY = 44
LOGPIXELSX = 88
LOGPIXELSY = 90
SIZEPALETTE = 104
NUMRESERVED = 106
COLORRES = 108

PHYSICALWIDTH = 110
PHYSICALHEIGHT = 111
PHYSICALOFFSETX = 112
PHYSICALOFFSETY = 113
SCALINGFACTORX = 114
SCALINGFACTORY = 115
VREFRESH = 116
DESKTOPVERTRES = 117
DESKTOPHORZRES = 118
BLTALIGNMENT = 119
SHADEBLENDCAPS = 120
COLORMGMTCAPS = 121

DT_PLOTTER = 0
DT_RASDISPLAY = 1
DT_RASPRINTER = 2
DT_RASCAMERA = 3
DT_CHARSTREAM = 4
DT_METAFILE = 5
DT_DISPFILE = 6
CC_NONE = 0
CC_CIRCLES = 1
CC_PIE = 2
CC_CHORD = 4
CC_ELLIPSES = 8
CC_WIDE = 16
CC_STYLED = 32
CC_WIDESTYLED = 64
CC_INTERIORS = 128
CC_ROUNDRECT = 256
LC_NONE = 0
LC_POLYLINE = 2
LC_MARKER = 4
LC_POLYMARKER = 8
LC_WIDE = 16
LC_STYLED = 32
LC_WIDESTYLED = 64
LC_INTERIORS = 128
PC_NONE = 0
PC_POLYGON = 1
PC_RECTANGLE = 2
PC_WINDPOLYGON = 4
PC_TRAPEZOID = 4
PC_SCANLINE = 8
PC_WIDE = 16
PC_STYLED = 32
PC_WIDESTYLED = 64
PC_INTERIORS = 128
CP_NONE = 0
CP_RECTANGLE = 1
CP_REGION = 2
TC_OP_CHARACTER = 1
TC_OP_STROKE = 2
TC_CP_STROKE = 4
TC_CR_90 = 8
TC_CR_ANY = 16
TC_SF_X_YINDEP = 32
TC_SA_DOUBLE = 64
TC_SA_INTEGER = 128
TC_SA_CONTIN = 256
TC_EA_DOUBLE = 512
TC_IA_ABLE = 1024
TC_UA_ABLE = 2048
TC_SO_ABLE = 4096
TC_RA_ABLE = 8192
TC_VA_ABLE = 16384
TC_RESERVED = 32768
TC_SCROLLBLT = 65536
RC_BITBLT = 1
RC_BANDING = 2
RC_SCALING = 4
RC_BITMAP64 = 8
RC_GDI20_OUTPUT = 16
RC_GDI20_STATE = 32
RC_SAVEBITMAP = 64
RC_DI_BITMAP = 128
RC_PALETTE = 256
RC_DIBTODEV = 512
RC_BIGFONT = 1024
RC_STRETCHBLT = 2048
RC_FLOODFILL = 4096
RC_STRETCHDIB = 8192
RC_OP_DX_OUTPUT = 16384
RC_DEVBITS = 32768
DIB_RGB_COLORS = 0
DIB_PAL_COLORS = 1
DIB_PAL_INDICES = 2
DIB_PAL_PHYSINDICES = 2
DIB_PAL_LOGINDICES = 4
SYSPAL_ERROR = 0
SYSPAL_STATIC = 1
SYSPAL_NOSTATIC = 2
CBM_CREATEDIB = 2
CBM_INIT = 4
FLOODFILLBORDER = 0
FLOODFILLSURFACE = 1
CCHFORMNAME = 32
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.

# DEVMODE.dmFields
DM_SPECVERSION = 800
DM_ORIENTATION = 1
DM_PAPERSIZE = 2
DM_PAPERLENGTH = 4
DM_PAPERWIDTH = 8
DM_SCALE = 16
DM_POSITION = 32
DM_NUP = 64
DM_DISPLAYORIENTATION = 128
DM_COPIES = 256
DM_DEFAULTSOURCE = 512
DM_PRINTQUALITY = 1024
DM_COLOR = 2048
DM_DUPLEX = 4096
DM_YRESOLUTION = 8192
DM_TTOPTION = 16384
DM_COLLATE = 32768
DM_FORMNAME = 65536
DM_LOGPIXELS = 131072
DM_BITSPERPEL = 262144
DM_PELSWIDTH = 524288
DM_PELSHEIGHT = 1048576
DM_DISPLAYFLAGS = 2097152
DM_DISPLAYFREQUENCY = 4194304
DM_ICMMETHOD = 8388608
DM_ICMINTENT = 16777216
DM_MEDIATYPE = 33554432
DM_DITHERTYPE = 67108864
DM_PANNINGWIDTH = 134217728
DM_PANNINGHEIGHT = 268435456
DM_DISPLAYFIXEDOUTPUT = 536870912

# DEVMODE.dmOrientation
DMORIENT_PORTRAIT = 1
DMORIENT_LANDSCAPE = 2

# DEVMODE.dmDisplayOrientation
DMDO_DEFAULT = 0
DMDO_90 = 1
DMDO_180 = 2
DMDO_270 = 3

# DEVMODE.dmDisplayFixedOutput
DMDFO_DEFAULT = 0
DMDFO_STRETCH = 1
DMDFO_CENTER = 2

# DEVMODE.dmPaperSize
DMPAPER_LETTER = 1
DMPAPER_LETTERSMALL = 2
DMPAPER_TABLOID = 3
DMPAPER_LEDGER = 4
DMPAPER_LEGAL = 5
DMPAPER_STATEMENT = 6
DMPAPER_EXECUTIVE = 7
DMPAPER_A3 = 8
DMPAPER_A4 = 9
DMPAPER_A4SMALL = 10
DMPAPER_A5 = 11
DMPAPER_B4 = 12
DMPAPER_B5 = 13
DMPAPER_FOLIO = 14
DMPAPER_QUARTO = 15
DMPAPER_10X14 = 16
DMPAPER_11X17 = 17
DMPAPER_NOTE = 18
DMPAPER_ENV_9 = 19
DMPAPER_ENV_10 = 20
DMPAPER_ENV_11 = 21
DMPAPER_ENV_12 = 22
DMPAPER_ENV_14 = 23
DMPAPER_CSHEET = 24
DMPAPER_DSHEET = 25
DMPAPER_ESHEET = 26
DMPAPER_ENV_DL = 27
DMPAPER_ENV_C5 = 28
DMPAPER_ENV_C3 = 29
DMPAPER_ENV_C4 = 30
DMPAPER_ENV_C6 = 31
DMPAPER_ENV_C65 = 32
DMPAPER_ENV_B4 = 33
DMPAPER_ENV_B5 = 34
DMPAPER_ENV_B6 = 35
DMPAPER_ENV_ITALY = 36
DMPAPER_ENV_MONARCH = 37
DMPAPER_ENV_PERSONAL = 38
DMPAPER_FANFOLD_US = 39
DMPAPER_FANFOLD_STD_GERMAN = 40
DMPAPER_FANFOLD_LGL_GERMAN = 41
DMPAPER_ISO_B4 = 42
DMPAPER_JAPANESE_POSTCARD = 43
DMPAPER_9X11 = 44
DMPAPER_10X11 = 45
DMPAPER_15X11 = 46
DMPAPER_ENV_INVITE = 47
DMPAPER_RESERVED_48 = 48
DMPAPER_RESERVED_49 = 49
DMPAPER_LETTER_EXTRA = 50
DMPAPER_LEGAL_EXTRA = 51
DMPAPER_TABLOID_EXTRA = 52
DMPAPER_A4_EXTRA = 53
DMPAPER_LETTER_TRANSVERSE = 54
DMPAPER_A4_TRANSVERSE = 55
DMPAPER_LETTER_EXTRA_TRANSVERSE = 56
DMPAPER_A_PLUS = 57
DMPAPER_B_PLUS = 58
DMPAPER_LETTER_PLUS = 59
DMPAPER_A4_PLUS = 60
DMPAPER_A5_TRANSVERSE = 61
DMPAPER_B5_TRANSVERSE = 62
DMPAPER_A3_EXTRA = 63
DMPAPER_A5_EXTRA = 64
DMPAPER_B5_EXTRA = 65
DMPAPER_A2 = 66
DMPAPER_A3_TRANSVERSE = 67
DMPAPER_A3_EXTRA_TRANSVERSE = 68
DMPAPER_DBL_JAPANESE_POSTCARD = 69
DMPAPER_A6 = 70
DMPAPER_JENV_KAKU2 = 71
DMPAPER_JENV_KAKU3 = 72
DMPAPER_JENV_CHOU3 = 73
DMPAPER_JENV_CHOU4 = 74
DMPAPER_LETTER_ROTATED = 75
DMPAPER_A3_ROTATED = 76
DMPAPER_A4_ROTATED = 77
DMPAPER_A5_ROTATED = 78
DMPAPER_B4_JIS_ROTATED = 79
DMPAPER_B5_JIS_ROTATED = 80
DMPAPER_JAPANESE_POSTCARD_ROTATED = 81
DMPAPER_DBL_JAPANESE_POSTCARD_ROTATED = 82
DMPAPER_A6_ROTATED = 83
DMPAPER_JENV_KAKU2_ROTATED = 84
DMPAPER_JENV_KAKU3_ROTATED = 85
DMPAPER_JENV_CHOU3_ROTATED = 86
DMPAPER_JENV_CHOU4_ROTATED = 87
DMPAPER_B6_JIS = 88
DMPAPER_B6_JIS_ROTATED = 89
DMPAPER_12X11 = 90
DMPAPER_JENV_YOU4 = 91
DMPAPER_JENV_YOU4_ROTATED = 92
DMPAPER_P16K = 93
DMPAPER_P32K = 94
DMPAPER_P32KBIG = 95
DMPAPER_PENV_1 = 96
DMPAPER_PENV_2 = 97
DMPAPER_PENV_3 = 98
DMPAPER_PENV_4 = 99
DMPAPER_PENV_5 = 100
DMPAPER_PENV_6 = 101
DMPAPER_PENV_7 = 102
DMPAPER_PENV_8 = 103
DMPAPER_PENV_9 = 104
DMPAPER_PENV_10 = 105
DMPAPER_P16K_ROTATED = 106
DMPAPER_P32K_ROTATED = 107
DMPAPER_P32KBIG_ROTATED = 108
DMPAPER_PENV_1_ROTATED = 109
DMPAPER_PENV_2_ROTATED = 110
DMPAPER_PENV_3_ROTATED = 111
DMPAPER_PENV_4_ROTATED = 112
DMPAPER_PENV_5_ROTATED = 113
DMPAPER_PENV_6_ROTATED = 114
DMPAPER_PENV_7_ROTATED = 115
DMPAPER_PENV_8_ROTATED = 116
DMPAPER_PENV_9_ROTATED = 117
DMPAPER_PENV_10_ROTATED = 118
DMPAPER_LAST = DMPAPER_PENV_10_ROTATED
DMPAPER_USER = 256

# DEVMODE.dmDefaultSource
DMBIN_UPPER = 1
DMBIN_ONLYONE = 1
DMBIN_LOWER = 2
DMBIN_MIDDLE = 3
DMBIN_MANUAL = 4
DMBIN_ENVELOPE = 5
DMBIN_ENVMANUAL = 6
DMBIN_AUTO = 7
DMBIN_TRACTOR = 8
DMBIN_SMALLFMT = 9
DMBIN_LARGEFMT = 10
DMBIN_LARGECAPACITY = 11
DMBIN_CASSETTE = 14
DMBIN_FORMSOURCE = 15
DMBIN_LAST = DMBIN_FORMSOURCE
DMBIN_USER = 256

# DEVMODE.dmPrintQuality
DMRES_DRAFT = -1
DMRES_LOW = -2
DMRES_MEDIUM = -3
DMRES_HIGH = -4

# DEVMODE.dmColor
DMCOLOR_MONOCHROME = 1
DMCOLOR_COLOR = 2

# DEVMODE.dmDuplex
DMDUP_SIMPLEX = 1
DMDUP_VERTICAL = 2
DMDUP_HORIZONTAL = 3

# DEVMODE.dmTTOption
DMTT_BITMAP = 1
DMTT_DOWNLOAD = 2
DMTT_SUBDEV = 3
DMTT_DOWNLOAD_OUTLINE = 4

# DEVMODE.dmCollate
DMCOLLATE_FALSE = 0
DMCOLLATE_TRUE = 1

# DEVMODE.dmDisplayFlags
DM_GRAYSCALE = 1
DM_INTERLACED = 2

# DEVMODE.dmICMMethod
DMICMMETHOD_NONE = 1
DMICMMETHOD_SYSTEM = 2
DMICMMETHOD_DRIVER = 3
DMICMMETHOD_DEVICE = 4
DMICMMETHOD_USER = 256

# DEVMODE.dmICMIntent
DMICM_SATURATE = 1
DMICM_CONTRAST = 2
DMICM_COLORIMETRIC = 3
DMICM_ABS_COLORIMETRIC = 4
DMICM_USER = 256

# DEVMODE.dmMediaType
DMMEDIA_STANDARD = 1
DMMEDIA_TRANSPARENCY = 2
DMMEDIA_GLOSSY = 3
DMMEDIA_USER = 256

# DEVMODE.dmDitherType
DMDITHER_NONE = 1
DMDITHER_COARSE = 2
DMDITHER_FINE = 3
DMDITHER_LINEART = 4
DMDITHER_ERRORDIFFUSION = 5
DMDITHER_RESERVED6 = 6
DMDITHER_RESERVED7 = 7
DMDITHER_RESERVED8 = 8
DMDITHER_RESERVED9 = 9
DMDITHER_GRAYSCALE = 10
DMDITHER_USER = 256

# DEVMODE.dmNup
DMNUP_SYSTEM = 1
DMNUP_ONEUP = 2

# used with ExtEscape
FEATURESETTING_NUP = 0
FEATURESETTING_OUTPUT = 1
FEATURESETTING_PSLEVEL = 2
FEATURESETTING_CUSTPAPER = 3
FEATURESETTING_MIRROR = 4
FEATURESETTING_NEGATIVE = 5
FEATURESETTING_PROTOCOL = 6
FEATURESETTING_PRIVATE_BEGIN = 0x1000
FEATURESETTING_PRIVATE_END = 0x1FFF

RDH_RECTANGLES = 1
GGO_METRICS = 0
GGO_BITMAP = 1
GGO_NATIVE = 2
TT_POLYGON_TYPE = 24
TT_PRIM_LINE = 1
TT_PRIM_QSPLINE = 2
TT_AVAILABLE = 1
TT_ENABLED = 2
DM_UPDATE = 1
DM_COPY = 2
DM_PROMPT = 4
DM_MODIFY = 8
DM_IN_BUFFER = DM_MODIFY
DM_IN_PROMPT = DM_PROMPT
DM_OUT_BUFFER = DM_COPY
DM_OUT_DEFAULT = DM_UPDATE

# DISPLAY_DEVICE.StateFlags
DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 1
DISPLAY_DEVICE_MULTI_DRIVER = 2
DISPLAY_DEVICE_PRIMARY_DEVICE = 4
DISPLAY_DEVICE_MIRRORING_DRIVER = 8
DISPLAY_DEVICE_VGA_COMPATIBLE = 16
DISPLAY_DEVICE_REMOVABLE = 32
DISPLAY_DEVICE_MODESPRUNED = 134217728
DISPLAY_DEVICE_REMOTE = 67108864
DISPLAY_DEVICE_DISCONNECT = 33554432

# DeviceCapabilities types
DC_FIELDS = 1
DC_PAPERS = 2
DC_PAPERSIZE = 3
DC_MINEXTENT = 4
DC_MAXEXTENT = 5
DC_BINS = 6
DC_DUPLEX = 7
DC_SIZE = 8
DC_EXTRA = 9
DC_VERSION = 10
DC_DRIVER = 11
DC_BINNAMES = 12
DC_ENUMRESOLUTIONS = 13
DC_FILEDEPENDENCIES = 14
DC_TRUETYPE = 15
DC_PAPERNAMES = 16
DC_ORIENTATION = 17
DC_COPIES = 18
DC_BINADJUST = 19
DC_EMF_COMPLIANT = 20
DC_DATATYPE_PRODUCED = 21
DC_COLLATE = 22
DC_MANUFACTURER = 23
DC_MODEL = 24
DC_PERSONALITY = 25
DC_PRINTRATE = 26
DC_PRINTRATEUNIT = 27
DC_PRINTERMEM = 28
DC_MEDIAREADY = 29
DC_STAPLE = 30
DC_PRINTRATEPPM = 31
DC_COLORDEVICE = 32
DC_NUP = 33
DC_MEDIATYPENAMES = 34
DC_MEDIATYPES = 35

PRINTRATEUNIT_PPM = 1
PRINTRATEUNIT_CPS = 2
PRINTRATEUNIT_LPM = 3
PRINTRATEUNIT_IPM = 4

# TrueType constants
DCTT_BITMAP = 1
DCTT_DOWNLOAD = 2
DCTT_SUBDEV = 4
DCTT_DOWNLOAD_OUTLINE = 8

DCBA_FACEUPNONE = 0
DCBA_FACEUPCENTER = 1
DCBA_FACEUPLEFT = 2
DCBA_FACEUPRIGHT = 3
DCBA_FACEDOWNNONE = 256
DCBA_FACEDOWNCENTER = 257
DCBA_FACEDOWNLEFT = 258
DCBA_FACEDOWNRIGHT = 259

CA_NEGATIVE = 1
CA_LOG_FILTER = 2
ILLUMINANT_DEVICE_DEFAULT = 0
ILLUMINANT_A = 1
ILLUMINANT_B = 2
ILLUMINANT_C = 3
ILLUMINANT_D50 = 4
ILLUMINANT_D55 = 5
ILLUMINANT_D65 = 6
ILLUMINANT_D75 = 7
ILLUMINANT_F2 = 8
ILLUMINANT_MAX_INDEX = ILLUMINANT_F2
ILLUMINANT_TUNGSTEN = ILLUMINANT_A
ILLUMINANT_DAYLIGHT = ILLUMINANT_C
ILLUMINANT_FLUORESCENT = ILLUMINANT_F2
ILLUMINANT_NTSC = ILLUMINANT_C

# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
FONTMAPPER_MAX = 10
ENHMETA_SIGNATURE = 1179469088
ENHMETA_STOCK_OBJECT = -2147483648
EMR_HEADER = 1
EMR_POLYBEZIER = 2
EMR_POLYGON = 3
EMR_POLYLINE = 4
EMR_POLYBEZIERTO = 5
EMR_POLYLINETO = 6
EMR_POLYPOLYLINE = 7
EMR_POLYPOLYGON = 8
EMR_SETWINDOWEXTEX = 9
EMR_SETWINDOWORGEX = 10
EMR_SETVIEWPORTEXTEX = 11
EMR_SETVIEWPORTORGEX = 12
EMR_SETBRUSHORGEX = 13
EMR_EOF = 14
EMR_SETPIXELV = 15
EMR_SETMAPPERFLAGS = 16
EMR_SETMAPMODE = 17
EMR_SETBKMODE = 18
EMR_SETPOLYFILLMODE = 19
EMR_SETROP2 = 20
EMR_SETSTRETCHBLTMODE = 21
EMR_SETTEXTALIGN = 22
EMR_SETCOLORADJUSTMENT = 23
EMR_SETTEXTCOLOR = 24
EMR_SETBKCOLOR = 25
EMR_OFFSETCLIPRGN = 26
EMR_MOVETOEX = 27
EMR_SETMETARGN = 28
EMR_EXCLUDECLIPRECT = 29
EMR_INTERSECTCLIPRECT = 30
EMR_SCALEVIEWPORTEXTEX = 31
EMR_SCALEWINDOWEXTEX = 32
EMR_SAVEDC = 33
EMR_RESTOREDC = 34
EMR_SETWORLDTRANSFORM = 35
EMR_MODIFYWORLDTRANSFORM = 36
EMR_SELECTOBJECT = 37
EMR_CREATEPEN = 38
EMR_CREATEBRUSHINDIRECT = 39
EMR_DELETEOBJECT = 40
EMR_ANGLEARC = 41
EMR_ELLIPSE = 42
EMR_RECTANGLE = 43
EMR_ROUNDRECT = 44
EMR_ARC = 45
EMR_CHORD = 46
EMR_PIE = 47
EMR_SELECTPALETTE = 48
EMR_CREATEPALETTE = 49
EMR_SETPALETTEENTRIES = 50
EMR_RESIZEPALETTE = 51
EMR_REALIZEPALETTE = 52
EMR_EXTFLOODFILL = 53
EMR_LINETO = 54
EMR_ARCTO = 55
EMR_POLYDRAW = 56
EMR_SETARCDIRECTION = 57
EMR_SETMITERLIMIT = 58
EMR_BEGINPATH = 59
EMR_ENDPATH = 60
EMR_CLOSEFIGURE = 61
EMR_FILLPATH = 62
EMR_STROKEANDFILLPATH = 63
EMR_STROKEPATH = 64
EMR_FLATTENPATH = 65
EMR_WIDENPATH = 66
EMR_SELECTCLIPPATH = 67
EMR_ABORTPATH = 68
EMR_GDICOMMENT = 70
EMR_FILLRGN = 71
EMR_FRAMERGN = 72
EMR_INVERTRGN = 73
EMR_PAINTRGN = 74
EMR_EXTSELECTCLIPRGN = 75
EMR_BITBLT = 76
EMR_STRETCHBLT = 77
EMR_MASKBLT = 78
EMR_PLGBLT = 79
EMR_SETDIBITSTODEVICE = 80
EMR_STRETCHDIBITS = 81
EMR_EXTCREATEFONTINDIRECTW = 82
EMR_EXTTEXTOUTA = 83
EMR_EXTTEXTOUTW = 84
EMR_POLYBEZIER16 = 85
EMR_POLYGON16 = 86
EMR_POLYLINE16 = 87
EMR_POLYBEZIERTO16 = 88
EMR_POLYLINETO16 = 89
EMR_POLYPOLYLINE16 = 90
EMR_POLYPOLYGON16 = 91
EMR_POLYDRAW16 = 92
EMR_CREATEMONOBRUSH = 93
EMR_CREATEDIBPATTERNBRUSHPT = 94
EMR_EXTCREATEPEN = 95
EMR_POLYTEXTOUTA = 96
EMR_POLYTEXTOUTW = 97
EMR_MIN = 1
EMR_MAX = 97
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
PANOSE_COUNT = 10
PAN_FAMILYTYPE_INDEX = 0
PAN_SERIFSTYLE_INDEX = 1
PAN_WEIGHT_INDEX = 2
PAN_PROPORTION_INDEX = 3
PAN_CONTRAST_INDEX = 4
PAN_STROKEVARIATION_INDEX = 5
PAN_ARMSTYLE_INDEX = 6
PAN_LETTERFORM_INDEX = 7
PAN_MIDLINE_INDEX = 8
PAN_XHEIGHT_INDEX = 9
PAN_CULTURE_LATIN = 0
PAN_ANY = 0
PAN_NO_FIT = 1
PAN_FAMILY_TEXT_DISPLAY = 2
PAN_FAMILY_SCRIPT = 3
PAN_FAMILY_DECORATIVE = 4
PAN_FAMILY_PICTORIAL = 5
PAN_SERIF_COVE = 2
PAN_SERIF_OBTUSE_COVE = 3
PAN_SERIF_SQUARE_COVE = 4
PAN_SERIF_OBTUSE_SQUARE_COVE = 5
PAN_SERIF_SQUARE = 6
PAN_SERIF_THIN = 7
PAN_SERIF_BONE = 8
PAN_SERIF_EXAGGERATED = 9
PAN_SERIF_TRIANGLE = 10
PAN_SERIF_NORMAL_SANS = 11
PAN_SERIF_OBTUSE_SANS = 12
PAN_SERIF_PERP_SANS = 13
PAN_SERIF_FLARED = 14
PAN_SERIF_ROUNDED = 15
PAN_WEIGHT_VERY_LIGHT = 2
PAN_WEIGHT_LIGHT = 3
PAN_WEIGHT_THIN = 4
PAN_WEIGHT_BOOK = 5
PAN_WEIGHT_MEDIUM = 6
PAN_WEIGHT_DEMI = 7
PAN_WEIGHT_BOLD = 8
PAN_WEIGHT_HEAVY = 9
PAN_WEIGHT_BLACK = 10
PAN_WEIGHT_NORD = 11
PAN_PROP_OLD_STYLE = 2
PAN_PROP_MODERN = 3
PAN_PROP_EVEN_WIDTH = 4
PAN_PROP_EXPANDED = 5
PAN_PROP_CONDENSED = 6
PAN_PROP_VERY_EXPANDED = 7
PAN_PROP_VERY_CONDENSED = 8
PAN_PROP_MONOSPACED = 9
PAN_CONTRAST_NONE = 2
PAN_CONTRAST_VERY_LOW = 3
PAN_CONTRAST_LOW = 4
PAN_CONTRAST_MEDIUM_LOW = 5
PAN_CONTRAST_MEDIUM = 6
PAN_CONTRAST_MEDIUM_HIGH = 7
PAN_CONTRAST_HIGH = 8
PAN_CONTRAST_VERY_HIGH = 9
PAN_STROKE_GRADUAL_DIAG = 2
PAN_STROKE_GRADUAL_TRAN = 3
PAN_STROKE_GRADUAL_VERT = 4
PAN_STROKE_GRADUAL_HORZ = 5
PAN_STROKE_RAPID_VERT = 6
PAN_STROKE_RAPID_HORZ = 7
PAN_STROKE_INSTANT_VERT = 8
PAN_STRAIGHT_ARMS_HORZ = 2
PAN_STRAIGHT_ARMS_WEDGE = 3
PAN_STRAIGHT_ARMS_VERT = 4
PAN_STRAIGHT_ARMS_SINGLE_SERIF = 5
PAN_STRAIGHT_ARMS_DOUBLE_SERIF = 6
PAN_BENT_ARMS_HORZ = 7
PAN_BENT_ARMS_WEDGE = 8
PAN_BENT_ARMS_VERT = 9
PAN_BENT_ARMS_SINGLE_SERIF = 10
PAN_BENT_ARMS_DOUBLE_SERIF = 11
PAN_LETT_NORMAL_CONTACT = 2
PAN_LETT_NORMAL_WEIGHTED = 3
PAN_LETT_NORMAL_BOXED = 4
PAN_LETT_NORMAL_FLATTENED = 5
PAN_LETT_NORMAL_ROUNDED = 6
PAN_LETT_NORMAL_OFF_CENTER = 7
PAN_LETT_NORMAL_SQUARE = 8
PAN_LETT_OBLIQUE_CONTACT = 9
PAN_LETT_OBLIQUE_WEIGHTED = 10
PAN_LETT_OBLIQUE_BOXED = 11
PAN_LETT_OBLIQUE_FLATTENED = 12
PAN_LETT_OBLIQUE_ROUNDED = 13
PAN_LETT_OBLIQUE_OFF_CENTER = 14
PAN_LETT_OBLIQUE_SQUARE = 15
PAN_MIDLINE_STANDARD_TRIMMED = 2
PAN_MIDLINE_STANDARD_POINTED = 3
PAN_MIDLINE_STANDARD_SERIFED = 4
PAN_MIDLINE_HIGH_TRIMMED = 5
PAN_MIDLINE_HIGH_POINTED = 6
PAN_MIDLINE_HIGH_SERIFED = 7
PAN_MIDLINE_CONSTANT_TRIMMED = 8
PAN_MIDLINE_CONSTANT_POINTED = 9
PAN_MIDLINE_CONSTANT_SERIFED = 10
PAN_MIDLINE_LOW_TRIMMED = 11
PAN_MIDLINE_LOW_POINTED = 12
PAN_MIDLINE_LOW_SERIFED = 13
PAN_XHEIGHT_CONSTANT_SMALL = 2
PAN_XHEIGHT_CONSTANT_STD = 3
PAN_XHEIGHT_CONSTANT_LARGE = 4
PAN_XHEIGHT_DUCKING_SMALL = 5
PAN_XHEIGHT_DUCKING_STD = 6
PAN_XHEIGHT_DUCKING_LARGE = 7
ELF_VENDOR_SIZE = 4
ELF_VERSION = 0
ELF_CULTURE_LATIN = 0
RASTER_FONTTYPE = 1
DEVICE_FONTTYPE = 2
TRUETYPE_FONTTYPE = 4


def PALETTEINDEX(i):
    return 16777216 | (i)


PC_RESERVED = 1
PC_EXPLICIT = 2
PC_NOCOLLAPSE = 4


def GetRValue(rgb):
    return rgb & 0xFF


def GetGValue(rgb):
    return (rgb >> 8) & 0xFF


def GetBValue(rgb):
    return (rgb >> 16) & 0xFF


TRANSPARENT = 1
OPAQUE = 2
BKMODE_LAST = 2
GM_COMPATIBLE = 1
GM_ADVANCED = 2
GM_LAST = 2
PT_CLOSEFIGURE = 1
PT_LINETO = 2
PT_BEZIERTO = 4
PT_MOVETO = 6
MM_TEXT = 1
MM_LOMETRIC = 2
MM_HIMETRIC = 3
MM_LOENGLISH = 4
MM_HIENGLISH = 5
MM_TWIPS = 6
MM_ISOTROPIC = 7
MM_ANISOTROPIC = 8
MM_MIN = MM_TEXT
MM_MAX = MM_ANISOTROPIC
MM_MAX_FIXEDSCALE = MM_TWIPS
ABSOLUTE = 1
RELATIVE = 2
WHITE_BRUSH = 0
LTGRAY_BRUSH = 1
GRAY_BRUSH = 2
DKGRAY_BRUSH = 3
BLACK_BRUSH = 4
NULL_BRUSH = 5
HOLLOW_BRUSH = NULL_BRUSH
WHITE_PEN = 6
BLACK_PEN = 7
NULL_PEN = 8
OEM_FIXED_FONT = 10
ANSI_FIXED_FONT = 11
ANSI_VAR_FONT = 12
SYSTEM_FONT = 13
DEVICE_DEFAULT_FONT = 14
DEFAULT_PALETTE = 15
SYSTEM_FIXED_FONT = 16
STOCK_LAST = 16
CLR_INVALID = -1

DC_BRUSH = 18
DC_PEN = 19

# Exception/Status codes from winuser.h and winnt.h
STATUS_WAIT_0 = 0
STATUS_ABANDONED_WAIT_0 = 128
STATUS_USER_APC = 192
STATUS_TIMEOUT = 258
STATUS_PENDING = 259
STATUS_SEGMENT_NOTIFICATION = 1073741829
STATUS_GUARD_PAGE_VIOLATION = -2147483647
STATUS_DATATYPE_MISALIGNMENT = -2147483646
STATUS_BREAKPOINT = -2147483645
STATUS_SINGLE_STEP = -2147483644
STATUS_ACCESS_VIOLATION = -1073741819
STATUS_IN_PAGE_ERROR = -1073741818
STATUS_INVALID_HANDLE = -1073741816
STATUS_NO_MEMORY = -1073741801
STATUS_ILLEGAL_INSTRUCTION = -1073741795
STATUS_NONCONTINUABLE_EXCEPTION = -1073741787
STATUS_INVALID_DISPOSITION = -1073741786
STATUS_ARRAY_BOUNDS_EXCEEDED = -1073741684
STATUS_FLOAT_DENORMAL_OPERAND = -1073741683
STATUS_FLOAT_DIVIDE_BY_ZERO = -1073741682
STATUS_FLOAT_INEXACT_RESULT = -1073741681
STATUS_FLOAT_INVALID_OPERATION = -1073741680
STATUS_FLOAT_OVERFLOW = -1073741679
STATUS_FLOAT_STACK_CHECK = -1073741678
STATUS_FLOAT_UNDERFLOW = -1073741677
STATUS_INTEGER_DIVIDE_BY_ZERO = -1073741676
STATUS_INTEGER_OVERFLOW = -1073741675
STATUS_PRIVILEGED_INSTRUCTION = -1073741674
STATUS_STACK_OVERFLOW = -1073741571
STATUS_CONTROL_C_EXIT = -1073741510


WAIT_FAILED = -1
WAIT_OBJECT_0 = STATUS_WAIT_0 + 0

WAIT_ABANDONED = STATUS_ABANDONED_WAIT_0 + 0
WAIT_ABANDONED_0 = STATUS_ABANDONED_WAIT_0 + 0

WAIT_TIMEOUT = STATUS_TIMEOUT
WAIT_IO_COMPLETION = STATUS_USER_APC
STILL_ACTIVE = STATUS_PENDING
EXCEPTION_ACCESS_VIOLATION = STATUS_ACCESS_VIOLATION
EXCEPTION_DATATYPE_MISALIGNMENT = STATUS_DATATYPE_MISALIGNMENT
EXCEPTION_BREAKPOINT = STATUS_BREAKPOINT
EXCEPTION_SINGLE_STEP = STATUS_SINGLE_STEP
EXCEPTION_ARRAY_BOUNDS_EXCEEDED = STATUS_ARRAY_BOUNDS_EXCEEDED
EXCEPTION_FLT_DENORMAL_OPERAND = STATUS_FLOAT_DENORMAL_OPERAND
EXCEPTION_FLT_DIVIDE_BY_ZERO = STATUS_FLOAT_DIVIDE_BY_ZERO
EXCEPTION_FLT_INEXACT_RESULT = STATUS_FLOAT_INEXACT_RESULT
EXCEPTION_FLT_INVALID_OPERATION = STATUS_FLOAT_INVALID_OPERATION
EXCEPTION_FLT_OVERFLOW = STATUS_FLOAT_OVERFLOW
EXCEPTION_FLT_STACK_CHECK = STATUS_FLOAT_STACK_CHECK
EXCEPTION_FLT_UNDERFLOW = STATUS_FLOAT_UNDERFLOW
EXCEPTION_INT_DIVIDE_BY_ZERO = STATUS_INTEGER_DIVIDE_BY_ZERO
EXCEPTION_INT_OVERFLOW = STATUS_INTEGER_OVERFLOW
EXCEPTION_PRIV_INSTRUCTION = STATUS_PRIVILEGED_INSTRUCTION
EXCEPTION_IN_PAGE_ERROR = STATUS_IN_PAGE_ERROR
EXCEPTION_ILLEGAL_INSTRUCTION = STATUS_ILLEGAL_INSTRUCTION
EXCEPTION_NONCONTINUABLE_EXCEPTION = STATUS_NONCONTINUABLE_EXCEPTION
EXCEPTION_STACK_OVERFLOW = STATUS_STACK_OVERFLOW
EXCEPTION_INVALID_DISPOSITION = STATUS_INVALID_DISPOSITION
EXCEPTION_GUARD_PAGE = STATUS_GUARD_PAGE_VIOLATION
EXCEPTION_INVALID_HANDLE = STATUS_INVALID_HANDLE
CONTROL_C_EXIT = STATUS_CONTROL_C_EXIT

# winuser.h line 8594
# constants used with SystemParametersInfo
SPI_GETBEEP = 1
SPI_SETBEEP = 2
SPI_GETMOUSE = 3
SPI_SETMOUSE = 4
SPI_GETBORDER = 5
SPI_SETBORDER = 6
SPI_GETKEYBOARDSPEED = 10
SPI_SETKEYBOARDSPEED = 11
SPI_LANGDRIVER = 12
SPI_ICONHORIZONTALSPACING = 13
SPI_GETSCREENSAVETIMEOUT = 14
SPI_SETSCREENSAVETIMEOUT = 15
SPI_GETSCREENSAVEACTIVE = 16
SPI_SETSCREENSAVEACTIVE = 17
SPI_GETGRIDGRANULARITY = 18
SPI_SETGRIDGRANULARITY = 19
SPI_SETDESKWALLPAPER = 20
SPI_SETDESKPATTERN = 21
SPI_GETKEYBOARDDELAY = 22
SPI_SETKEYBOARDDELAY = 23
SPI_ICONVERTICALSPACING = 24
SPI_GETICONTITLEWRAP = 25
SPI_SETICONTITLEWRAP = 26
SPI_GETMENUDROPALIGNMENT = 27
SPI_SETMENUDROPALIGNMENT = 28
SPI_SETDOUBLECLKWIDTH = 29
SPI_SETDOUBLECLKHEIGHT = 30
SPI_GETICONTITLELOGFONT = 31
SPI_SETDOUBLECLICKTIME = 32
SPI_SETMOUSEBUTTONSWAP = 33
SPI_SETICONTITLELOGFONT = 34
SPI_GETFASTTASKSWITCH = 35
SPI_SETFASTTASKSWITCH = 36
SPI_SETDRAGFULLWINDOWS = 37
SPI_GETDRAGFULLWINDOWS = 38
SPI_GETNONCLIENTMETRICS = 41
SPI_SETNONCLIENTMETRICS = 42
SPI_GETMINIMIZEDMETRICS = 43
SPI_SETMINIMIZEDMETRICS = 44
SPI_GETICONMETRICS = 45
SPI_SETICONMETRICS = 46
SPI_SETWORKAREA = 47
SPI_GETWORKAREA = 48
SPI_SETPENWINDOWS = 49
SPI_GETFILTERKEYS = 50
SPI_SETFILTERKEYS = 51
SPI_GETTOGGLEKEYS = 52
SPI_SETTOGGLEKEYS = 53
SPI_GETMOUSEKEYS = 54
SPI_SETMOUSEKEYS = 55
SPI_GETSHOWSOUNDS = 56
SPI_SETSHOWSOUNDS = 57
SPI_GETSTICKYKEYS = 58
SPI_SETSTICKYKEYS = 59
SPI_GETACCESSTIMEOUT = 60
SPI_SETACCESSTIMEOUT = 61
SPI_GETSERIALKEYS = 62
SPI_SETSERIALKEYS = 63
SPI_GETSOUNDSENTRY = 64
SPI_SETSOUNDSENTRY = 65
SPI_GETHIGHCONTRAST = 66
SPI_SETHIGHCONTRAST = 67
SPI_GETKEYBOARDPREF = 68
SPI_SETKEYBOARDPREF = 69
SPI_GETSCREENREADER = 70
SPI_SETSCREENREADER = 71
SPI_GETANIMATION = 72
SPI_SETANIMATION = 73
SPI_GETFONTSMOOTHING = 74
SPI_SETFONTSMOOTHING = 75
SPI_SETDRAGWIDTH = 76
SPI_SETDRAGHEIGHT = 77
SPI_SETHANDHELD = 78
SPI_GETLOWPOWERTIMEOUT = 79
SPI_GETPOWEROFFTIMEOUT = 80
SPI_SETLOWPOWERTIMEOUT = 81
SPI_SETPOWEROFFTIMEOUT = 82
SPI_GETLOWPOWERACTIVE = 83
SPI_GETPOWEROFFACTIVE = 84
SPI_SETLOWPOWERACTIVE = 85
SPI_SETPOWEROFFACTIVE = 86
SPI_SETCURSORS = 87
SPI_SETICONS = 88
SPI_GETDEFAULTINPUTLANG = 89
SPI_SETDEFAULTINPUTLANG = 90
SPI_SETLANGTOGGLE = 91
SPI_GETWINDOWSEXTENSION = 92
SPI_SETMOUSETRAILS = 93
SPI_GETMOUSETRAILS = 94
SPI_GETSNAPTODEFBUTTON = 95
SPI_SETSNAPTODEFBUTTON = 96
SPI_SETSCREENSAVERRUNNING = 97
SPI_SCREENSAVERRUNNING = SPI_SETSCREENSAVERRUNNING
SPI_GETMOUSEHOVERWIDTH = 98
SPI_SETMOUSEHOVERWIDTH = 99
SPI_GETMOUSEHOVERHEIGHT = 100
SPI_SETMOUSEHOVERHEIGHT = 101
SPI_GETMOUSEHOVERTIME = 102
SPI_SETMOUSEHOVERTIME = 103
SPI_GETWHEELSCROLLLINES = 104
SPI_SETWHEELSCROLLLINES = 105
SPI_GETMENUSHOWDELAY = 106
SPI_SETMENUSHOWDELAY = 107

SPI_GETSHOWIMEUI = 110
SPI_SETSHOWIMEUI = 111
SPI_GETMOUSESPEED = 112
SPI_SETMOUSESPEED = 113
SPI_GETSCREENSAVERRUNNING = 114
SPI_GETDESKWALLPAPER = 115

SPI_GETACTIVEWINDOWTRACKING = 4096
SPI_SETACTIVEWINDOWTRACKING = 4097
SPI_GETMENUANIMATION = 4098
SPI_SETMENUANIMATION = 4099
SPI_GETCOMBOBOXANIMATION = 4100
SPI_SETCOMBOBOXANIMATION = 4101
SPI_GETLISTBOXSMOOTHSCROLLING = 4102
SPI_SETLISTBOXSMOOTHSCROLLING = 4103
SPI_GETGRADIENTCAPTIONS = 4104
SPI_SETGRADIENTCAPTIONS = 4105
SPI_GETKEYBOARDCUES = 4106
SPI_SETKEYBOARDCUES = 4107
SPI_GETMENUUNDERLINES = 4106
SPI_SETMENUUNDERLINES = 4107
SPI_GETACTIVEWNDTRKZORDER = 4108
SPI_SETACTIVEWNDTRKZORDER = 4109
SPI_GETHOTTRACKING = 4110
SPI_SETHOTTRACKING = 4111

SPI_GETMENUFADE = 4114
SPI_SETMENUFADE = 4115
SPI_GETSELECTIONFADE = 4116
SPI_SETSELECTIONFADE = 4117
SPI_GETTOOLTIPANIMATION = 4118
SPI_SETTOOLTIPANIMATION = 4119
SPI_GETTOOLTIPFADE = 4120
SPI_SETTOOLTIPFADE = 4121
SPI_GETCURSORSHADOW = 4122
SPI_SETCURSORSHADOW = 4123
SPI_GETMOUSESONAR = 4124
SPI_SETMOUSESONAR = 4125
SPI_GETMOUSECLICKLOCK = 4126
SPI_SETMOUSECLICKLOCK = 4127
SPI_GETMOUSEVANISH = 4128
SPI_SETMOUSEVANISH = 4129
SPI_GETFLATMENU = 4130
SPI_SETFLATMENU = 4131
SPI_GETDROPSHADOW = 4132
SPI_SETDROPSHADOW = 4133
SPI_GETBLOCKSENDINPUTRESETS = 4134
SPI_SETBLOCKSENDINPUTRESETS = 4135
SPI_GETUIEFFECTS = 4158
SPI_SETUIEFFECTS = 4159

SPI_GETFOREGROUNDLOCKTIMEOUT = 8192
SPI_SETFOREGROUNDLOCKTIMEOUT = 8193
SPI_GETACTIVEWNDTRKTIMEOUT = 8194
SPI_SETACTIVEWNDTRKTIMEOUT = 8195
SPI_GETFOREGROUNDFLASHCOUNT = 8196
SPI_SETFOREGROUNDFLASHCOUNT = 8197
SPI_GETCARETWIDTH = 8198
SPI_SETCARETWIDTH = 8199
SPI_GETMOUSECLICKLOCKTIME = 8200
SPI_SETMOUSECLICKLOCKTIME = 8201
SPI_GETFONTSMOOTHINGTYPE = 8202
SPI_SETFONTSMOOTHINGTYPE = 8203
SPI_GETFONTSMOOTHINGCONTRAST = 8204
SPI_SETFONTSMOOTHINGCONTRAST = 8205
SPI_GETFOCUSBORDERWIDTH = 8206
SPI_SETFOCUSBORDERWIDTH = 8207
SPI_GETFOCUSBORDERHEIGHT = 8208
SPI_SETFOCUSBORDERHEIGHT = 8209
SPI_GETFONTSMOOTHINGORIENTATION = 8210
SPI_SETFONTSMOOTHINGORIENTATION = 8211

# fWinIni flags for SystemParametersInfo
SPIF_UPDATEINIFILE = 1
SPIF_SENDWININICHANGE = 2
SPIF_SENDCHANGE = SPIF_SENDWININICHANGE

# used with SystemParametersInfo and SPI_GETFONTSMOOTHINGTYPE/SPI_SETFONTSMOOTHINGTYPE
FE_FONTSMOOTHINGSTANDARD = 1
FE_FONTSMOOTHINGCLEARTYPE = 2
FE_FONTSMOOTHINGDOCKING = 32768

METRICS_USEDEFAULT = -1
ARW_BOTTOMLEFT = 0
ARW_BOTTOMRIGHT = 1
ARW_TOPLEFT = 2
ARW_TOPRIGHT = 3
ARW_STARTMASK = 3
ARW_STARTRIGHT = 1
ARW_STARTTOP = 2
ARW_LEFT = 0
ARW_RIGHT = 0
ARW_UP = 4
ARW_DOWN = 4
ARW_HIDE = 8
# ARW_VALID = 0x000F
SERKF_SERIALKEYSON = 1
SERKF_AVAILABLE = 2
SERKF_INDICATOR = 4
HCF_HIGHCONTRASTON = 1
HCF_AVAILABLE = 2
HCF_HOTKEYACTIVE = 4
HCF_CONFIRMHOTKEY = 8
HCF_HOTKEYSOUND = 16
HCF_INDICATOR = 32
HCF_HOTKEYAVAILABLE = 64
CDS_UPDATEREGISTRY = 1
CDS_TEST = 2
CDS_FULLSCREEN = 4
CDS_GLOBAL = 8
CDS_SET_PRIMARY = 16
CDS_RESET = 1073741824
CDS_SETRECT = 536870912
CDS_NORESET = 268435456

# return values from ChangeDisplaySettings and ChangeDisplaySettingsEx
DISP_CHANGE_SUCCESSFUL = 0
DISP_CHANGE_RESTART = 1
DISP_CHANGE_FAILED = -1
DISP_CHANGE_BADMODE = -2
DISP_CHANGE_NOTUPDATED = -3
DISP_CHANGE_BADFLAGS = -4
DISP_CHANGE_BADPARAM = -5
DISP_CHANGE_BADDUALVIEW = -6

ENUM_CURRENT_SETTINGS = -1
ENUM_REGISTRY_SETTINGS = -2
FKF_FILTERKEYSON = 1
FKF_AVAILABLE = 2
FKF_HOTKEYACTIVE = 4
FKF_CONFIRMHOTKEY = 8
FKF_HOTKEYSOUND = 16
FKF_INDICATOR = 32
FKF_CLICKON = 64
SKF_STICKYKEYSON = 1
SKF_AVAILABLE = 2
SKF_HOTKEYACTIVE = 4
SKF_CONFIRMHOTKEY = 8
SKF_HOTKEYSOUND = 16
SKF_INDICATOR = 32
SKF_AUDIBLEFEEDBACK = 64
SKF_TRISTATE = 128
SKF_TWOKEYSOFF = 256
SKF_LALTLATCHED = 268435456
SKF_LCTLLATCHED = 67108864
SKF_LSHIFTLATCHED = 16777216
SKF_RALTLATCHED = 536870912
SKF_RCTLLATCHED = 134217728
SKF_RSHIFTLATCHED = 33554432
SKF_LWINLATCHED = 1073741824
SKF_RWINLATCHED = -2147483648
SKF_LALTLOCKED = 1048576
SKF_LCTLLOCKED = 262144
SKF_LSHIFTLOCKED = 65536
SKF_RALTLOCKED = 2097152
SKF_RCTLLOCKED = 524288
SKF_RSHIFTLOCKED = 131072
SKF_LWINLOCKED = 4194304
SKF_RWINLOCKED = 8388608
MKF_MOUSEKEYSON = 1
MKF_AVAILABLE = 2
MKF_HOTKEYACTIVE = 4
MKF_CONFIRMHOTKEY = 8
MKF_HOTKEYSOUND = 16
MKF_INDICATOR = 32
MKF_MODIFIERS = 64
MKF_REPLACENUMBERS = 128
MKF_LEFTBUTTONSEL = 268435456
MKF_RIGHTBUTTONSEL = 536870912
MKF_LEFTBUTTONDOWN = 16777216
MKF_RIGHTBUTTONDOWN = 33554432
MKF_MOUSEMODE = -2147483648
ATF_TIMEOUTON = 1
ATF_ONOFFFEEDBACK = 2
SSGF_NONE = 0
SSGF_DISPLAY = 3
SSTF_NONE = 0
SSTF_CHARS = 1
SSTF_BORDER = 2
SSTF_DISPLAY = 3
SSWF_NONE = 0
SSWF_TITLE = 1
SSWF_WINDOW = 2
SSWF_DISPLAY = 3
SSWF_CUSTOM = 4
SSF_SOUNDSENTRYON = 1
SSF_AVAILABLE = 2
SSF_INDICATOR = 4
TKF_TOGGLEKEYSON = 1
TKF_AVAILABLE = 2
TKF_HOTKEYACTIVE = 4
TKF_CONFIRMHOTKEY = 8
TKF_HOTKEYSOUND = 16
TKF_INDICATOR = 32
SLE_ERROR = 1
SLE_MINORERROR = 2
SLE_WARNING = 3
MONITOR_DEFAULTTONULL = 0
MONITOR_DEFAULTTOPRIMARY = 1
MONITOR_DEFAULTTONEAREST = 2
MONITORINFOF_PRIMARY = 1
CCHDEVICENAME = 32
CHILDID_SELF = 0
INDEXID_OBJECT = 0
INDEXID_CONTAINER = 0
OBJID_WINDOW = 0
OBJID_SYSMENU = -1
OBJID_TITLEBAR = -2
OBJID_MENU = -3
OBJID_CLIENT = -4
OBJID_VSCROLL = -5
OBJID_HSCROLL = -6
OBJID_SIZEGRIP = -7
OBJID_CARET = -8
OBJID_CURSOR = -9
OBJID_ALERT = -10
OBJID_SOUND = -11
EVENT_MIN = 1
EVENT_MAX = 2147483647
EVENT_SYSTEM_SOUND = 1
EVENT_SYSTEM_ALERT = 2
EVENT_SYSTEM_FOREGROUND = 3
EVENT_SYSTEM_MENUSTART = 4
EVENT_SYSTEM_MENUEND = 5
EVENT_SYSTEM_MENUPOPUPSTART = 6
EVENT_SYSTEM_MENUPOPUPEND = 7
EVENT_SYSTEM_CAPTURESTART = 8
EVENT_SYSTEM_CAPTUREEND = 9
EVENT_SYSTEM_MOVESIZESTART = 10
EVENT_SYSTEM_MOVESIZEEND = 11
EVENT_SYSTEM_CONTEXTHELPSTART = 12
EVENT_SYSTEM_CONTEXTHELPEND = 13
EVENT_SYSTEM_DRAGDROPSTART = 14
EVENT_SYSTEM_DRAGDROPEND = 15
EVENT_SYSTEM_DIALOGSTART = 16
EVENT_SYSTEM_DIALOGEND = 17
EVENT_SYSTEM_SCROLLINGSTART = 18
EVENT_SYSTEM_SCROLLINGEND = 19
EVENT_SYSTEM_SWITCHSTART = 20
EVENT_SYSTEM_SWITCHEND = 21
EVENT_SYSTEM_MINIMIZESTART = 22
EVENT_SYSTEM_MINIMIZEEND = 23
EVENT_OBJECT_CREATE = 32768
EVENT_OBJECT_DESTROY = 32769
EVENT_OBJECT_SHOW = 32770
EVENT_OBJECT_HIDE = 32771
EVENT_OBJECT_REORDER = 32772
EVENT_OBJECT_FOCUS = 32773
EVENT_OBJECT_SELECTION = 32774
EVENT_OBJECT_SELECTIONADD = 32775
EVENT_OBJECT_SELECTIONREMOVE = 32776
EVENT_OBJECT_SELECTIONWITHIN = 32777
EVENT_OBJECT_STATECHANGE = 32778
EVENT_OBJECT_LOCATIONCHANGE = 32779
EVENT_OBJECT_NAMECHANGE = 32780
EVENT_OBJECT_DESCRIPTIONCHANGE = 32781
EVENT_OBJECT_VALUECHANGE = 32782
EVENT_OBJECT_PARENTCHANGE = 32783
EVENT_OBJECT_HELPCHANGE = 32784
EVENT_OBJECT_DEFACTIONCHANGE = 32785
EVENT_OBJECT_ACCELERATORCHANGE = 32786
SOUND_SYSTEM_STARTUP = 1
SOUND_SYSTEM_SHUTDOWN = 2
SOUND_SYSTEM_BEEP = 3
SOUND_SYSTEM_ERROR = 4
SOUND_SYSTEM_QUESTION = 5
SOUND_SYSTEM_WARNING = 6
SOUND_SYSTEM_INFORMATION = 7
SOUND_SYSTEM_MAXIMIZE = 8
SOUND_SYSTEM_MINIMIZE = 9
SOUND_SYSTEM_RESTOREUP = 10
SOUND_SYSTEM_RESTOREDOWN = 11
SOUND_SYSTEM_APPSTART = 12
SOUND_SYSTEM_FAULT = 13
SOUND_SYSTEM_APPEND = 14
SOUND_SYSTEM_MENUCOMMAND = 15
SOUND_SYSTEM_MENUPOPUP = 16
CSOUND_SYSTEM = 16
ALERT_SYSTEM_INFORMATIONAL = 1
ALERT_SYSTEM_WARNING = 2
ALERT_SYSTEM_ERROR = 3
ALERT_SYSTEM_QUERY = 4
ALERT_SYSTEM_CRITICAL = 5
CALERT_SYSTEM = 6
WINEVENT_OUTOFCONTEXT = 0
WINEVENT_SKIPOWNTHREAD = 1
WINEVENT_SKIPOWNPROCESS = 2
WINEVENT_INCONTEXT = 4
GUI_CARETBLINKING = 1
GUI_INMOVESIZE = 2
GUI_INMENUMODE = 4
GUI_SYSTEMMENUMODE = 8
GUI_POPUPMENUMODE = 16
STATE_SYSTEM_UNAVAILABLE = 1
STATE_SYSTEM_SELECTED = 2
STATE_SYSTEM_FOCUSED = 4
STATE_SYSTEM_PRESSED = 8
STATE_SYSTEM_CHECKED = 16
STATE_SYSTEM_MIXED = 32
STATE_SYSTEM_READONLY = 64
STATE_SYSTEM_HOTTRACKED = 128
STATE_SYSTEM_DEFAULT = 256
STATE_SYSTEM_EXPANDED = 512
STATE_SYSTEM_COLLAPSED = 1024
STATE_SYSTEM_BUSY = 2048
STATE_SYSTEM_FLOATING = 4096
STATE_SYSTEM_MARQUEED = 8192
STATE_SYSTEM_ANIMATED = 16384
STATE_SYSTEM_INVISIBLE = 32768
STATE_SYSTEM_OFFSCREEN = 65536
STATE_SYSTEM_SIZEABLE = 131072
STATE_SYSTEM_MOVEABLE = 262144
STATE_SYSTEM_SELFVOICING = 524288
STATE_SYSTEM_FOCUSABLE = 1048576
STATE_SYSTEM_SELECTABLE = 2097152
STATE_SYSTEM_LINKED = 4194304
STATE_SYSTEM_TRAVERSED = 8388608
STATE_SYSTEM_MULTISELECTABLE = 16777216
STATE_SYSTEM_EXTSELECTABLE = 33554432
STATE_SYSTEM_ALERT_LOW = 67108864
STATE_SYSTEM_ALERT_MEDIUM = 134217728
STATE_SYSTEM_ALERT_HIGH = 268435456
STATE_SYSTEM_VALID = 536870911
CCHILDREN_TITLEBAR = 5
CCHILDREN_SCROLLBAR = 5
CURSOR_SHOWING = 1
WS_ACTIVECAPTION = 1
GA_MIC = 1
GA_PARENT = 1
GA_ROOT = 2
GA_ROOTOWNER = 3
GA_MAC = 4

# winuser.h line 1979
BF_LEFT = 1
BF_TOP = 2
BF_RIGHT = 4
BF_BOTTOM = 8
BF_TOPLEFT = BF_TOP | BF_LEFT
BF_TOPRIGHT = BF_TOP | BF_RIGHT
BF_BOTTOMLEFT = BF_BOTTOM | BF_LEFT
BF_BOTTOMRIGHT = BF_BOTTOM | BF_RIGHT
BF_RECT = BF_LEFT | BF_TOP | BF_RIGHT | BF_BOTTOM
BF_DIAGONAL = 16
BF_DIAGONAL_ENDTOPRIGHT = BF_DIAGONAL | BF_TOP | BF_RIGHT
BF_DIAGONAL_ENDTOPLEFT = BF_DIAGONAL | BF_TOP | BF_LEFT
BF_DIAGONAL_ENDBOTTOMLEFT = BF_DIAGONAL | BF_BOTTOM | BF_LEFT
BF_DIAGONAL_ENDBOTTOMRIGHT = BF_DIAGONAL | BF_BOTTOM | BF_RIGHT
BF_MIDDLE = 2048
BF_SOFT = 4096
BF_ADJUST = 8192
BF_FLAT = 16384
BF_MONO = 32768
DFC_CAPTION = 1
DFC_MENU = 2
DFC_SCROLL = 3
DFC_BUTTON = 4
DFC_POPUPMENU = 5
DFCS_CAPTIONCLOSE = 0
DFCS_CAPTIONMIN = 1
DFCS_CAPTIONMAX = 2
DFCS_CAPTIONRESTORE = 3
DFCS_CAPTIONHELP = 4
DFCS_MENUARROW = 0
DFCS_MENUCHECK = 1
DFCS_MENUBULLET = 2
DFCS_MENUARROWRIGHT = 4
DFCS_SCROLLUP = 0
DFCS_SCROLLDOWN = 1
DFCS_SCROLLLEFT = 2
DFCS_SCROLLRIGHT = 3
DFCS_SCROLLCOMBOBOX = 5
DFCS_SCROLLSIZEGRIP = 8
DFCS_SCROLLSIZEGRIPRIGHT = 16
DFCS_BUTTONCHECK = 0
DFCS_BUTTONRADIOIMAGE = 1
DFCS_BUTTONRADIOMASK = 2
DFCS_BUTTONRADIO = 4
DFCS_BUTTON3STATE = 8
DFCS_BUTTONPUSH = 16
DFCS_INACTIVE = 256
DFCS_PUSHED = 512
DFCS_CHECKED = 1024
DFCS_TRANSPARENT = 2048
DFCS_HOT = 4096
DFCS_ADJUSTRECT = 8192
DFCS_FLAT = 16384
DFCS_MONO = 32768
DC_ACTIVE = 1
DC_SMALLCAP = 2
DC_ICON = 4
DC_TEXT = 8
DC_INBUTTON = 16
DC_GRADIENT = 32
IDANI_OPEN = 1
IDANI_CLOSE = 2
IDANI_CAPTION = 3
CF_TEXT = 1
CF_BITMAP = 2
CF_METAFILEPICT = 3
CF_SYLK = 4
CF_DIF = 5
CF_TIFF = 6
CF_OEMTEXT = 7
CF_DIB = 8
CF_PALETTE = 9
CF_PENDATA = 10
CF_RIFF = 11
CF_WAVE = 12
CF_UNICODETEXT = 13
CF_ENHMETAFILE = 14
CF_HDROP = 15
CF_LOCALE = 16
CF_DIBV5 = 17
CF_MAX = 18
CF_OWNERDISPLAY = 128
CF_DSPTEXT = 129
CF_DSPBITMAP = 130
CF_DSPMETAFILEPICT = 131
CF_DSPENHMETAFILE = 142
CF_PRIVATEFIRST = 512
CF_PRIVATELAST = 767
CF_GDIOBJFIRST = 768
CF_GDIOBJLAST = 1023
FVIRTKEY = 1
FNOINVERT = 2
FSHIFT = 4
FCONTROL = 8
FALT = 16
WPF_SETMINPOSITION = 1
WPF_RESTORETOMAXIMIZED = 2
ODT_MENU = 1
ODT_LISTBOX = 2
ODT_COMBOBOX = 3
ODT_BUTTON = 4
ODT_STATIC = 5
ODA_DRAWENTIRE = 1
ODA_SELECT = 2
ODA_FOCUS = 4
ODS_SELECTED = 1
ODS_GRAYED = 2
ODS_DISABLED = 4
ODS_CHECKED = 8
ODS_FOCUS = 16
ODS_DEFAULT = 32
ODS_COMBOBOXEDIT = 4096
ODS_HOTLIGHT = 64
ODS_INACTIVE = 128
PM_NOREMOVE = 0
PM_REMOVE = 1
PM_NOYIELD = 2
MOD_ALT = 1
MOD_CONTROL = 2
MOD_SHIFT = 4
MOD_WIN = 8
MOD_NOREPEAT = 16384
IDHOT_SNAPWINDOW = -1
IDHOT_SNAPDESKTOP = -2
# EW_RESTARTWINDOWS = 0x0042
# EW_REBOOTSYSTEM = 0x0043
# EW_EXITANDEXECAPP = 0x0044
ENDSESSION_LOGOFF = -2147483648
EWX_LOGOFF = 0
EWX_SHUTDOWN = 1
EWX_REBOOT = 2
EWX_FORCE = 4
EWX_POWEROFF = 8
EWX_FORCEIFHUNG = 16
BSM_ALLDESKTOPS = 16
BROADCAST_QUERY_DENY = 1112363332  # Return this value to deny a query.

DBWF_LPARAMPOINTER = 32768

# winuser.h line 3232
SWP_NOSIZE = 1
SWP_NOMOVE = 2
SWP_NOZORDER = 4
SWP_NOREDRAW = 8
SWP_NOACTIVATE = 16
SWP_FRAMECHANGED = 32
SWP_SHOWWINDOW = 64
SWP_HIDEWINDOW = 128
SWP_NOCOPYBITS = 256
SWP_NOOWNERZORDER = 512
SWP_NOSENDCHANGING = 1024
SWP_DRAWFRAME = SWP_FRAMECHANGED
SWP_NOREPOSITION = SWP_NOOWNERZORDER
SWP_DEFERERASE = 8192
SWP_ASYNCWINDOWPOS = 16384

DLGWINDOWEXTRA = 30
# winuser.h line 4249
KEYEVENTF_EXTENDEDKEY = 1
KEYEVENTF_KEYUP = 2
KEYEVENTF_UNICODE = 4
KEYEVENTF_SCANCODE = 8
MOUSEEVENTF_MOVE = 1
MOUSEEVENTF_LEFTDOWN = 2
MOUSEEVENTF_LEFTUP = 4
MOUSEEVENTF_RIGHTDOWN = 8
MOUSEEVENTF_RIGHTUP = 16
MOUSEEVENTF_MIDDLEDOWN = 32
MOUSEEVENTF_MIDDLEUP = 64
MOUSEEVENTF_XDOWN = 128
MOUSEEVENTF_XUP = 256
MOUSEEVENTF_WHEEL = 2048
MOUSEEVENTF_HWHEEL = 4096
MOUSEEVENTF_MOVE_NOCOALESCE = 8192
MOUSEEVENTF_VIRTUALDESK = 16384
MOUSEEVENTF_ABSOLUTE = 32768
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2
MWMO_WAITALL = 1
MWMO_ALERTABLE = 2
MWMO_INPUTAVAILABLE = 4
QS_KEY = 1
QS_MOUSEMOVE = 2
QS_MOUSEBUTTON = 4
QS_POSTMESSAGE = 8
QS_TIMER = 16
QS_PAINT = 32
QS_SENDMESSAGE = 64
QS_HOTKEY = 128
QS_MOUSE = QS_MOUSEMOVE | QS_MOUSEBUTTON
QS_INPUT = QS_MOUSE | QS_KEY
QS_ALLEVENTS = QS_INPUT | QS_POSTMESSAGE | QS_TIMER | QS_PAINT | QS_HOTKEY
QS_ALLINPUT = (
    QS_INPUT | QS_POSTMESSAGE | QS_TIMER | QS_PAINT | QS_HOTKEY | QS_SENDMESSAGE
)


IMN_CLOSESTATUSWINDOW = 1
IMN_OPENSTATUSWINDOW = 2
IMN_CHANGECANDIDATE = 3
IMN_CLOSECANDIDATE = 4
IMN_OPENCANDIDATE = 5
IMN_SETCONVERSIONMODE = 6
IMN_SETSENTENCEMODE = 7
IMN_SETOPENSTATUS = 8
IMN_SETCANDIDATEPOS = 9
IMN_SETCOMPOSITIONFONT = 10
IMN_SETCOMPOSITIONWINDOW = 11
IMN_SETSTATUSWINDOWPOS = 12
IMN_GUIDELINE = 13
IMN_PRIVATE = 14

# winuser.h line 8518
HELP_CONTEXT = 1
HELP_QUIT = 2
HELP_INDEX = 3
HELP_CONTENTS = 3
HELP_HELPONHELP = 4
HELP_SETINDEX = 5
HELP_SETCONTENTS = 5
HELP_CONTEXTPOPUP = 8
HELP_FORCEFILE = 9
HELP_KEY = 257
HELP_COMMAND = 258
HELP_PARTIALKEY = 261
HELP_MULTIKEY = 513
HELP_SETWINPOS = 515
HELP_CONTEXTMENU = 10
HELP_FINDER = 11
HELP_WM_HELP = 12
HELP_SETPOPUP_POS = 13
HELP_TCARD = 32768
HELP_TCARD_DATA = 16
HELP_TCARD_OTHER_CALLER = 17
IDH_NO_HELP = 28440
IDH_MISSING_CONTEXT = 28441  # Control doesn't have matching help context
IDH_GENERIC_HELP_BUTTON = 28442  # Property sheet help button
IDH_OK = 28443
IDH_CANCEL = 28444
IDH_HELP = 28445
GR_GDIOBJECTS = 0  # Count of GDI objects
GR_USEROBJECTS = 1  # Count of USER objects
# Generated by h2py from \msvcnt\include\wingdi.h
# manually added (missed by generation some how!
SRCCOPY = 13369376  # dest = source
SRCPAINT = 15597702  # dest = source OR dest
SRCAND = 8913094  # dest = source AND dest
SRCINVERT = 6684742  # dest = source XOR dest
SRCERASE = 4457256  # dest = source AND (NOT dest )
NOTSRCCOPY = 3342344  # dest = (NOT source)
NOTSRCERASE = 1114278  # dest = (NOT src) AND (NOT dest)
MERGECOPY = 12583114  # dest = (source AND pattern)
MERGEPAINT = 12255782  # dest = (NOT source) OR dest
PATCOPY = 15728673  # dest = pattern
PATPAINT = 16452105  # dest = DPSnoo
PATINVERT = 5898313  # dest = pattern XOR dest
DSTINVERT = 5570569  # dest = (NOT dest)
BLACKNESS = 66  # dest = BLACK
WHITENESS = 16711778  # dest = WHITE

# hacked and split manually by mhammond.
R2_BLACK = 1
R2_NOTMERGEPEN = 2
R2_MASKNOTPEN = 3
R2_NOTCOPYPEN = 4
R2_MASKPENNOT = 5
R2_NOT = 6
R2_XORPEN = 7
R2_NOTMASKPEN = 8
R2_MASKPEN = 9
R2_NOTXORPEN = 10
R2_NOP = 11
R2_MERGENOTPEN = 12
R2_COPYPEN = 13
R2_MERGEPENNOT = 14
R2_MERGEPEN = 15
R2_WHITE = 16
R2_LAST = 16
GDI_ERROR = -1
ERROR = 0
NULLREGION = 1
SIMPLEREGION = 2
COMPLEXREGION = 3
RGN_ERROR = ERROR
RGN_AND = 1
RGN_OR = 2
RGN_XOR = 3
RGN_DIFF = 4
RGN_COPY = 5
RGN_MIN = RGN_AND
RGN_MAX = RGN_COPY

## Stretching modes used with Get/SetStretchBltMode
BLACKONWHITE = 1
WHITEONBLACK = 2
COLORONCOLOR = 3
HALFTONE = 4
MAXSTRETCHBLTMODE = 4
STRETCH_ANDSCANS = BLACKONWHITE
STRETCH_ORSCANS = WHITEONBLACK
STRETCH_DELETESCANS = COLORONCOLOR
STRETCH_HALFTONE = HALFTONE

ALTERNATE = 1
WINDING = 2
POLYFILL_LAST = 2

## flags used with SetLayout
LAYOUT_RTL = 1
LAYOUT_BTT = 2
LAYOUT_VBH = 4
LAYOUT_ORIENTATIONMASK = LAYOUT_RTL | LAYOUT_BTT | LAYOUT_VBH
LAYOUT_BITMAPORIENTATIONPRESERVED = 8

TA_NOUPDATECP = 0
TA_UPDATECP = 1
TA_LEFT = 0
TA_RIGHT = 2
TA_CENTER = 6
TA_TOP = 0
TA_BOTTOM = 8
TA_BASELINE = 24
TA_MASK = TA_BASELINE + TA_CENTER + TA_UPDATECP
VTA_BASELINE = TA_BASELINE
VTA_LEFT = TA_BOTTOM
VTA_RIGHT = TA_TOP
VTA_CENTER = TA_CENTER
VTA_BOTTOM = TA_RIGHT
VTA_TOP = TA_LEFT
ETO_GRAYED = 1
ETO_OPAQUE = 2
ETO_CLIPPED = 4
ASPECT_FILTERING = 1
DCB_RESET = 1
DCB_ACCUMULATE = 2
DCB_DIRTY = DCB_ACCUMULATE
DCB_SET = DCB_RESET | DCB_ACCUMULATE
DCB_ENABLE = 4
DCB_DISABLE = 8
META_SETBKCOLOR = 513
META_SETBKMODE = 258
META_SETMAPMODE = 259
META_SETROP2 = 260
META_SETRELABS = 261
META_SETPOLYFILLMODE = 262
META_SETSTRETCHBLTMODE = 263
META_SETTEXTCHAREXTRA = 264
META_SETTEXTCOLOR = 521
META_SETTEXTJUSTIFICATION = 522
META_SETWINDOWORG = 523
META_SETWINDOWEXT = 524
META_SETVIEWPORTORG = 525
META_SETVIEWPORTEXT = 526
META_OFFSETWINDOWORG = 527
META_SCALEWINDOWEXT = 1040
META_OFFSETVIEWPORTORG = 529
META_SCALEVIEWPORTEXT = 1042
META_LINETO = 531
META_MOVETO = 532
META_EXCLUDECLIPRECT = 1045
META_INTERSECTCLIPRECT = 1046
META_ARC = 2071
META_ELLIPSE = 1048
META_FLOODFILL = 1049
META_PIE = 2074
META_RECTANGLE = 1051
META_ROUNDRECT = 1564
META_PATBLT = 1565
META_SAVEDC = 30
META_SETPIXEL = 1055
META_OFFSETCLIPRGN = 544
META_TEXTOUT = 1313
META_BITBLT = 2338
META_STRETCHBLT = 2851
META_POLYGON = 804
META_POLYLINE = 805
META_ESCAPE = 1574
META_RESTOREDC = 295
META_FILLREGION = 552
META_FRAMEREGION = 1065
META_INVERTREGION = 298
META_PAINTREGION = 299
META_SELECTCLIPREGION = 300
META_SELECTOBJECT = 301
META_SETTEXTALIGN = 302
META_CHORD = 2096
META_SETMAPPERFLAGS = 561
META_EXTTEXTOUT = 2610
META_SETDIBTODEV = 3379
META_SELECTPALETTE = 564
META_REALIZEPALETTE = 53
META_ANIMATEPALETTE = 1078
META_SETPALENTRIES = 55
META_POLYPOLYGON = 1336
META_RESIZEPALETTE = 313
META_DIBBITBLT = 2368
META_DIBSTRETCHBLT = 2881
META_DIBCREATEPATTERNBRUSH = 322
META_STRETCHDIB = 3907
META_EXTFLOODFILL = 1352
META_DELETEOBJECT = 496
META_CREATEPALETTE = 247
META_CREATEPATTERNBRUSH = 505
META_CREATEPENINDIRECT = 762
META_CREATEFONTINDIRECT = 763
META_CREATEBRUSHINDIRECT = 764
META_CREATEREGION = 1791
FILE_BEGIN = 0
FILE_CURRENT = 1
FILE_END = 2
FILE_FLAG_WRITE_THROUGH = -2147483648
FILE_FLAG_OVERLAPPED = 1073741824
FILE_FLAG_NO_BUFFERING = 536870912
FILE_FLAG_RANDOM_ACCESS = 268435456
FILE_FLAG_SEQUENTIAL_SCAN = 134217728
FILE_FLAG_DELETE_ON_CLOSE = 67108864
FILE_FLAG_BACKUP_SEMANTICS = 33554432
FILE_FLAG_POSIX_SEMANTICS = 16777216
CREATE_NEW = 1
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
TRUNCATE_EXISTING = 5
PIPE_ACCESS_INBOUND = 1
PIPE_ACCESS_OUTBOUND = 2
PIPE_ACCESS_DUPLEX = 3
PIPE_CLIENT_END = 0
PIPE_SERVER_END = 1
PIPE_WAIT = 0
PIPE_NOWAIT = 1
PIPE_READMODE_BYTE = 0
PIPE_READMODE_MESSAGE = 2
PIPE_TYPE_BYTE = 0
PIPE_TYPE_MESSAGE = 4
PIPE_UNLIMITED_INSTANCES = 255
SECURITY_CONTEXT_TRACKING = 262144
SECURITY_EFFECTIVE_ONLY = 524288
SECURITY_SQOS_PRESENT = 1048576
SECURITY_VALID_SQOS_FLAGS = 2031616
DTR_CONTROL_DISABLE = 0
DTR_CONTROL_ENABLE = 1
DTR_CONTROL_HANDSHAKE = 2
RTS_CONTROL_DISABLE = 0
RTS_CONTROL_ENABLE = 1
RTS_CONTROL_HANDSHAKE = 2
RTS_CONTROL_TOGGLE = 3
GMEM_FIXED = 0
GMEM_MOVEABLE = 2
GMEM_NOCOMPACT = 16
GMEM_NODISCARD = 32
GMEM_ZEROINIT = 64
GMEM_MODIFY = 128
GMEM_DISCARDABLE = 256
GMEM_NOT_BANKED = 4096
GMEM_SHARE = 8192
GMEM_DDESHARE = 8192
GMEM_NOTIFY = 16384
GMEM_LOWER = GMEM_NOT_BANKED
GMEM_VALID_FLAGS = 32626
GMEM_INVALID_HANDLE = 32768
GHND = GMEM_MOVEABLE | GMEM_ZEROINIT
GPTR = GMEM_FIXED | GMEM_ZEROINIT
GMEM_DISCARDED = 16384
GMEM_LOCKCOUNT = 255
LMEM_FIXED = 0
LMEM_MOVEABLE = 2
LMEM_NOCOMPACT = 16
LMEM_NODISCARD = 32
LMEM_ZEROINIT = 64
LMEM_MODIFY = 128
LMEM_DISCARDABLE = 3840
LMEM_VALID_FLAGS = 3954
LMEM_INVALID_HANDLE = 32768
LHND = LMEM_MOVEABLE | LMEM_ZEROINIT
LPTR = LMEM_FIXED | LMEM_ZEROINIT
NONZEROLHND = LMEM_MOVEABLE
NONZEROLPTR = LMEM_FIXED
LMEM_DISCARDED = 16384
LMEM_LOCKCOUNT = 255
DEBUG_PROCESS = 1
DEBUG_ONLY_THIS_PROCESS = 2
CREATE_SUSPENDED = 4
DETACHED_PROCESS = 8
CREATE_NEW_CONSOLE = 16
NORMAL_PRIORITY_CLASS = 32
IDLE_PRIORITY_CLASS = 64
HIGH_PRIORITY_CLASS = 128
REALTIME_PRIORITY_CLASS = 256
CREATE_NEW_PROCESS_GROUP = 512
CREATE_UNICODE_ENVIRONMENT = 1024
CREATE_SEPARATE_WOW_VDM = 2048
CREATE_SHARED_WOW_VDM = 4096
CREATE_DEFAULT_ERROR_MODE = 67108864
CREATE_NO_WINDOW = 134217728
PROFILE_USER = 268435456
PROFILE_KERNEL = 536870912
PROFILE_SERVER = 1073741824
THREAD_BASE_PRIORITY_LOWRT = 15
THREAD_BASE_PRIORITY_MAX = 2
THREAD_BASE_PRIORITY_MIN = -2
THREAD_BASE_PRIORITY_IDLE = -15
THREAD_PRIORITY_LOWEST = THREAD_BASE_PRIORITY_MIN
THREAD_PRIORITY_BELOW_NORMAL = THREAD_PRIORITY_LOWEST + 1
THREAD_PRIORITY_HIGHEST = THREAD_BASE_PRIORITY_MAX
THREAD_PRIORITY_ABOVE_NORMAL = THREAD_PRIORITY_HIGHEST - 1
THREAD_PRIORITY_ERROR_RETURN = MAXLONG
THREAD_PRIORITY_TIME_CRITICAL = THREAD_BASE_PRIORITY_LOWRT
THREAD_PRIORITY_IDLE = THREAD_BASE_PRIORITY_IDLE
THREAD_PRIORITY_NORMAL = 0
THREAD_MODE_BACKGROUND_BEGIN = 0x00010000
THREAD_MODE_BACKGROUND_END = 0x00020000

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
RIP_EVENT = 9
DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_REMOTE = 4
DRIVE_CDROM = 5
DRIVE_RAMDISK = 6
FILE_TYPE_UNKNOWN = 0
FILE_TYPE_DISK = 1
FILE_TYPE_CHAR = 2
FILE_TYPE_PIPE = 3
FILE_TYPE_REMOTE = 32768
NOPARITY = 0
ODDPARITY = 1
EVENPARITY = 2
MARKPARITY = 3
SPACEPARITY = 4
ONESTOPBIT = 0
ONE5STOPBITS = 1
TWOSTOPBITS = 2
CBR_110 = 110
CBR_300 = 300
CBR_600 = 600
CBR_1200 = 1200
CBR_2400 = 2400
CBR_4800 = 4800
CBR_9600 = 9600
CBR_14400 = 14400
CBR_19200 = 19200
CBR_38400 = 38400
CBR_56000 = 56000
CBR_57600 = 57600
CBR_115200 = 115200
CBR_128000 = 128000
CBR_256000 = 256000
S_QUEUEEMPTY = 0
S_THRESHOLD = 1
S_ALLTHRESHOLD = 2
S_NORMAL = 0
S_LEGATO = 1
S_STACCATO = 2
NMPWAIT_WAIT_FOREVER = -1
NMPWAIT_NOWAIT = 1
NMPWAIT_USE_DEFAULT_WAIT = 0
OF_READ = 0
OF_WRITE = 1
OF_READWRITE = 2
OF_SHARE_COMPAT = 0
OF_SHARE_EXCLUSIVE = 16
OF_SHARE_DENY_WRITE = 32
OF_SHARE_DENY_READ = 48
OF_SHARE_DENY_NONE = 64
OF_PARSE = 256
OF_DELETE = 512
OF_VERIFY = 1024
OF_CANCEL = 2048
OF_CREATE = 4096
OF_PROMPT = 8192
OF_EXIST = 16384
OF_REOPEN = 32768
OFS_MAXPATHNAME = 128
MAXINTATOM = 49152

# winbase.h
PROCESS_HEAP_REGION = 1
PROCESS_HEAP_UNCOMMITTED_RANGE = 2
PROCESS_HEAP_ENTRY_BUSY = 4
PROCESS_HEAP_ENTRY_MOVEABLE = 16
PROCESS_HEAP_ENTRY_DDESHARE = 32
SCS_32BIT_BINARY = 0
SCS_DOS_BINARY = 1
SCS_WOW_BINARY = 2
SCS_PIF_BINARY = 3
SCS_POSIX_BINARY = 4
SCS_OS216_BINARY = 5
SEM_FAILCRITICALERRORS = 1
SEM_NOGPFAULTERRORBOX = 2
SEM_NOALIGNMENTFAULTEXCEPT = 4
SEM_NOOPENFILEERRORBOX = 32768
LOCKFILE_FAIL_IMMEDIATELY = 1
LOCKFILE_EXCLUSIVE_LOCK = 2
HANDLE_FLAG_INHERIT = 1
HANDLE_FLAG_PROTECT_FROM_CLOSE = 2
HINSTANCE_ERROR = 32
GET_TAPE_MEDIA_INFORMATION = 0
GET_TAPE_DRIVE_INFORMATION = 1
SET_TAPE_MEDIA_INFORMATION = 0
SET_TAPE_DRIVE_INFORMATION = 1
FORMAT_MESSAGE_ALLOCATE_BUFFER = 256
FORMAT_MESSAGE_IGNORE_INSERTS = 512
FORMAT_MESSAGE_FROM_STRING = 1024
FORMAT_MESSAGE_FROM_HMODULE = 2048
FORMAT_MESSAGE_FROM_SYSTEM = 4096
FORMAT_MESSAGE_ARGUMENT_ARRAY = 8192
FORMAT_MESSAGE_MAX_WIDTH_MASK = 255
BACKUP_INVALID = 0
BACKUP_DATA = 1
BACKUP_EA_DATA = 2
BACKUP_SECURITY_DATA = 3
BACKUP_ALTERNATE_DATA = 4
BACKUP_LINK = 5
BACKUP_PROPERTY_DATA = 6
BACKUP_OBJECT_ID = 7
BACKUP_REPARSE_DATA = 8
BACKUP_SPARSE_BLOCK = 9

STREAM_NORMAL_ATTRIBUTE = 0
STREAM_MODIFIED_WHEN_READ = 1
STREAM_CONTAINS_SECURITY = 2
STREAM_CONTAINS_PROPERTIES = 4
STARTF_USESHOWWINDOW = 1
STARTF_USESIZE = 2
STARTF_USEPOSITION = 4
STARTF_USECOUNTCHARS = 8
STARTF_USEFILLATTRIBUTE = 16
STARTF_FORCEONFEEDBACK = 64
STARTF_FORCEOFFFEEDBACK = 128
STARTF_USESTDHANDLES = 256
STARTF_USEHOTKEY = 512
SHUTDOWN_NORETRY = 1
DONT_RESOLVE_DLL_REFERENCES = 1
LOAD_LIBRARY_AS_DATAFILE = 2
LOAD_WITH_ALTERED_SEARCH_PATH = 8
DDD_RAW_TARGET_PATH = 1
DDD_REMOVE_DEFINITION = 2
DDD_EXACT_MATCH_ON_REMOVE = 4
MOVEFILE_REPLACE_EXISTING = 1
MOVEFILE_COPY_ALLOWED = 2
MOVEFILE_DELAY_UNTIL_REBOOT = 4
MAX_COMPUTERNAME_LENGTH = 15
LOGON32_LOGON_INTERACTIVE = 2
LOGON32_LOGON_NETWORK = 3
LOGON32_LOGON_BATCH = 4
LOGON32_LOGON_SERVICE = 5
LOGON32_LOGON_UNLOCK = 7
LOGON32_LOGON_NETWORK_CLEARTEXT = 8
LOGON32_LOGON_NEW_CREDENTIALS = 9
LOGON32_PROVIDER_DEFAULT = 0
LOGON32_PROVIDER_WINNT35 = 1
LOGON32_PROVIDER_WINNT40 = 2
LOGON32_PROVIDER_WINNT50 = 3
VER_PLATFORM_WIN32s = 0
VER_PLATFORM_WIN32_WINDOWS = 1
VER_PLATFORM_WIN32_NT = 2
TC_NORMAL = 0
TC_HARDERR = 1
TC_GP_TRAP = 2
TC_SIGNAL = 3
AC_LINE_OFFLINE = 0
AC_LINE_ONLINE = 1
AC_LINE_BACKUP_POWER = 2
AC_LINE_UNKNOWN = 255
BATTERY_FLAG_HIGH = 1
BATTERY_FLAG_LOW = 2
BATTERY_FLAG_CRITICAL = 4
BATTERY_FLAG_CHARGING = 8
BATTERY_FLAG_NO_BATTERY = 128
BATTERY_FLAG_UNKNOWN = 255
BATTERY_PERCENTAGE_UNKNOWN = 255
BATTERY_LIFE_UNKNOWN = -1

# Generated by h2py from d:\msdev\include\richedit.h
cchTextLimitDefault = 32767
WM_CONTEXTMENU = 123
WM_PRINTCLIENT = 792
EN_MSGFILTER = 1792
EN_REQUESTRESIZE = 1793
EN_SELCHANGE = 1794
EN_DROPFILES = 1795
EN_PROTECTED = 1796
EN_CORRECTTEXT = 1797
EN_STOPNOUNDO = 1798
EN_IMECHANGE = 1799
EN_SAVECLIPBOARD = 1800
EN_OLEOPFAILED = 1801
ENM_NONE = 0
ENM_CHANGE = 1
ENM_UPDATE = 2
ENM_SCROLL = 4
ENM_KEYEVENTS = 65536
ENM_MOUSEEVENTS = 131072
ENM_REQUESTRESIZE = 262144
ENM_SELCHANGE = 524288
ENM_DROPFILES = 1048576
ENM_PROTECTED = 2097152
ENM_CORRECTTEXT = 4194304
ENM_IMECHANGE = 8388608
ES_SAVESEL = 32768
ES_SUNKEN = 16384
ES_DISABLENOSCROLL = 8192
ES_SELECTIONBAR = 16777216
ES_EX_NOCALLOLEINIT = 16777216
ES_VERTICAL = 4194304
ES_NOIME = 524288
ES_SELFIME = 262144
ECO_AUTOWORDSELECTION = 1
ECO_AUTOVSCROLL = 64
ECO_AUTOHSCROLL = 128
ECO_NOHIDESEL = 256
ECO_READONLY = 2048
ECO_WANTRETURN = 4096
ECO_SAVESEL = 32768
ECO_SELECTIONBAR = 16777216
ECO_VERTICAL = 4194304
ECOOP_SET = 1
ECOOP_OR = 2
ECOOP_AND = 3
ECOOP_XOR = 4
WB_CLASSIFY = 3
WB_MOVEWORDLEFT = 4
WB_MOVEWORDRIGHT = 5
WB_LEFTBREAK = 6
WB_RIGHTBREAK = 7
WB_MOVEWORDPREV = 4
WB_MOVEWORDNEXT = 5
WB_PREVBREAK = 6
WB_NEXTBREAK = 7
PC_FOLLOWING = 1
PC_LEADING = 2
PC_OVERFLOW = 3
PC_DELIMITER = 4
WBF_WORDWRAP = 16
WBF_WORDBREAK = 32
WBF_OVERFLOW = 64
WBF_LEVEL1 = 128
WBF_LEVEL2 = 256
WBF_CUSTOM = 512
CFM_BOLD = 1
CFM_ITALIC = 2
CFM_UNDERLINE = 4
CFM_STRIKEOUT = 8
CFM_PROTECTED = 16
CFM_SIZE = -2147483648
CFM_COLOR = 1073741824
CFM_FACE = 536870912
CFM_OFFSET = 268435456
CFM_CHARSET = 134217728
CFE_BOLD = 1
CFE_ITALIC = 2
CFE_UNDERLINE = 4
CFE_STRIKEOUT = 8
CFE_PROTECTED = 16
CFE_AUTOCOLOR = 1073741824
yHeightCharPtsMost = 1638
SCF_SELECTION = 1
SCF_WORD = 2
SF_TEXT = 1
SF_RTF = 2
SF_RTFNOOBJS = 3
SF_TEXTIZED = 4
SFF_SELECTION = 32768
SFF_PLAINRTF = 16384
MAX_TAB_STOPS = 32
lDefaultTab = 720
PFM_STARTINDENT = 1
PFM_RIGHTINDENT = 2
PFM_OFFSET = 4
PFM_ALIGNMENT = 8
PFM_TABSTOPS = 16
PFM_NUMBERING = 32
PFM_OFFSETINDENT = -2147483648
PFN_BULLET = 1
PFA_LEFT = 1
PFA_RIGHT = 2
PFA_CENTER = 3
WM_NOTIFY = 78
SEL_EMPTY = 0
SEL_TEXT = 1
SEL_OBJECT = 2
SEL_MULTICHAR = 4
SEL_MULTIOBJECT = 8
OLEOP_DOVERB = 1
CF_RTF = "Rich Text Format"
CF_RTFNOOBJS = "Rich Text Format Without Objects"
CF_RETEXTOBJ = "RichEdit Text and Objects"

# From wincon.h
RIGHT_ALT_PRESSED = 1  # the right alt key is pressed.
LEFT_ALT_PRESSED = 2  # the left alt key is pressed.
RIGHT_CTRL_PRESSED = 4  # the right ctrl key is pressed.
LEFT_CTRL_PRESSED = 8  # the left ctrl key is pressed.
SHIFT_PRESSED = 16  # the shift key is pressed.
NUMLOCK_ON = 32  # the numlock light is on.
SCROLLLOCK_ON = 64  # the scrolllock light is on.
CAPSLOCK_ON = 128  # the capslock light is on.
ENHANCED_KEY = 256  # the key is enhanced.
NLS_DBCSCHAR = 65536  # DBCS for JPN: SBCS/DBCS mode.
NLS_ALPHANUMERIC = 0  # DBCS for JPN: Alphanumeric mode.
NLS_KATAKANA = 131072  # DBCS for JPN: Katakana mode.
NLS_HIRAGANA = 262144  # DBCS for JPN: Hiragana mode.
NLS_ROMAN = 4194304  # DBCS for JPN: Roman/Noroman mode.
NLS_IME_CONVERSION = 8388608  # DBCS for JPN: IME conversion.
NLS_IME_DISABLE = 536870912  # DBCS for JPN: IME enable/disable.

FROM_LEFT_1ST_BUTTON_PRESSED = 1
RIGHTMOST_BUTTON_PRESSED = 2
FROM_LEFT_2ND_BUTTON_PRESSED = 4
FROM_LEFT_3RD_BUTTON_PRESSED = 8
FROM_LEFT_4TH_BUTTON_PRESSED = 16

CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2
CTRL_LOGOFF_EVENT = 5
CTRL_SHUTDOWN_EVENT = 6

MOUSE_MOVED = 1
DOUBLE_CLICK = 2
MOUSE_WHEELED = 4

# property sheet window messages from prsht.h
PSM_SETCURSEL = WM_USER + 101
PSM_REMOVEPAGE = WM_USER + 102
PSM_ADDPAGE = WM_USER + 103
PSM_CHANGED = WM_USER + 104
PSM_RESTARTWINDOWS = WM_USER + 105
PSM_REBOOTSYSTEM = WM_USER + 106
PSM_CANCELTOCLOSE = WM_USER + 107
PSM_QUERYSIBLINGS = WM_USER + 108
PSM_UNCHANGED = WM_USER + 109
PSM_APPLY = WM_USER + 110
PSM_SETTITLEA = WM_USER + 111
PSM_SETTITLEW = WM_USER + 120
PSM_SETWIZBUTTONS = WM_USER + 112
PSM_PRESSBUTTON = WM_USER + 113
PSM_SETCURSELID = WM_USER + 114
PSM_SETFINISHTEXTA = WM_USER + 115
PSM_SETFINISHTEXTW = WM_USER + 121
PSM_GETTABCONTROL = WM_USER + 116
PSM_ISDIALOGMESSAGE = WM_USER + 117
PSM_GETCURRENTPAGEHWND = WM_USER + 118
PSM_INSERTPAGE = WM_USER + 119
PSM_SETHEADERTITLEA = WM_USER + 125
PSM_SETHEADERTITLEW = WM_USER + 126
PSM_SETHEADERSUBTITLEA = WM_USER + 127
PSM_SETHEADERSUBTITLEW = WM_USER + 128
PSM_HWNDTOINDEX = WM_USER + 129
PSM_INDEXTOHWND = WM_USER + 130
PSM_PAGETOINDEX = WM_USER + 131
PSM_INDEXTOPAGE = WM_USER + 132
PSM_IDTOINDEX = WM_USER + 133
PSM_INDEXTOID = WM_USER + 134
PSM_GETRESULT = WM_USER + 135
PSM_RECALCPAGESIZES = WM_USER + 136

# GetUserNameEx/GetComputerNameEx
NameUnknown = 0
NameFullyQualifiedDN = 1
NameSamCompatible = 2
NameDisplay = 3
NameUniqueId = 6
NameCanonical = 7
NameUserPrincipal = 8
NameCanonicalEx = 9
NameServicePrincipal = 10
NameDnsDomain = 12

ComputerNameNetBIOS = 0
ComputerNameDnsHostname = 1
ComputerNameDnsDomain = 2
ComputerNameDnsFullyQualified = 3
ComputerNamePhysicalNetBIOS = 4
ComputerNamePhysicalDnsHostname = 5
ComputerNamePhysicalDnsDomain = 6
ComputerNamePhysicalDnsFullyQualified = 7

LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002
ULW_COLORKEY = 0x00000001
ULW_ALPHA = 0x00000002
ULW_OPAQUE = 0x00000004

# WinDef.h
TRUE = 1
FALSE = 0
MAX_PATH = 260
# WinGDI.h
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
GRADIENT_FILL_RECT_H = 0
GRADIENT_FILL_RECT_V = 1
GRADIENT_FILL_TRIANGLE = 2
GRADIENT_FILL_OP_FLAG = 255

## flags used with Get/SetSystemFileCacheSize
MM_WORKING_SET_MAX_HARD_ENABLE = 1
MM_WORKING_SET_MAX_HARD_DISABLE = 2
MM_WORKING_SET_MIN_HARD_ENABLE = 4
MM_WORKING_SET_MIN_HARD_DISABLE = 8

## Flags for GetFinalPathNameByHandle
VOLUME_NAME_DOS = 0
VOLUME_NAME_GUID = 1
VOLUME_NAME_NT = 2
VOLUME_NAME_NONE = 4
FILE_NAME_NORMALIZED = 0
FILE_NAME_OPENED = 8

DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000
DEVICE_NOTIFY_SERVICE_HANDLE = 0x00000001

# From Dbt.h
# Generated by h2py from Dbt.h
WM_DEVICECHANGE = 0x0219
BSF_QUERY = 0x00000001
BSF_IGNORECURRENTTASK = 0x00000002
BSF_FLUSHDISK = 0x00000004
BSF_NOHANG = 0x00000008
BSF_POSTMESSAGE = 0x00000010
BSF_FORCEIFHUNG = 0x00000020
BSF_NOTIMEOUTIFNOTHUNG = 0x00000040
BSF_MSGSRV32ISOK = -2147483648
BSF_MSGSRV32ISOK_BIT = 31
BSM_ALLCOMPONENTS = 0x00000000
BSM_VXDS = 0x00000001
BSM_NETDRIVER = 0x00000002
BSM_INSTALLABLEDRIVERS = 0x00000004
BSM_APPLICATIONS = 0x00000008
DBT_APPYBEGIN = 0x0000
DBT_APPYEND = 0x0001
DBT_DEVNODES_CHANGED = 0x0007
DBT_QUERYCHANGECONFIG = 0x0017
DBT_CONFIGCHANGED = 0x0018
DBT_CONFIGCHANGECANCELED = 0x0019
DBT_MONITORCHANGE = 0x001B
DBT_SHELLLOGGEDON = 0x0020
DBT_CONFIGMGAPI32 = 0x0022
DBT_VXDINITCOMPLETE = 0x0023
DBT_VOLLOCKQUERYLOCK = 0x8041
DBT_VOLLOCKLOCKTAKEN = 0x8042
DBT_VOLLOCKLOCKFAILED = 0x8043
DBT_VOLLOCKQUERYUNLOCK = 0x8044
DBT_VOLLOCKLOCKRELEASED = 0x8045
DBT_VOLLOCKUNLOCKFAILED = 0x8046
LOCKP_ALLOW_WRITES = 0x01
LOCKP_FAIL_WRITES = 0x00
LOCKP_FAIL_MEM_MAPPING = 0x02
LOCKP_ALLOW_MEM_MAPPING = 0x00
LOCKP_USER_MASK = 0x03
LOCKP_LOCK_FOR_FORMAT = 0x04
LOCKF_LOGICAL_LOCK = 0x00
LOCKF_PHYSICAL_LOCK = 0x01
DBT_NO_DISK_SPACE = 0x0047
DBT_LOW_DISK_SPACE = 0x0048
DBT_CONFIGMGPRIVATE = 0x7FFF
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEQUERYREMOVE = 0x8001
DBT_DEVICEQUERYREMOVEFAILED = 0x8002
DBT_DEVICEREMOVEPENDING = 0x8003
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVICETYPESPECIFIC = 0x8005
DBT_CUSTOMEVENT = 0x8006
DBT_DEVTYP_OEM = 0x00000000
DBT_DEVTYP_DEVNODE = 0x00000001
DBT_DEVTYP_VOLUME = 0x00000002
DBT_DEVTYP_PORT = 0x00000003
DBT_DEVTYP_NET = 0x00000004
DBT_DEVTYP_DEVICEINTERFACE = 0x00000005
DBT_DEVTYP_HANDLE = 0x00000006
DBTF_MEDIA = 0x0001
DBTF_NET = 0x0002
DBTF_RESOURCE = 0x00000001
DBTF_XPORT = 0x00000002
DBTF_SLOWNET = 0x00000004
DBT_VPOWERDAPI = 0x8100
DBT_USERDEFINED = 0xFFFF

# From ime_cmodes.h
# bit field for conversion mode
IME_CMODE_ALPHANUMERIC = 0x0000
IME_CMODE_NATIVE = 0x0001
IME_CMODE_CHINESE = IME_CMODE_NATIVE
IME_CMODE_HANGUL = IME_CMODE_NATIVE
IME_CMODE_JAPANESE = IME_CMODE_NATIVE
IME_CMODE_KATAKANA = 0x0002  # only effect under IME_CMODE_NATIVE
IME_CMODE_LANGUAGE = 0x0003
IME_CMODE_FULLSHAPE = 0x0008
IME_CMODE_ROMAN = 0x0010
IME_CMODE_CHARCODE = 0x0020
IME_CMODE_HANJACONVERT = 0x0040
IME_CMODE_NATIVESYMBOL = 0x0080

# === NexusCore/exported_projects\app_20250703_223016\app\routes.py ===
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product
from app.forms import ProductForm
import csv
import io
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/manage', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data,
            supplier_url=form.supplier_url.data,
            image_url=form.image_url.data,
            stock_status=form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost=form.shipping_cost.data,
            customs_duty=form.customs_duty.data,
            procurement_fee=form.procurement_fee.data
        )
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))
    products = Product.query.all()
    return render_template('products/manage.html', form=form, products=products)

@bp.route('/products/<int:id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('商品を削除しました', 'success')
    return redirect(url_for('main.manage_products'))

@bp.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('ファイルがアップロードされていません', 'error')
        return redirect(url_for('main.manage_products'))
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません', 'error')
        return redirect(url_for('main.manage_products'))
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            csv_reader = csv.DictReader(stream)
            count = 0
            for row in csv_reader:
                required_fields = ['name', 'purchase_price', 'selling_price']
                if not all(field in row for field in required_fields):
                    flash('CSVに必須項目が不足しています', 'error')
                    return redirect(url_for('main.manage_products'))
                product = Product(
                    name=row['name'],
                    brand=row.get('brand', ''),
                    purchase_price=float(row['purchase_price']),
                    selling_price=float(row['selling_price']),
                    supplier_url=row.get('supplier_url', ''),
                    image_url=row.get('image_url', ''),
                    stock_status=row.get('stock_status', 'true').lower() in ['true', '1', 'yes'],
                    transaction_fee=float(row.get('transaction_fee', 0)),
                    shipping_cost=float(row.get('shipping_cost', 0)),
                    customs_duty=float(row.get('customs_duty', 0)),
                    procurement_fee=float(row.get('procurement_fee', 0))
                )
                if hasattr(product, "calculate_profit"):
                    product.profit = product.calculate_profit()
                db.session.add(product)
                count += 1
            db.session.commit()
            flash(f'{count}件の商品をインポートしました', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'CSVインポート中にエラーが発生しました: {str(e)}', 'error')
    else:
        flash('CSVファイルのみアップロード可能です', 'error')
    return redirect(url_for('main.manage_products'))

@bp.route('/export_csv')
def export_csv():
    try:
        products = Product.query.all()
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー書き込み
        writer.writerow([
            'name', 'brand', 'purchase_price', 'selling_price',
            'transaction_fee', 'shipping_cost', 'customs_duty', 'procurement_fee',
            'supplier_url', 'image_url', 'stock_status'
        ])

        # データ書き込み
        for product in products:
            writer.writerow([
                product.name,
                product.brand,
                product.purchase_price,
                product.selling_price,
                product.transaction_fee,
                product.shipping_cost,
                product.customs_duty,
                product.procurement_fee,
                product.supplier_url,
                product.image_url,
                'true' if product.stock_status else 'false'
            ])

        output.seek(0)
        date_str = datetime.now().strftime('%Y%m%d%H%M%S')
        # 文字化け対策: BOM付きUTF-8
        bom = '\ufeff'
        csv_data = bom + output.getvalue()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment;filename=products_{date_str}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    except Exception as e:
        flash(f'CSVエクスポート中にエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('main.manage_products'))

@bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.commit()
        flash('商品情報を更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))

# === NexusCore/exported_projects\project_export_m73owrzi\app\routes.py ===
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product
from app.forms import ProductForm
import csv
import io
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/manage', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data,
            supplier_url=form.supplier_url.data,
            image_url=form.image_url.data,
            stock_status=form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost=form.shipping_cost.data,
            customs_duty=form.customs_duty.data,
            procurement_fee=form.procurement_fee.data
        )
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))
    products = Product.query.all()
    return render_template('products/manage.html', form=form, products=products)

@bp.route('/products/<int:id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('商品を削除しました', 'success')
    return redirect(url_for('main.manage_products'))

@bp.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('ファイルがアップロードされていません', 'error')
        return redirect(url_for('main.manage_products'))
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません', 'error')
        return redirect(url_for('main.manage_products'))
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            csv_reader = csv.DictReader(stream)
            count = 0
            for row in csv_reader:
                required_fields = ['name', 'purchase_price', 'selling_price']
                if not all(field in row for field in required_fields):
                    flash('CSVに必須項目が不足しています', 'error')
                    return redirect(url_for('main.manage_products'))
                product = Product(
                    name=row['name'],
                    brand=row.get('brand', ''),
                    purchase_price=float(row['purchase_price']),
                    selling_price=float(row['selling_price']),
                    supplier_url=row.get('supplier_url', ''),
                    image_url=row.get('image_url', ''),
                    stock_status=row.get('stock_status', 'true').lower() in ['true', '1', 'yes'],
                    transaction_fee=float(row.get('transaction_fee', 0)),
                    shipping_cost=float(row.get('shipping_cost', 0)),
                    customs_duty=float(row.get('customs_duty', 0)),
                    procurement_fee=float(row.get('procurement_fee', 0))
                )
                if hasattr(product, "calculate_profit"):
                    product.profit = product.calculate_profit()
                db.session.add(product)
                count += 1
            db.session.commit()
            flash(f'{count}件の商品をインポートしました', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'CSVインポート中にエラーが発生しました: {str(e)}', 'error')
    else:
        flash('CSVファイルのみアップロード可能です', 'error')
    return redirect(url_for('main.manage_products'))

@bp.route('/export_csv')
def export_csv():
    try:
        products = Product.query.all()
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー書き込み
        writer.writerow([
            'name', 'brand', 'purchase_price', 'selling_price',
            'transaction_fee', 'shipping_cost', 'customs_duty', 'procurement_fee',
            'supplier_url', 'image_url', 'stock_status'
        ])

        # データ書き込み
        for product in products:
            writer.writerow([
                product.name,
                product.brand,
                product.purchase_price,
                product.selling_price,
                product.transaction_fee,
                product.shipping_cost,
                product.customs_duty,
                product.procurement_fee,
                product.supplier_url,
                product.image_url,
                'true' if product.stock_status else 'false'
            ])

        output.seek(0)
        date_str = datetime.now().strftime('%Y%m%d%H%M%S')
        # 文字化け対策: BOM付きUTF-8
        bom = '\ufeff'
        csv_data = bom + output.getvalue()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment;filename=products_{date_str}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    except Exception as e:
        flash(f'CSVエクスポート中にエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('main.manage_products'))

@bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.commit()
        flash('商品情報を更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))

# === NexusCore/exported_projects\project_export_xb_l70t8\app\routes.py ===
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product
from app.forms import ProductForm
import csv
import io
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/manage', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data,
            supplier_url=form.supplier_url.data,
            image_url=form.image_url.data,
            stock_status=form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost=form.shipping_cost.data,
            customs_duty=form.customs_duty.data,
            procurement_fee=form.procurement_fee.data
        )
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))
    products = Product.query.all()
    return render_template('products/manage.html', form=form, products=products)

@bp.route('/products/<int:id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('商品を削除しました', 'success')
    return redirect(url_for('main.manage_products'))

@bp.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('ファイルがアップロードされていません', 'error')
        return redirect(url_for('main.manage_products'))
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません', 'error')
        return redirect(url_for('main.manage_products'))
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            csv_reader = csv.DictReader(stream)
            count = 0
            for row in csv_reader:
                required_fields = ['name', 'purchase_price', 'selling_price']
                if not all(field in row for field in required_fields):
                    flash('CSVに必須項目が不足しています', 'error')
                    return redirect(url_for('main.manage_products'))
                product = Product(
                    name=row['name'],
                    brand=row.get('brand', ''),
                    purchase_price=float(row['purchase_price']),
                    selling_price=float(row['selling_price']),
                    supplier_url=row.get('supplier_url', ''),
                    image_url=row.get('image_url', ''),
                    stock_status=row.get('stock_status', 'true').lower() in ['true', '1', 'yes'],
                    transaction_fee=float(row.get('transaction_fee', 0)),
                    shipping_cost=float(row.get('shipping_cost', 0)),
                    customs_duty=float(row.get('customs_duty', 0)),
                    procurement_fee=float(row.get('procurement_fee', 0))
                )
                if hasattr(product, "calculate_profit"):
                    product.profit = product.calculate_profit()
                db.session.add(product)
                count += 1
            db.session.commit()
            flash(f'{count}件の商品をインポートしました', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'CSVインポート中にエラーが発生しました: {str(e)}', 'error')
    else:
        flash('CSVファイルのみアップロード可能です', 'error')
    return redirect(url_for('main.manage_products'))

@bp.route('/export_csv')
def export_csv():
    try:
        products = Product.query.all()
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー書き込み
        writer.writerow([
            'name', 'brand', 'purchase_price', 'selling_price',
            'transaction_fee', 'shipping_cost', 'customs_duty', 'procurement_fee',
            'supplier_url', 'image_url', 'stock_status'
        ])

        # データ書き込み
        for product in products:
            writer.writerow([
                product.name,
                product.brand,
                product.purchase_price,
                product.selling_price,
                product.transaction_fee,
                product.shipping_cost,
                product.customs_duty,
                product.procurement_fee,
                product.supplier_url,
                product.image_url,
                'true' if product.stock_status else 'false'
            ])

        output.seek(0)
        date_str = datetime.now().strftime('%Y%m%d%H%M%S')
        # 文字化け対策: BOM付きUTF-8
        bom = '\ufeff'
        csv_data = bom + output.getvalue()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment;filename=products_{date_str}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    except Exception as e:
        flash(f'CSVエクスポート中にエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('main.manage_products'))

@bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.commit()
        flash('商品情報を更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\routes.py ===
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product
from app.forms import ProductForm
import csv
import io
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/manage', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data,
            supplier_url=form.supplier_url.data,
            image_url=form.image_url.data,
            stock_status=form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost=form.shipping_cost.data,
            customs_duty=form.customs_duty.data,
            procurement_fee=form.procurement_fee.data
        )
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))
    products = Product.query.all()
    return render_template('products/manage.html', form=form, products=products)

@bp.route('/products/<int:id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('商品を削除しました', 'success')
    return redirect(url_for('main.manage_products'))

@bp.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('ファイルがアップロードされていません', 'error')
        return redirect(url_for('main.manage_products'))
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません', 'error')
        return redirect(url_for('main.manage_products'))
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            csv_reader = csv.DictReader(stream)
            count = 0
            for row in csv_reader:
                required_fields = ['name', 'purchase_price', 'selling_price']
                if not all(field in row for field in required_fields):
                    flash('CSVに必須項目が不足しています', 'error')
                    return redirect(url_for('main.manage_products'))
                product = Product(
                    name=row['name'],
                    brand=row.get('brand', ''),
                    purchase_price=float(row['purchase_price']),
                    selling_price=float(row['selling_price']),
                    supplier_url=row.get('supplier_url', ''),
                    image_url=row.get('image_url', ''),
                    stock_status=row.get('stock_status', 'true').lower() in ['true', '1', 'yes'],
                    transaction_fee=float(row.get('transaction_fee', 0)),
                    shipping_cost=float(row.get('shipping_cost', 0)),
                    customs_duty=float(row.get('customs_duty', 0)),
                    procurement_fee=float(row.get('procurement_fee', 0))
                )
                if hasattr(product, "calculate_profit"):
                    product.profit = product.calculate_profit()
                db.session.add(product)
                count += 1
            db.session.commit()
            flash(f'{count}件の商品をインポートしました', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'CSVインポート中にエラーが発生しました: {str(e)}', 'error')
    else:
        flash('CSVファイルのみアップロード可能です', 'error')
    return redirect(url_for('main.manage_products'))

@bp.route('/export_csv')
def export_csv():
    try:
        products = Product.query.all()
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー書き込み
        writer.writerow([
            'name', 'brand', 'purchase_price', 'selling_price',
            'transaction_fee', 'shipping_cost', 'customs_duty', 'procurement_fee',
            'supplier_url', 'image_url', 'stock_status'
        ])

        # データ書き込み
        for product in products:
            writer.writerow([
                product.name,
                product.brand,
                product.purchase_price,
                product.selling_price,
                product.transaction_fee,
                product.shipping_cost,
                product.customs_duty,
                product.procurement_fee,
                product.supplier_url,
                product.image_url,
                'true' if product.stock_status else 'false'
            ])

        output.seek(0)
        date_str = datetime.now().strftime('%Y%m%d%H%M%S')
        # 文字化け対策: BOM付きUTF-8
        bom = '\ufeff'
        csv_data = bom + output.getvalue()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment;filename=products_{date_str}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    except Exception as e:
        flash(f'CSVエクスポート中にエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('main.manage_products'))

@bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.commit()
        flash('商品情報を更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))

# === NexusCore/src\opencodeinterpreter_webui.py ===
# 📁 ファイル名: opencodeinterpreter_webui.py
# 📂 フォルダ構成: /src/opencodeinterpreter_webui.py
# 🕠 目的: Gradio UIにユニットテスト生成 + 修正サイクル + テスト一括実行を統合

import gradio as gr
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from uuid import uuid4

# --- 独自モジュール ---
from code_interpreter.sandbox_runner import run_and_repair, run_test_and_repair
from utils.diff_tools import generate_diff_report, score_code_improvement
from utils.test_generator import generate_unit_tests
from utils.file_utils import (
    extract_file_content,
    handle_uploaded_files,
    file_list_display,
    extract_zip_texts,
    download_history,
)

# --- Whisper 音声認識用 ---
def process_audio(audio_file):
    try:
        if audio_file is None:
            raise gr.Warning("録音がキャンセルされました。")
        with open(audio_file, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ja",
                response_format="text"
            )
        return transcript
    except gr.Warning as w:
        raise w
    except Exception as e:
        logging.error(f"音声処理エラー: {str(e)}")
        raise gr.Error(f"音声処理エラー: {e}")

# --- Gradioユーティリティ関数 ---
def update_uuid(dialog_info):
    new_uuid = str(uuid4())
    logging.info(f"allocating new uuid {new_uuid} for conversation...")
    return [new_uuid, dialog_info[1]]

def history_to_messages(history):
    messages = []
    for msg in history:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append(msg)
        elif isinstance(msg, (list, tuple)) and len(msg) == 2:
            messages.append({"role": "user", "content": msg[0]})
            messages.append({"role": "assistant", "content": msg[1]})
    return messages

def bot(user_message, files, history, dialog_info, frontend_preview):
    try:
        if files is None:
            files = []
        file_info, file_content, file_types, frontend_preview_str = handle_uploaded_files(files)
        user_input = user_message
        if file_info:
            user_input += "\n" + file_info
        if file_content:
            user_input += f"\n[\u30d5\u30a1\u30a4\u30eb\u5185\u5bb9（4000\u6587\u5b57\u307e\u3067）]\n{file_content[:4000]}"

        prev_messages = history if history and isinstance(history[0], dict) else history_to_messages(history)
        ai_response = "ファイルまたはテキストを受け取りました。"

        chatbot_value = prev_messages + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ]
        return chatbot_value, chatbot_value, dialog_info, frontend_preview_str

    except Exception as e:
        logging.error(f"bot error: {e}")
        raise gr.Error(f"エラー: {e}")

def reset_textbox():
    return gr.update(value="")

def clear_history(history, dialog_info):
    return [], [], update_uuid(dialog_info), ""

# --- ユニットテスト生成 ---
def generate_and_show_tests(code: str) -> str:
    try:
        return generate_unit_tests(code)
    except Exception as e:
        logging.error(f"ユニットテスト生成失敗: {e}")
        return f"エラー: {e}"

# --- Gradio UI構成 ---
def gradio_launch():
    with gr.Blocks() as demo:
        with gr.Tabs():
            # タブ1: 修正・テスト
            with gr.Tab("🛠 修正サイクル"):
                code_input = gr.Textbox(label="💡 入力コード（エラーあり可）", lines=10)
                btn_testgen = gr.Button("🧪 ユニットテスト生成")
                test_output = gr.Code(label="📄 生成されたユニットテスト")
                btn_run_repair = gr.Button("🔁 修正のみ実行")
                btn_run_test_repair = gr.Button("🧪 修正+\u30c6スト一括")
                output_code = gr.Code(label="✅ 修正済みコード or レポート")

                btn_testgen.click(fn=generate_and_show_tests, inputs=code_input, outputs=test_output)
                btn_run_repair.click(fn=run_and_repair, inputs=code_input, outputs=output_code)
                btn_run_test_repair.click(fn=run_test_and_repair, inputs=code_input, outputs=output_code)

            # タブ2: チャット＋ファイル分析
            with gr.Tab("💬 Chat + ファイル分析"):
                chatbot = gr.Chatbot(label="OpenCodeInterpreter", height=600, type="messages")
                msg = gr.Textbox(placeholder="メッセージ入力 or 音声録音", scale=5)
                file_input = gr.File(file_types=[".py", ".txt", ".md", ".json", ".zip"], file_count="multiple")
                file_list = gr.Textbox(label="アップロードファイル一覧", interactive=False, max_lines=10)
                audio_input = gr.Audio(sources="microphone", type="filepath", label="音声録音")
                frontend_preview = gr.Textbox(label="ファイル先頭プレビュー（100字）")
                submit = gr.Button("Submit")
                clear = gr.Button("Clear")
                download_btn = gr.DownloadButton("履歴ダウンロード")
                session_state = gr.State([])
                dialog_info = gr.State(["", 0])

                demo.load(update_uuid, dialog_info, dialog_info)
                file_input.change(file_list_display, inputs=file_input, outputs=file_list)
                audio_input.change(process_audio, inputs=audio_input, outputs=msg)
                submit.click(bot, [msg, file_input, session_state, dialog_info, frontend_preview], [chatbot, session_state, dialog_info, frontend_preview])
                clear.click(lambda h, d: ([], [], update_uuid(d), ""), [session_state, dialog_info], [chatbot, session_state, dialog_info, frontend_preview])
                download_btn.click(download_history, [session_state], download_btn)

        demo.queue(max_size=20)
        demo.launch(share=True, inbrowser=True)

# --- 起動 ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が未設定です。.envを確認してください。")
    client = OpenAI(api_key=api_key)
    gradio_launch()

# === NexusCore/src\api\server.py ===
# ==============================================================================
# フォルダ: src/api
# ファイル名: server.py
# メモ: NexusCoreの機能を外部に公開するためのFlask APIサーバー。
#      Orchestratorの実行をバックグラウンドスレッドで処理する。
# ==============================================================================
import os
import sys
import logging
import threading
import uuid
from flask import Flask, request, jsonify

# --- パス設定 ---
# このファイルがどこから実行されても、srcフォルダ内のモジュールを見つけられるようにする
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- NexusCoreのコンポーネントをインポート ---
from src.core.orchestrator import Orchestrator
from src.agents.architect_agent import ArchitectAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.postmortem_agent import PostmortemAgent
from src.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from src.utils.config import config

# --- グローバル変数 ---
app = Flask(__name__)
tasks = {} # 実行中のタスクの状態を保存する辞書

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("nexus_api_server.log", mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def run_orchestrator_task(task_id: str, requirement: str, project_path: str, constitution: dict):
    """Orchestratorをバックグラウンドで実行するワーカー関数"""
    logger.info(f"Starting background task: {task_id}")
    tasks[task_id] = {"status": "running", "message": "Initializing agents..."}
    
    try:
        # --- AI開発チーム（エージェント群）の招集 ---
        model_name = "gemini-1.5-pro-latest" 
        api_key = config.GEMINI_API_KEY_AGENT_A
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY_AGENT_A is not set in the .env file.")

        architect = ArchitectAgent(api_key=api_key, model=model_name)
        planner = PlannerAgent(api_key=api_key, model=model_name)
        coder = CoderAgent(api_key=api_key, model=model_name)
        tester = TesterAgent(api_key=api_key, model=model_name)
        debugger = DebuggerAgent(api_key=api_key, model=model_name, project_path=project_path)
        guardian = GuardianAgent(api_key=api_key, model=model_name)
        policy_agent = PolicyAgent(api_key=api_key, model=model_name)
        postmortem_agent = PostmortemAgent(api_key=api_key, model=model_name)
        knowledge_curator_agent = KnowledgeCuratorAgent(api_key=api_key, model=model_name)

        # --- 司令塔 (Orchestrator) の任命 ---
        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            architect=architect,
            planner=planner,
            coder=coder,
            tester=tester,
            debugger=debugger,
            guardian=guardian,
            policy_agent=policy_agent,
            postmortem_agent=postmortem_agent,
            knowledge_curator_agent=knowledge_curator_agent
        )

        # --- 開発プロセスの開始 ---
        tasks[task_id]["message"] = "Design phase started."
        orchestrator.design_phase(requirement)
        
        tasks[task_id]["message"] = "Development cycle started."
        orchestrator.development_cycle(requirement)
        
        tasks[task_id] = {"status": "completed", "message": "Development process finished successfully."}
        logger.info(f"Task {task_id} completed successfully.")

    except Exception as e:
        logger.critical(f"An error occurred in task {task_id}: {e}", exc_info=True)
        tasks[task_id] = {"status": "error", "message": str(e)}

@app.route('/api/v1/execute', methods=['POST'])
def execute_task():
    """新しい開発タスクを開始するAPIエンドポイント"""
    data = request.json
    if not data or 'requirement' not in data or 'project_path' not in data:
        return jsonify({"error": "Missing 'requirement' or 'project_path' in request body"}), 400

    task_id = str(uuid.uuid4())
    requirement = data['requirement']
    project_path = os.path.abspath(data['project_path'])
    
    # プロジェクト憲法を定義 (将来的にはリクエストから受け取ることも可能)
    constitution = {
        "description": data.get("constitution_text", "Default constitution: write clean, maintainable code."),
        "quality_gate": {
            "MIN_COVERAGE": 90,
            "MIN_PYLINT_SCORE": 8.0
        }
    }

    # バックグラウンドでOrchestratorを実行
    thread = threading.Thread(
        target=run_orchestrator_task,
        args=(task_id, requirement, project_path, constitution)
    )
    thread.daemon = True
    thread.start()

    logger.info(f"Task {task_id} created for requirement: '{requirement}'")
    
    return jsonify({
        "message": "Task accepted and is running in the background.",
        "task_id": task_id,
        "status_url": f"/api/v1/status/{task_id}"
    }), 202

@app.route('/api/v1/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """タスクの現在の状態を返すAPIエンドポイント"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

if __name__ == '__main__':
    logger.info("Starting NexusCore API Server...")
    app.run(host='0.0.0.0', port=5001, debug=True)

# === NexusCore/src\gradio_app\revision_loop.py ===
# OpenCodeInterpreter 拡張：反復AI修正ループ・バージョン管理付きGradioアプリ

import gradio as gr
import os
import json
import re
import subprocess
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# === 設定と初期化 ===
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === パス設定 ===
SANDBOX_DIR = "../sandbox_output"
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")
RESULT_LOG = os.path.join(SANDBOX_DIR, "test_result.log")
HISTORY_DIR = "patch_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

# === ファイル保存 ===
def save_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# === テスト実行 ===
def run_pytest():
    try:
        result = subprocess.run(
            ["pytest", TEST_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout + "\n" + result.stderr
        save_file(RESULT_LOG, output)
        return output
    except Exception as e:
        return f"⚠️ pytest execution failed: {e}"

# === GPTプロンプト生成 ===
def generate_prompt(main_file, related_files, version_summary, history_summary, failed_tests, user_instruction):
    return f"""
【前提】
- 対象ファイル: {main_file}
- 関連ファイル・依存関係: {related_files}
- 現在のバージョン: {version_summary}
- 修正履歴: {history_summary}
- 直近のテスト失敗内容: {failed_tests}
- ユーザーからの追加指示: {user_instruction}

【タスク】
1. 上記情報をもとに、{main_file}の修正版を提案してください。
2. 修正内容の要約と、なぜその修正が必要かを簡潔に説明してください。
3. 依存ファイルや関連箇所に問題があれば、修正案に含めてください。
4. テストが通らない場合は、失敗理由・考えられる原因・追加で見直すべき点を解説してください。
5. 修正案は必ず「コードブロック」で出力し、説明文と分けてください。

【出力フォーマット例】
---
【修正版コード】
ここに修正版コード

【修正理由・要約】
- 主な修正点:
- 修正が必要な理由:
- 依存関係の見直し点:
- テスト失敗時の考察:
---
"""

# === GPT呼び出しとコード抽出 ===
def extract_code_and_reason(full_response):
    code_match = re.search(r"```(?:python)?\n(.*?)```", full_response, re.DOTALL)
    reason_match = re.split(r"```.*?```", full_response, maxsplit=1)
    code = code_match.group(1).strip() if code_match else ""
    reason = reason_match[1].strip() if len(reason_match) > 1 else ""
    return code, reason

def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# === 履歴保存 ===
def save_patch_history(code, reason, prompt):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {
        "timestamp": now,
        "code": code,
        "reason": reason,
        "prompt": prompt,
        "test_log": read_file(RESULT_LOG) if os.path.exists(RESULT_LOG) else ""
    }
    save_file(os.path.join(HISTORY_DIR, f"patch_{now}.json"), json.dumps(data, indent=2, ensure_ascii=False))

# === Gradio UI ===
with gr.Blocks() as demo:
    gr.Markdown("## 🛠 安全・納得・AIアシスト型修正フロー")

    code_input = gr.Code(label="📝 修正対象コード", language="python")
    user_instruction = gr.Textbox(label="🧠 ユーザーからの追加指示")
    test_failures = gr.Textbox(label="❌ 直近のテスト失敗ログ", lines=5)

    generated_code = gr.Code(label="✅ 修正版コード", language="python")
    explanation = gr.Textbox(label="📄 修正理由・要約")
    test_result = gr.Textbox(label="🧪 pytest実行結果", lines=10)

    approve_btn = gr.Button("✅ 承認して上書き")
    revise_btn = gr.Button("🔁 AI修正案を再生成")

    def generate_revision(user_code, user_note, fail_log):
        version_summary = "現行バージョンはユーザー入力の内容"
        history = "履歴は直近の1回のみ"
        prompt = generate_prompt("sample.py", "test_sample.py", version_summary, history, fail_log, user_note)
        gpt_response = call_gpt(prompt)
        code, reason = extract_code_and_reason(gpt_response)
        return code, reason, prompt

    def apply_patch(generated_code, reason, prompt):
        save_file(SAMPLE_FILE, generated_code)
        save_patch_history(generated_code, reason, prompt)
        result = run_pytest()
        return result

    revise_btn.click(fn=generate_revision, inputs=[code_input, user_instruction, test_failures], outputs=[generated_code, explanation, user_instruction])
    approve_btn.click(fn=apply_patch, inputs=[generated_code, explanation, user_instruction], outputs=[test_result])

if __name__ == "__main__":
    demo.launch()
def launch_revision_ui():
    with gr.Row():
        # ここに反復AI修正ループの UI を構成
        gr.Markdown("### 🔁 反復AI修正ループ & バージョン管理")
        # 元の Blocks の中身をここにコピーしてください（demo = gr.Blocks() の中身だけ）

# === NexusCore/healing_sandbox\src\agents\patch_applier.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: patch_applier.py
# メモ: 内部ロジックを簡素化し、OS標準の`patch`コマンドを直接呼び出すことで
#      信頼性と堅牢性を向上させた最終バージョン。
# ==============================================================================
import logging
import os
import shutil
import subprocess
import tempfile
import re

class PatchApplier:
    """
    'unified diff' 形式のパッチをソースコードファイルに適用するためのクラス。
    DebuggerAgentによって生成されたパッチを解釈し、対象ファイルを安全に更新する。
    """

    def apply(self, patch_str: str, target_file_path: str) -> bool:
        """
        指定されたファイルにパッチを適用します。

        Args:
            patch_str (str): unified diff形式のパッチ文字列。
            target_file_path (str): パッチを適用するファイルのパス。

        Returns:
            bool: パッチの適用が成功した場合はTrue、失敗した場合はFalse。
        """
        if not patch_str:
            logging.warning("Patch is empty. Nothing to apply.")
            return False

        if not os.path.exists(target_file_path):
            logging.error(f"Target file not found: {target_file_path}")
            return False

        # `patch` コマンドラインツールが利用可能かチェック
        if shutil.which("patch"):
            logging.info("Found 'patch' command. Using the standard system tool for reliability.")
            return self._apply_with_patch_command(patch_str, target_file_path)
        else:
            logging.warning("'patch' command not found. Attempting to apply patch using a built-in Python method. This is less robust for complex patches but avoids external dependencies.")
            return self._apply_with_python_fallback(patch_str, target_file_path)

    def _apply_with_patch_command(self, patch_str: str, target_file_path: str) -> bool:
        """
        `patch` コマンドを使用してパッチを適用します。最も信頼性の高い方法です。
        """
        try:
            # パッチ文字列を一時ファイルに書き込む
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.patch', encoding='utf-8', newline='\n') as patch_file:
                patch_file.write(patch_str)
                patch_filename = patch_file.name

            # patchコマンドを実行
            result = subprocess.run(
                ['patch', '-u', target_file_path, '-i', patch_filename],
                capture_output=True, text=True, encoding='utf-8', errors='replace'
            )

            # 一時ファイルを削除
            os.unlink(patch_filename)

            if result.returncode == 0:
                logging.info(f"Successfully applied patch to {target_file_path} using 'patch' command.")
                return True
            else:
                # パッチ適用失敗時のエラーログを詳細に出力
                logging.error(f"Failed to apply patch using 'patch' command. Stderr:\n{result.stderr}")
                return False
        except Exception as e:
            logging.error(f"An error occurred while using 'patch' command: {e}", exc_info=True)
            return False

    def _apply_with_python_fallback(self, patch_str: str, target_file_path: str) -> bool:
        """
        `patch`コマンドが見つからない場合の、Pythonのみでパッチ適用を試みるフォールバック。
        """
        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            patch_lines = patch_str.splitlines(True)
            patched_lines = []
            original_idx = 0
            patch_idx = 0

            # ヘッダーをスキップ
            while patch_idx < len(patch_lines) and not patch_lines[patch_idx].startswith('@@'):
                patch_idx += 1

            if patch_idx >= len(patch_lines):
                logging.error("Patch does not contain any hunk headers ('@@').")
                return False

            # ハンク（変更箇所）を処理
            while patch_idx < len(patch_lines):
                if not patch_lines[patch_idx].startswith('@@'):
                    patch_idx += 1
                    continue
                
                hunk_header = patch_lines[patch_idx]
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', hunk_header)
                if not match:
                    logging.error(f"Could not parse hunk header: {hunk_header.strip()}")
                    return False
                
                old_start = int(match.group(1))
                
                # ハンクの前の行を元のファイルからコピー
                patched_lines.extend(original_lines[original_idx : old_start - 1])
                original_idx = old_start - 1
                patch_idx += 1

                # ハンク内の行を適用
                while patch_idx < len(patch_lines) and not patch_lines[patch_idx].startswith('@@'):
                    line = patch_lines[patch_idx]
                    if line.startswith('+'):
                        patched_lines.append(line[1:])
                    elif line.startswith('-'):
                        original_idx += 1 # 元のファイルの行をスキップ
                    elif line.startswith(' '):
                        if original_idx < len(original_lines):
                            patched_lines.append(original_lines[original_idx])
                        else: # 元のファイルに行がない場合は、パッチのコンテキスト行をそのまま使う
                            patched_lines.append(line[1:])
                        original_idx += 1
                    patch_idx += 1
            
            # 残りの行を元のファイルからコピー
            patched_lines.extend(original_lines[original_idx:])

            # 変更後の内容をファイルに書き戻す
            with open(target_file_path, 'w', encoding='utf-8', newline='') as f:
                f.writelines(patched_lines)

            return True
        except Exception as e:
            logging.error(f"Python fallback patch applicator failed: {e}", exc_info=True)
            return False

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_function_base.py ===
import decimal
import math
import operator
import sys
import warnings
from fractions import Fraction
from functools import partial

import hypothesis
import hypothesis.strategies as st
import pytest
from hypothesis.extra.numpy import arrays

import numpy as np
import numpy.lib._function_base_impl as nfb
from numpy import (
    angle,
    average,
    bartlett,
    blackman,
    corrcoef,
    cov,
    delete,
    diff,
    digitize,
    extract,
    flipud,
    gradient,
    hamming,
    hanning,
    i0,
    insert,
    interp,
    kaiser,
    ma,
    meshgrid,
    piecewise,
    place,
    rot90,
    select,
    setxor1d,
    sinc,
    trapezoid,
    trim_zeros,
    unique,
    unwrap,
    vectorize,
)
from numpy._core.numeric import normalize_axis_tuple
from numpy.exceptions import AxisError
from numpy.random import rand
from numpy.testing import (
    HAS_REFCOUNT,
    IS_WASM,
    NOGIL_BUILD,
    assert_,
    assert_allclose,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
    assert_warns,
    suppress_warnings,
)


def get_mat(n):
    data = np.arange(n)
    data = np.add.outer(data, data)
    return data


def _make_complex(real, imag):
    """
    Like real + 1j * imag, but behaves as expected when imag contains non-finite
    values
    """
    ret = np.zeros(np.broadcast(real, imag).shape, np.complex128)
    ret.real = real
    ret.imag = imag
    return ret


class TestRot90:
    def test_basic(self):
        assert_raises(ValueError, rot90, np.ones(4))
        assert_raises(ValueError, rot90, np.ones((2, 2, 2)), axes=(0, 1, 2))
        assert_raises(ValueError, rot90, np.ones((2, 2)), axes=(0, 2))
        assert_raises(ValueError, rot90, np.ones((2, 2)), axes=(1, 1))
        assert_raises(ValueError, rot90, np.ones((2, 2, 2)), axes=(-2, 1))

        a = [[0, 1, 2],
             [3, 4, 5]]
        b1 = [[2, 5],
              [1, 4],
              [0, 3]]
        b2 = [[5, 4, 3],
              [2, 1, 0]]
        b3 = [[3, 0],
              [4, 1],
              [5, 2]]
        b4 = [[0, 1, 2],
              [3, 4, 5]]

        for k in range(-3, 13, 4):
            assert_equal(rot90(a, k=k), b1)
        for k in range(-2, 13, 4):
            assert_equal(rot90(a, k=k), b2)
        for k in range(-1, 13, 4):
            assert_equal(rot90(a, k=k), b3)
        for k in range(0, 13, 4):
            assert_equal(rot90(a, k=k), b4)

        assert_equal(rot90(rot90(a, axes=(0, 1)), axes=(1, 0)), a)
        assert_equal(rot90(a, k=1, axes=(1, 0)), rot90(a, k=-1, axes=(0, 1)))

    def test_axes(self):
        a = np.ones((50, 40, 3))
        assert_equal(rot90(a).shape, (40, 50, 3))
        assert_equal(rot90(a, axes=(0, 2)), rot90(a, axes=(0, -1)))
        assert_equal(rot90(a, axes=(1, 2)), rot90(a, axes=(-2, -1)))

    def test_rotation_axes(self):
        a = np.arange(8).reshape((2, 2, 2))

        a_rot90_01 = [[[2, 3],
                       [6, 7]],
                      [[0, 1],
                       [4, 5]]]
        a_rot90_12 = [[[1, 3],
                       [0, 2]],
                      [[5, 7],
                       [4, 6]]]
        a_rot90_20 = [[[4, 0],
                       [6, 2]],
                      [[5, 1],
                       [7, 3]]]
        a_rot90_10 = [[[4, 5],
                       [0, 1]],
                      [[6, 7],
                       [2, 3]]]

        assert_equal(rot90(a, axes=(0, 1)), a_rot90_01)
        assert_equal(rot90(a, axes=(1, 0)), a_rot90_10)
        assert_equal(rot90(a, axes=(1, 2)), a_rot90_12)

        for k in range(1, 5):
            assert_equal(rot90(a, k=k, axes=(2, 0)),
                         rot90(a_rot90_20, k=k - 1, axes=(2, 0)))


class TestFlip:

    def test_axes(self):
        assert_raises(AxisError, np.flip, np.ones(4), axis=1)
        assert_raises(AxisError, np.flip, np.ones((4, 4)), axis=2)
        assert_raises(AxisError, np.flip, np.ones((4, 4)), axis=-3)
        assert_raises(AxisError, np.flip, np.ones((4, 4)), axis=(0, 3))

    def test_basic_lr(self):
        a = get_mat(4)
        b = a[:, ::-1]
        assert_equal(np.flip(a, 1), b)
        a = [[0, 1, 2],
             [3, 4, 5]]
        b = [[2, 1, 0],
             [5, 4, 3]]
        assert_equal(np.flip(a, 1), b)

    def test_basic_ud(self):
        a = get_mat(4)
        b = a[::-1, :]
        assert_equal(np.flip(a, 0), b)
        a = [[0, 1, 2],
             [3, 4, 5]]
        b = [[3, 4, 5],
             [0, 1, 2]]
        assert_equal(np.flip(a, 0), b)

    def test_3d_swap_axis0(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        b = np.array([[[4, 5],
                       [6, 7]],
                      [[0, 1],
                       [2, 3]]])

        assert_equal(np.flip(a, 0), b)

    def test_3d_swap_axis1(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        b = np.array([[[2, 3],
                       [0, 1]],
                      [[6, 7],
                       [4, 5]]])

        assert_equal(np.flip(a, 1), b)

    def test_3d_swap_axis2(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        b = np.array([[[1, 0],
                       [3, 2]],
                      [[5, 4],
                       [7, 6]]])

        assert_equal(np.flip(a, 2), b)

    def test_4d(self):
        a = np.arange(2 * 3 * 4 * 5).reshape(2, 3, 4, 5)
        for i in range(a.ndim):
            assert_equal(np.flip(a, i),
                         np.flipud(a.swapaxes(0, i)).swapaxes(i, 0))

    def test_default_axis(self):
        a = np.array([[1, 2, 3],
                      [4, 5, 6]])
        b = np.array([[6, 5, 4],
                      [3, 2, 1]])
        assert_equal(np.flip(a), b)

    def test_multiple_axes(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        assert_equal(np.flip(a, axis=()), a)

        b = np.array([[[5, 4],
                       [7, 6]],
                      [[1, 0],
                       [3, 2]]])

        assert_equal(np.flip(a, axis=(0, 2)), b)

        c = np.array([[[3, 2],
                       [1, 0]],
                      [[7, 6],
                       [5, 4]]])

        assert_equal(np.flip(a, axis=(1, 2)), c)


class TestAny:

    def test_basic(self):
        y1 = [0, 0, 1, 0]
        y2 = [0, 0, 0, 0]
        y3 = [1, 0, 1, 0]
        assert_(np.any(y1))
        assert_(np.any(y3))
        assert_(not np.any(y2))

    def test_nd(self):
        y1 = [[0, 0, 0], [0, 1, 0], [1, 1, 0]]
        assert_(np.any(y1))
        assert_array_equal(np.any(y1, axis=0), [1, 1, 0])
        assert_array_equal(np.any(y1, axis=1), [0, 1, 1])


class TestAll:

    def test_basic(self):
        y1 = [0, 1, 1, 0]
        y2 = [0, 0, 0, 0]
        y3 = [1, 1, 1, 1]
        assert_(not np.all(y1))
        assert_(np.all(y3))
        assert_(not np.all(y2))
        assert_(np.all(~np.array(y2)))

    def test_nd(self):
        y1 = [[0, 0, 1], [0, 1, 1], [1, 1, 1]]
        assert_(not np.all(y1))
        assert_array_equal(np.all(y1, axis=0), [0, 0, 1])
        assert_array_equal(np.all(y1, axis=1), [0, 0, 1])


@pytest.mark.parametrize("dtype", ["i8", "U10", "object", "datetime64[ms]"])
def test_any_and_all_result_dtype(dtype):
    arr = np.ones(3, dtype=dtype)
    assert np.any(arr).dtype == np.bool
    assert np.all(arr).dtype == np.bool


class TestCopy:

    def test_basic(self):
        a = np.array([[1, 2], [3, 4]])
        a_copy = np.copy(a)
        assert_array_equal(a, a_copy)
        a_copy[0, 0] = 10
        assert_equal(a[0, 0], 1)
        assert_equal(a_copy[0, 0], 10)

    def test_order(self):
        # It turns out that people rely on np.copy() preserving order by
        # default; changing this broke scikit-learn:
        # github.com/scikit-learn/scikit-learn/commit/7842748cf777412c506a8c0ed28090711d3a3783
        a = np.array([[1, 2], [3, 4]])
        assert_(a.flags.c_contiguous)
        assert_(not a.flags.f_contiguous)
        a_fort = np.array([[1, 2], [3, 4]], order="F")
        assert_(not a_fort.flags.c_contiguous)
        assert_(a_fort.flags.f_contiguous)
        a_copy = np.copy(a)
        assert_(a_copy.flags.c_contiguous)
        assert_(not a_copy.flags.f_contiguous)
        a_fort_copy = np.copy(a_fort)
        assert_(not a_fort_copy.flags.c_contiguous)
        assert_(a_fort_copy.flags.f_contiguous)

    def test_subok(self):
        mx = ma.ones(5)
        assert_(not ma.isMaskedArray(np.copy(mx, subok=False)))
        assert_(ma.isMaskedArray(np.copy(mx, subok=True)))
        # Default behavior
        assert_(not ma.isMaskedArray(np.copy(mx)))


class TestAverage:

    def test_basic(self):
        y1 = np.array([1, 2, 3])
        assert_(average(y1, axis=0) == 2.)
        y2 = np.array([1., 2., 3.])
        assert_(average(y2, axis=0) == 2.)
        y3 = [0., 0., 0.]
        assert_(average(y3, axis=0) == 0.)

        y4 = np.ones((4, 4))
        y4[0, 1] = 0
        y4[1, 0] = 2
        assert_almost_equal(y4.mean(0), average(y4, 0))
        assert_almost_equal(y4.mean(1), average(y4, 1))

        y5 = rand(5, 5)
        assert_almost_equal(y5.mean(0), average(y5, 0))
        assert_almost_equal(y5.mean(1), average(y5, 1))

    @pytest.mark.parametrize(
        'x, axis, expected_avg, weights, expected_wavg, expected_wsum',
        [([1, 2, 3], None, [2.0], [3, 4, 1], [1.75], [8.0]),
         ([[1, 2, 5], [1, 6, 11]], 0, [[1.0, 4.0, 8.0]],
          [1, 3], [[1.0, 5.0, 9.5]], [[4, 4, 4]])],
    )
    def test_basic_keepdims(self, x, axis, expected_avg,
                            weights, expected_wavg, expected_wsum):
        avg = np.average(x, axis=axis, keepdims=True)
        assert avg.shape == np.shape(expected_avg)
        assert_array_equal(avg, expected_avg)

        wavg = np.average(x, axis=axis, weights=weights, keepdims=True)
        assert wavg.shape == np.shape(expected_wavg)
        assert_array_equal(wavg, expected_wavg)

        wavg, wsum = np.average(x, axis=axis, weights=weights, returned=True,
                                keepdims=True)
        assert wavg.shape == np.shape(expected_wavg)
        assert_array_equal(wavg, expected_wavg)
        assert wsum.shape == np.shape(expected_wsum)
        assert_array_equal(wsum, expected_wsum)

    def test_weights(self):
        y = np.arange(10)
        w = np.arange(10)
        actual = average(y, weights=w)
        desired = (np.arange(10) ** 2).sum() * 1. / np.arange(10).sum()
        assert_almost_equal(actual, desired)

        y1 = np.array([[1, 2, 3], [4, 5, 6]])
        w0 = [1, 2]
        actual = average(y1, weights=w0, axis=0)
        desired = np.array([3., 4., 5.])
        assert_almost_equal(actual, desired)

        w1 = [0, 0, 1]
        actual = average(y1, weights=w1, axis=1)
        desired = np.array([3., 6.])
        assert_almost_equal(actual, desired)

        # weights and input have different shapes but no axis is specified
        with pytest.raises(
                TypeError,
                match="Axis must be specified when shapes of a "
                      "and weights differ"):
            average(y1, weights=w1)

        # 2D Case
        w2 = [[0, 0, 1], [0, 0, 2]]
        desired = np.array([3., 6.])
        assert_array_equal(average(y1, weights=w2, axis=1), desired)
        assert_equal(average(y1, weights=w2), 5.)

        y3 = rand(5).astype(np.float32)
        w3 = rand(5).astype(np.float64)

        assert_(np.average(y3, weights=w3).dtype == np.result_type(y3, w3))

        # test weights with `keepdims=False` and `keepdims=True`
        x = np.array([2, 3, 4]).reshape(3, 1)
        w = np.array([4, 5, 6]).reshape(3, 1)

        actual = np.average(x, weights=w, axis=1, keepdims=False)
        desired = np.array([2., 3., 4.])
        assert_array_equal(actual, desired)

        actual = np.average(x, weights=w, axis=1, keepdims=True)
        desired = np.array([[2.], [3.], [4.]])
        assert_array_equal(actual, desired)

    def test_weight_and_input_dims_different(self):
        y = np.arange(12).reshape(2, 2, 3)
        w = np.array([0., 0., 1., .5, .5, 0., 0., .5, .5, 1., 0., 0.])\
            .reshape(2, 2, 3)

        subw0 = w[:, :, 0]
        actual = average(y, axis=(0, 1), weights=subw0)
        desired = np.array([7., 8., 9.])
        assert_almost_equal(actual, desired)

        subw1 = w[1, :, :]
        actual = average(y, axis=(1, 2), weights=subw1)
        desired = np.array([2.25, 8.25])
        assert_almost_equal(actual, desired)

        subw2 = w[:, 0, :]
        actual = average(y, axis=(0, 2), weights=subw2)
        desired = np.array([4.75, 7.75])
        assert_almost_equal(actual, desired)

        # here the weights have the wrong shape for the specified axes
        with pytest.raises(
                ValueError,
                match="Shape of weights must be consistent with "
                      "shape of a along specified axis"):
            average(y, axis=(0, 1, 2), weights=subw0)

        with pytest.raises(
                ValueError,
                match="Shape of weights must be consistent with "
                      "shape of a along specified axis"):
            average(y, axis=(0, 1), weights=subw1)

        # swapping the axes should be same as transposing weights
        actual = average(y, axis=(1, 0), weights=subw0)
        desired = average(y, axis=(0, 1), weights=subw0.T)
        assert_almost_equal(actual, desired)

        # if average over all axes, should have float output
        actual = average(y, axis=(0, 1, 2), weights=w)
        assert_(actual.ndim == 0)

    def test_returned(self):
        y = np.array([[1, 2, 3], [4, 5, 6]])

        # No weights
        avg, scl = average(y, returned=True)
        assert_equal(scl, 6.)

        avg, scl = average(y, 0, returned=True)
        assert_array_equal(scl, np.array([2., 2., 2.]))

        avg, scl = average(y, 1, returned=True)
        assert_array_equal(scl, np.array([3., 3.]))

        # With weights
        w0 = [1, 2]
        avg, scl = average(y, weights=w0, axis=0, returned=True)
        assert_array_equal(scl, np.array([3., 3., 3.]))

        w1 = [1, 2, 3]
        avg, scl = average(y, weights=w1, axis=1, returned=True)
        assert_array_equal(scl, np.array([6., 6.]))

        w2 = [[0, 0, 1], [1, 2, 3]]
        avg, scl = average(y, weights=w2, axis=1, returned=True)
        assert_array_equal(scl, np.array([1., 6.]))

    def test_subclasses(self):
        class subclass(np.ndarray):
            pass
        a = np.array([[1, 2], [3, 4]]).view(subclass)
        w = np.array([[1, 2], [3, 4]]).view(subclass)

        assert_equal(type(np.average(a)), subclass)
        assert_equal(type(np.average(a, weights=w)), subclass)

    def test_upcasting(self):
        typs = [('i4', 'i4', 'f8'), ('i4', 'f4', 'f8'), ('f4', 'i4', 'f8'),
                 ('f4', 'f4', 'f4'), ('f4', 'f8', 'f8')]
        for at, wt, rt in typs:
            a = np.array([[1, 2], [3, 4]], dtype=at)
            w = np.array([[1, 2], [3, 4]], dtype=wt)
            assert_equal(np.average(a, weights=w).dtype, np.dtype(rt))

    def test_object_dtype(self):
        a = np.array([decimal.Decimal(x) for x in range(10)])
        w = np.array([decimal.Decimal(1) for _ in range(10)])
        w /= w.sum()
        assert_almost_equal(a.mean(0), average(a, weights=w))

    def test_object_no_weights(self):
        a = np.array([decimal.Decimal(x) for x in range(10)])
        m = average(a)
        assert m == decimal.Decimal('4.5')

    def test_average_class_without_dtype(self):
        # see gh-21988
        a = np.array([Fraction(1, 5), Fraction(3, 5)])
        assert_equal(np.average(a), Fraction(2, 5))


class TestSelect:
    choices = [np.array([1, 2, 3]),
               np.array([4, 5, 6]),
               np.array([7, 8, 9])]
    conditions = [np.array([False, False, False]),
                  np.array([False, True, False]),
                  np.array([False, False, True])]

    def _select(self, cond, values, default=0):
        output = []
        for m in range(len(cond)):
            output += [V[m] for V, C in zip(values, cond) if C[m]] or [default]
        return output

    def test_basic(self):
        choices = self.choices
        conditions = self.conditions
        assert_array_equal(select(conditions, choices, default=15),
                           self._select(conditions, choices, default=15))

        assert_equal(len(choices), 3)
        assert_equal(len(conditions), 3)

    def test_broadcasting(self):
        conditions = [np.array(True), np.array([False, True, False])]
        choices = [1, np.arange(12).reshape(4, 3)]
        assert_array_equal(select(conditions, choices), np.ones((4, 3)))
        # default can broadcast too:
        assert_equal(select([True], [0], default=[0]).shape, (1,))

    def test_return_dtype(self):
        assert_equal(select(self.conditions, self.choices, 1j).dtype,
                     np.complex128)
        # But the conditions need to be stronger then the scalar default
        # if it is scalar.
        choices = [choice.astype(np.int8) for choice in self.choices]
        assert_equal(select(self.conditions, choices).dtype, np.int8)

        d = np.array([1, 2, 3, np.nan, 5, 7])
        m = np.isnan(d)
        assert_equal(select([m], [d]), [0, 0, 0, np.nan, 0, 0])

    def test_deprecated_empty(self):
        assert_raises(ValueError, select, [], [], 3j)
        assert_raises(ValueError, select, [], [])

    def test_non_bool_deprecation(self):
        choices = self.choices
        conditions = self.conditions[:]
        conditions[0] = conditions[0].astype(np.int_)
        assert_raises(TypeError, select, conditions, choices)
        conditions[0] = conditions[0].astype(np.uint8)
        assert_raises(TypeError, select, conditions, choices)
        assert_raises(TypeError, select, conditions, choices)

    def test_many_arguments(self):
        # This used to be limited by NPY_MAXARGS == 32
        conditions = [np.array([False])] * 100
        choices = [np.array([1])] * 100
        select(conditions, choices)


class TestInsert:

    def test_basic(self):
        a = [1, 2, 3]
        assert_equal(insert(a, 0, 1), [1, 1, 2, 3])
        assert_equal(insert(a, 3, 1), [1, 2, 3, 1])
        assert_equal(insert(a, [1, 1, 1], [1, 2, 3]), [1, 1, 2, 3, 2, 3])
        assert_equal(insert(a, 1, [1, 2, 3]), [1, 1, 2, 3, 2, 3])
        assert_equal(insert(a, [1, -1, 3], 9), [1, 9, 2, 9, 3, 9])
        assert_equal(insert(a, slice(-1, None, -1), 9), [9, 1, 9, 2, 9, 3])
        assert_equal(insert(a, [-1, 1, 3], [7, 8, 9]), [1, 8, 2, 7, 3, 9])
        b = np.array([0, 1], dtype=np.float64)
        assert_equal(insert(b, 0, b[0]), [0., 0., 1.])
        assert_equal(insert(b, [], []), b)
        assert_equal(insert(a, np.array([True] * 4), 9), [9, 1, 9, 2, 9, 3, 9])
        assert_equal(insert(a, np.array([True, False, True, False]), 9),
                     [9, 1, 2, 9, 3])

    def test_multidim(self):
        a = [[1, 1, 1]]
        r = [[2, 2, 2],
             [1, 1, 1]]
        assert_equal(insert(a, 0, [1]), [1, 1, 1, 1])
        assert_equal(insert(a, 0, [2, 2, 2], axis=0), r)
        assert_equal(insert(a, 0, 2, axis=0), r)
        assert_equal(insert(a, 2, 2, axis=1), [[1, 1, 2, 1]])

        a = np.array([[1, 1], [2, 2], [3, 3]])
        b = np.arange(1, 4).repeat(3).reshape(3, 3)
        c = np.concatenate(
            (a[:, 0:1], np.arange(1, 4).repeat(3).reshape(3, 3).T,
             a[:, 1:2]), axis=1)
        assert_equal(insert(a, [1], [[1], [2], [3]], axis=1), b)
        assert_equal(insert(a, [1], [1, 2, 3], axis=1), c)
        # scalars behave differently, in this case exactly opposite:
        assert_equal(insert(a, 1, [1, 2, 3], axis=1), b)
        assert_equal(insert(a, 1, [[1], [2], [3]], axis=1), c)

        a = np.arange(4).reshape(2, 2)
        assert_equal(insert(a[:, :1], 1, a[:, 1], axis=1), a)
        assert_equal(insert(a[:1, :], 1, a[1, :], axis=0), a)

        # negative axis value
        a = np.arange(24).reshape((2, 3, 4))
        assert_equal(insert(a, 1, a[:, :, 3], axis=-1),
                     insert(a, 1, a[:, :, 3], axis=2))
        assert_equal(insert(a, 1, a[:, 2, :], axis=-2),
                     insert(a, 1, a[:, 2, :], axis=1))

        # invalid axis value
        assert_raises(AxisError, insert, a, 1, a[:, 2, :], axis=3)
        assert_raises(AxisError, insert, a, 1, a[:, 2, :], axis=-4)

        # negative axis value
        a = np.arange(24).reshape((2, 3, 4))
        assert_equal(insert(a, 1, a[:, :, 3], axis=-1),
                     insert(a, 1, a[:, :, 3], axis=2))
        assert_equal(insert(a, 1, a[:, 2, :], axis=-2),
                     insert(a, 1, a[:, 2, :], axis=1))

    def test_0d(self):
        a = np.array(1)
        with pytest.raises(AxisError):
            insert(a, [], 2, axis=0)
        with pytest.raises(TypeError):
            insert(a, [], 2, axis="nonsense")

    def test_subclass(self):
        class SubClass(np.ndarray):
            pass
        a = np.arange(10).view(SubClass)
        assert_(isinstance(np.insert(a, 0, [0]), SubClass))
        assert_(isinstance(np.insert(a, [], []), SubClass))
        assert_(isinstance(np.insert(a, [0, 1], [1, 2]), SubClass))
        assert_(isinstance(np.insert(a, slice(1, 2), [1, 2]), SubClass))
        assert_(isinstance(np.insert(a, slice(1, -2, -1), []), SubClass))
        # This is an error in the future:
        a = np.array(1).view(SubClass)
        assert_(isinstance(np.insert(a, 0, [0]), SubClass))

    def test_index_array_copied(self):
        x = np.array([1, 1, 1])
        np.insert([0, 1, 2], x, [3, 4, 5])
        assert_equal(x, np.array([1, 1, 1]))

    def test_structured_array(self):
        a = np.array([(1, 'a'), (2, 'b'), (3, 'c')],
                     dtype=[('foo', 'i'), ('bar', 'S1')])
        val = (4, 'd')
        b = np.insert(a, 0, val)
        assert_array_equal(b[0], np.array(val, dtype=b.dtype))
        val = [(4, 'd')] * 2
        b = np.insert(a, [0, 2], val)
        assert_array_equal(b[[0, 3]], np.array(val, dtype=b.dtype))

    def test_index_floats(self):
        with pytest.raises(IndexError):
            np.insert([0, 1, 2], np.array([1.0, 2.0]), [10, 20])
        with pytest.raises(IndexError):
            np.insert([0, 1, 2], np.array([], dtype=float), [])

    @pytest.mark.parametrize('idx', [4, -4])
    def test_index_out_of_bounds(self, idx):
        with pytest.raises(IndexError, match='out of bounds'):
            np.insert([0, 1, 2], [idx], [3, 4])


class TestAmax:

    def test_basic(self):
        a = [3, 4, 5, 10, -3, -5, 6.0]
        assert_equal(np.amax(a), 10.0)
        b = [[3, 6.0, 9.0],
             [4, 10.0, 5.0],
             [8, 3.0, 2.0]]
        assert_equal(np.amax(b, axis=0), [8.0, 10.0, 9.0])
        assert_equal(np.amax(b, axis=1), [9.0, 10.0, 8.0])


class TestAmin:

    def test_basic(self):
        a = [3, 4, 5, 10, -3, -5, 6.0]
        assert_equal(np.amin(a), -5.0)
        b = [[3, 6.0, 9.0],
             [4, 10.0, 5.0],
             [8, 3.0, 2.0]]
        assert_equal(np.amin(b, axis=0), [3.0, 3.0, 2.0])
        assert_equal(np.amin(b, axis=1), [3.0, 4.0, 2.0])


class TestPtp:

    def test_basic(self):
        a = np.array([3, 4, 5, 10, -3, -5, 6.0])
        assert_equal(np.ptp(a, axis=0), 15.0)
        b = np.array([[3, 6.0, 9.0],
                      [4, 10.0, 5.0],
                      [8, 3.0, 2.0]])
        assert_equal(np.ptp(b, axis=0), [5.0, 7.0, 7.0])
        assert_equal(np.ptp(b, axis=-1), [6.0, 6.0, 6.0])

        assert_equal(np.ptp(b, axis=0, keepdims=True), [[5.0, 7.0, 7.0]])
        assert_equal(np.ptp(b, axis=(0, 1), keepdims=True), [[8.0]])


class TestCumsum:

    @pytest.mark.parametrize("cumsum", [np.cumsum, np.cumulative_sum])
    def test_basic(self, cumsum):
        ba = [1, 2, 10, 11, 6, 5, 4]
        ba2 = [[1, 2, 3, 4], [5, 6, 7, 9], [10, 3, 4, 5]]
        for ctype in [np.int8, np.uint8, np.int16, np.uint16, np.int32,
                      np.uint32, np.float32, np.float64, np.complex64,
                      np.complex128]:
            a = np.array(ba, ctype)
            a2 = np.array(ba2, ctype)

            tgt = np.array([1, 3, 13, 24, 30, 35, 39], ctype)
            assert_array_equal(cumsum(a, axis=0), tgt)

            tgt = np.array(
                [[1, 2, 3, 4], [6, 8, 10, 13], [16, 11, 14, 18]], ctype)
            assert_array_equal(cumsum(a2, axis=0), tgt)

            tgt = np.array(
                [[1, 3, 6, 10], [5, 11, 18, 27], [10, 13, 17, 22]], ctype)
            assert_array_equal(cumsum(a2, axis=1), tgt)


class TestProd:

    def test_basic(self):
        ba = [1, 2, 10, 11, 6, 5, 4]
        ba2 = [[1, 2, 3, 4], [5, 6, 7, 9], [10, 3, 4, 5]]
        for ctype in [np.int16, np.uint16, np.int32, np.uint32,
                      np.float32, np.float64, np.complex64, np.complex128]:
            a = np.array(ba, ctype)
            a2 = np.array(ba2, ctype)
            if ctype in ['1', 'b']:
                assert_raises(ArithmeticError, np.prod, a)
                assert_raises(ArithmeticError, np.prod, a2, 1)
            else:
                assert_equal(a.prod(axis=0), 26400)
                assert_array_equal(a2.prod(axis=0),
                                   np.array([50, 36, 84, 180], ctype))
                assert_array_equal(a2.prod(axis=-1),
                                   np.array([24, 1890, 600], ctype))


class TestCumprod:

    @pytest.mark.parametrize("cumprod", [np.cumprod, np.cumulative_prod])
    def test_basic(self, cumprod):
        ba = [1, 2, 10, 11, 6, 5, 4]
        ba2 = [[1, 2, 3, 4], [5, 6, 7, 9], [10, 3, 4, 5]]
        for ctype in [np.int16, np.uint16, np.int32, np.uint32,
                      np.float32, np.float64, np.complex64, np.complex128]:
            a = np.array(ba, ctype)
            a2 = np.array(ba2, ctype)
            if ctype in ['1', 'b']:
                assert_raises(ArithmeticError, cumprod, a)
                assert_raises(ArithmeticError, cumprod, a2, 1)
                assert_raises(ArithmeticError, cumprod, a)
            else:
                assert_array_equal(cumprod(a, axis=-1),
                                   np.array([1, 2, 20, 220,
                                             1320, 6600, 26400], ctype))
                assert_array_equal(cumprod(a2, axis=0),
                                   np.array([[1, 2, 3, 4],
                                             [5, 12, 21, 36],
                                             [50, 36, 84, 180]], ctype))
                assert_array_equal(cumprod(a2, axis=-1),
                                   np.array([[1, 2, 6, 24],
                                             [5, 30, 210, 1890],
                                             [10, 30, 120, 600]], ctype))


def test_cumulative_include_initial():
    arr = np.arange(8).reshape((2, 2, 2))

    expected = np.array([
        [[0, 0], [0, 1], [2, 4]], [[0, 0], [4, 5], [10, 12]]
    ])
    assert_array_equal(
        np.cumulative_sum(arr, axis=1, include_initial=True), expected
    )

    expected = np.array([
        [[1, 0, 0], [1, 2, 6]], [[1, 4, 20], [1, 6, 42]]
    ])
    assert_array_equal(
        np.cumulative_prod(arr, axis=2, include_initial=True), expected
    )

    out = np.zeros((3, 2), dtype=np.float64)
    expected = np.array([[0, 0], [1, 2], [4, 6]], dtype=np.float64)
    arr = np.arange(1, 5).reshape((2, 2))
    np.cumulative_sum(arr, axis=0, out=out, include_initial=True)
    assert_array_equal(out, expected)

    expected = np.array([1, 2, 4])
    assert_array_equal(
        np.cumulative_prod(np.array([2, 2]), include_initial=True), expected
    )


class TestDiff:

    def test_basic(self):
        x = [1, 4, 6, 7, 12]
        out = np.array([3, 2, 1, 5])
        out2 = np.array([-1, -1, 4])
        out3 = np.array([0, 5])
        assert_array_equal(diff(x), out)
        assert_array_equal(diff(x, n=2), out2)
        assert_array_equal(diff(x, n=3), out3)

        x = [1.1, 2.2, 3.0, -0.2, -0.1]
        out = np.array([1.1, 0.8, -3.2, 0.1])
        assert_almost_equal(diff(x), out)

        x = [True, True, False, False]
        out = np.array([False, True, False])
        out2 = np.array([True, True])
        assert_array_equal(diff(x), out)
        assert_array_equal(diff(x, n=2), out2)

    def test_axis(self):
        x = np.zeros((10, 20, 30))
        x[:, 1::2, :] = 1
        exp = np.ones((10, 19, 30))
        exp[:, 1::2, :] = -1
        assert_array_equal(diff(x), np.zeros((10, 20, 29)))
        assert_array_equal(diff(x, axis=-1), np.zeros((10, 20, 29)))
        assert_array_equal(diff(x, axis=0), np.zeros((9, 20, 30)))
        assert_array_equal(diff(x, axis=1), exp)
        assert_array_equal(diff(x, axis=-2), exp)
        assert_raises(AxisError, diff, x, axis=3)
        assert_raises(AxisError, diff, x, axis=-4)

        x = np.array(1.11111111111, np.float64)
        assert_raises(ValueError, diff, x)

    def test_nd(self):
        x = 20 * rand(10, 20, 30)
        out1 = x[:, :, 1:] - x[:, :, :-1]
        out2 = out1[:, :, 1:] - out1[:, :, :-1]
        out3 = x[1:, :, :] - x[:-1, :, :]
        out4 = out3[1:, :, :] - out3[:-1, :, :]
        assert_array_equal(diff(x), out1)
        assert_array_equal(diff(x, n=2), out2)
        assert_array_equal(diff(x, axis=0), out3)
        assert_array_equal(diff(x, n=2, axis=0), out4)

    def test_n(self):
        x = list(range(3))
        assert_raises(ValueError, diff, x, n=-1)
        output = [diff(x, n=n) for n in range(1, 5)]
        expected = [[1, 1], [0], [], []]
        assert_(diff(x, n=0) is x)
        for n, (expected_n, output_n) in enumerate(zip(expected, output), start=1):
            assert_(type(output_n) is np.ndarray)
            assert_array_equal(output_n, expected_n)
            assert_equal(output_n.dtype, np.int_)
            assert_equal(len(output_n), max(0, len(x) - n))

    def test_times(self):
        x = np.arange('1066-10-13', '1066-10-16', dtype=np.datetime64)
        expected = [
            np.array([1, 1], dtype='timedelta64[D]'),
            np.array([0], dtype='timedelta64[D]'),
        ]
        expected.extend([np.array([], dtype='timedelta64[D]')] * 3)
        for n, exp in enumerate(expected, start=1):
            out = diff(x, n=n)
            assert_array_equal(out, exp)
            assert_equal(out.dtype, exp.dtype)

    def test_subclass(self):
        x = ma.array([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]],
                     mask=[[False, False], [True, False],
                           [False, True], [True, True], [False, False]])
        out = diff(x)
        assert_array_equal(out.data, [[1], [1], [1], [1], [1]])
        assert_array_equal(out.mask, [[False], [True],
                                      [True], [True], [False]])
        assert_(type(out) is type(x))

        out3 = diff(x, n=3)
        assert_array_equal(out3.data, [[], [], [], [], []])
        assert_array_equal(out3.mask, [[], [], [], [], []])
        assert_(type(out3) is type(x))

    def test_prepend(self):
        x = np.arange(5) + 1
        assert_array_equal(diff(x, prepend=0), np.ones(5))
        assert_array_equal(diff(x, prepend=[0]), np.ones(5))
        assert_array_equal(np.cumsum(np.diff(x, prepend=0)), x)
        assert_array_equal(diff(x, prepend=[-1, 0]), np.ones(6))

        x = np.arange(4).reshape(2, 2)
        result = np.diff(x, axis=1, prepend=0)
        expected = [[0, 1], [2, 1]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=1, prepend=[[0], [0]])
        assert_array_equal(result, expected)

        result = np.diff(x, axis=0, prepend=0)
        expected = [[0, 1], [2, 2]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=0, prepend=[[0, 0]])
        assert_array_equal(result, expected)

        assert_raises(ValueError, np.diff, x, prepend=np.zeros((3, 3)))

        assert_raises(AxisError, diff, x, prepend=0, axis=3)

    def test_append(self):
        x = np.arange(5)
        result = diff(x, append=0)
        expected = [1, 1, 1, 1, -4]
        assert_array_equal(result, expected)
        result = diff(x, append=[0])
        assert_array_equal(result, expected)
        result = diff(x, append=[0, 2])
        expected = expected + [2]
        assert_array_equal(result, expected)

        x = np.arange(4).reshape(2, 2)
        result = np.diff(x, axis=1, append=0)
        expected = [[1, -1], [1, -3]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=1, append=[[0], [0]])
        assert_array_equal(result, expected)

        result = np.diff(x, axis=0, append=0)
        expected = [[2, 2], [-2, -3]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=0, append=[[0, 0]])
        assert_array_equal(result, expected)

        assert_raises(ValueError, np.diff, x, append=np.zeros((3, 3)))

        assert_raises(AxisError, diff, x, append=0, axis=3)


class TestDelete:

    def setup_method(self):
        self.a = np.arange(5)
        self.nd_a = np.arange(5).repeat(2).reshape(1, 5, 2)

    def _check_inverse_of_slicing(self, indices):
        a_del = delete(self.a, indices)
        nd_a_del = delete(self.nd_a, indices, axis=1)
        msg = f'Delete failed for obj: {indices!r}'
        assert_array_equal(setxor1d(a_del, self.a[indices, ]), self.a,
                           err_msg=msg)
        xor = setxor1d(nd_a_del[0, :, 0], self.nd_a[0, indices, 0])
        assert_array_equal(xor, self.nd_a[0, :, 0], err_msg=msg)

    def test_slices(self):
        lims = [-6, -2, 0, 1, 2, 4, 5]
        steps = [-3, -1, 1, 3]
        for start in lims:
            for stop in lims:
                for step in steps:
                    s = slice(start, stop, step)
                    self._check_inverse_of_slicing(s)

    def test_fancy(self):
        self._check_inverse_of_slicing(np.array([[0, 1], [2, 1]]))
        with pytest.raises(IndexError):
            delete(self.a, [100])
        with pytest.raises(IndexError):
            delete(self.a, [-100])

        self._check_inverse_of_slicing([0, -1, 2, 2])

        self._check_inverse_of_slicing([True, False, False, True, False])

        # not legal, indexing with these would change the dimension
        with pytest.raises(ValueError):
            delete(self.a, True)
        with pytest.raises(ValueError):
            delete(self.a, False)

        # not enough items
        with pytest.raises(ValueError):
            delete(self.a, [False] * 4)

    def test_single(self):
        self._check_inverse_of_slicing(0)
        self._check_inverse_of_slicing(-4)

    def test_0d(self):
        a = np.array(1)
        with pytest.raises(AxisError):
            delete(a, [], axis=0)
        with pytest.raises(TypeError):
            delete(a, [], axis="nonsense")

    def test_subclass(self):
        class SubClass(np.ndarray):
            pass
        a = self.a.view(SubClass)
        assert_(isinstance(delete(a, 0), SubClass))
        assert_(isinstance(delete(a, []), SubClass))
        assert_(isinstance(delete(a, [0, 1]), SubClass))
        assert_(isinstance(delete(a, slice(1, 2)), SubClass))
        assert_(isinstance(delete(a, slice(1, -2)), SubClass))

    def test_array_order_preserve(self):
        # See gh-7113
        k = np.arange(10).reshape(2, 5, order='F')
        m = delete(k, slice(60, None), axis=1)

        # 'k' is Fortran ordered, and 'm' should have the
        # same ordering as 'k' and NOT become C ordered
        assert_equal(m.flags.c_contiguous, k.flags.c_contiguous)
        assert_equal(m.flags.f_contiguous, k.flags.f_contiguous)

    def test_index_floats(self):
        with pytest.raises(IndexError):
            np.delete([0, 1, 2], np.array([1.0, 2.0]))
        with pytest.raises(IndexError):
            np.delete([0, 1, 2], np.array([], dtype=float))

    @pytest.mark.parametrize("indexer", [np.array([1]), [1]])
    def test_single_item_array(self, indexer):
        a_del_int = delete(self.a, 1)
        a_del = delete(self.a, indexer)
        assert_equal(a_del_int, a_del)

        nd_a_del_int = delete(self.nd_a, 1, axis=1)
        nd_a_del = delete(self.nd_a, np.array([1]), axis=1)
        assert_equal(nd_a_del_int, nd_a_del)

    def test_single_item_array_non_int(self):
        # Special handling for integer arrays must not affect non-integer ones.
        # If `False` was cast to `0` it would delete the element:
        res = delete(np.ones(1), np.array([False]))
        assert_array_equal(res, np.ones(1))

        # Test the more complicated (with axis) case from gh-21840
        x = np.ones((3, 1))
        false_mask = np.array([False], dtype=bool)
        true_mask = np.array([True], dtype=bool)

        res = delete(x, false_mask, axis=-1)
        assert_array_equal(res, x)
        res = delete(x, true_mask, axis=-1)
        assert_array_equal(res, x[:, :0])

        # Object or e.g. timedeltas should *not* be allowed
        with pytest.raises(IndexError):
            delete(np.ones(2), np.array([0], dtype=object))

        with pytest.raises(IndexError):
            # timedeltas are sometimes "integral, but clearly not allowed:
            delete(np.ones(2), np.array([0], dtype="m8[ns]"))


class TestGradient:

    def test_basic(self):
        v = [[1, 1], [3, 4]]
        x = np.array(v)
        dx = [np.array([[2., 3.], [2., 3.]]),
              np.array([[0., 0.], [1., 1.]])]
        assert_array_equal(gradient(x), dx)
        assert_array_equal(gradient(v), dx)

    def test_args(self):
        dx = np.cumsum(np.ones(5))
        dx_uneven = [1., 2., 5., 9., 11.]
        f_2d = np.arange(25).reshape(5, 5)

        # distances must be scalars or have size equal to gradient[axis]
        gradient(np.arange(5), 3.)
        gradient(np.arange(5), np.array(3.))
        gradient(np.arange(5), dx)
        # dy is set equal to dx because scalar
        gradient(f_2d, 1.5)
        gradient(f_2d, np.array(1.5))

        gradient(f_2d, dx_uneven, dx_uneven)
        # mix between even and uneven spaces and
        # mix between scalar and vector
        gradient(f_2d, dx, 2)

        # 2D but axis specified
        gradient(f_2d, dx, axis=1)

        # 2d coordinate arguments are not yet allowed
        assert_raises_regex(ValueError, '.*scalars or 1d',
            gradient, f_2d, np.stack([dx] * 2, axis=-1), 1)

    def test_badargs(self):
        f_2d = np.arange(25).reshape(5, 5)
        x = np.cumsum(np.ones(5))

        # wrong sizes
        assert_raises(ValueError, gradient, f_2d, x, np.ones(2))
        assert_raises(ValueError, gradient, f_2d, 1, np.ones(2))
        assert_raises(ValueError, gradient, f_2d, np.ones(2), np.ones(2))
        # wrong number of arguments
        assert_raises(TypeError, gradient, f_2d, x)
        assert_raises(TypeError, gradient, f_2d, x, axis=(0, 1))
        assert_raises(TypeError, gradient, f_2d, x, x, x)
        assert_raises(TypeError, gradient, f_2d, 1, 1, 1)
        assert_raises(TypeError, gradient, f_2d, x, x, axis=1)
        assert_raises(TypeError, gradient, f_2d, 1, 1, axis=1)

    def test_datetime64(self):
        # Make sure gradient() can handle special types like datetime64
        x = np.array(
            ['1910-08-16', '1910-08-11', '1910-08-10', '1910-08-12',
             '1910-10-12', '1910-12-12', '1912-12-12'],
            dtype='datetime64[D]')
        dx = np.array(
            [-5, -3, 0, 31, 61, 396, 731],
            dtype='timedelta64[D]')
        assert_array_equal(gradient(x), dx)
        assert_(dx.dtype == np.dtype('timedelta64[D]'))

    def test_masked(self):
        # Make sure that gradient supports subclasses like masked arrays
        x = np.ma.array([[1, 1], [3, 4]],
                        mask=[[False, False], [False, False]])
        out = gradient(x)[0]
        assert_equal(type(out), type(x))
        # And make sure that the output and input don't have aliased mask
        # arrays
        assert_(x._mask is not out._mask)
        # Also check that edge_order=2 doesn't alter the original mask
        x2 = np.ma.arange(5)
        x2[2] = np.ma.masked
        np.gradient(x2, edge_order=2)
        assert_array_equal(x2.mask, [False, False, True, False, False])

    def test_second_order_accurate(self):
        # Testing that the relative numerical error is less that 3% for
        # this example problem. This corresponds to second order
        # accurate finite differences for all interior and boundary
        # points.
        x = np.linspace(0, 1, 10)
        dx = x[1] - x[0]
        y = 2 * x ** 3 + 4 * x ** 2 + 2 * x
        analytical = 6 * x ** 2 + 8 * x + 2
        num_error = np.abs((np.gradient(y, dx, edge_order=2) / analytical) - 1)
        assert_(np.all(num_error < 0.03) == True)

        # test with unevenly spaced
        np.random.seed(0)
        x = np.sort(np.random.random(10))
        y = 2 * x ** 3 + 4 * x ** 2 + 2 * x
        analytical = 6 * x ** 2 + 8 * x + 2
        num_error = np.abs((np.gradient(y, x, edge_order=2) / analytical) - 1)
        assert_(np.all(num_error < 0.03) == True)

    def test_spacing(self):
        f = np.array([0, 2., 3., 4., 5., 5.])
        f = np.tile(f, (6, 1)) + f.reshape(-1, 1)
        x_uneven = np.array([0., 0.5, 1., 3., 5., 7.])
        x_even = np.arange(6.)

        fdx_even_ord1 = np.tile([2., 1.5, 1., 1., 0.5, 0.], (6, 1))
        fdx_even_ord2 = np.tile([2.5, 1.5, 1., 1., 0.5, -0.5], (6, 1))
        fdx_uneven_ord1 = np.tile([4., 3., 1.7, 0.5, 0.25, 0.], (6, 1))
        fdx_uneven_ord2 = np.tile([5., 3., 1.7, 0.5, 0.25, -0.25], (6, 1))

        # evenly spaced
        for edge_order, exp_res in [(1, fdx_even_ord1), (2, fdx_even_ord2)]:
            res1 = gradient(f, 1., axis=(0, 1), edge_order=edge_order)
            res2 = gradient(f, x_even, x_even,
                            axis=(0, 1), edge_order=edge_order)
            res3 = gradient(f, x_even, x_even,
                            axis=None, edge_order=edge_order)
            assert_array_equal(res1, res2)
            assert_array_equal(res2, res3)
            assert_almost_equal(res1[0], exp_res.T)
            assert_almost_equal(res1[1], exp_res)

            res1 = gradient(f, 1., axis=0, edge_order=edge_order)
            res2 = gradient(f, x_even, axis=0, edge_order=edge_order)
            assert_(res1.shape == res2.shape)
            assert_almost_equal(res2, exp_res.T)

            res1 = gradient(f, 1., axis=1, edge_order=edge_order)
            res2 = gradient(f, x_even, axis=1, edge_order=edge_order)
            assert_(res1.shape == res2.shape)
            assert_array_equal(res2, exp_res)

        # unevenly spaced
        for edge_order, exp_res in [(1, fdx_uneven_ord1), (2, fdx_uneven_ord2)]:
            res1 = gradient(f, x_uneven, x_uneven,
                            axis=(0, 1), edge_order=edge_order)
            res2 = gradient(f, x_uneven, x_uneven,
                            axis=None, edge_order=edge_order)
            assert_array_equal(res1, res2)
            assert_almost_equal(res1[0], exp_res.T)
            assert_almost_equal(res1[1], exp_res)

            res1 = gradient(f, x_uneven, axis=0, edge_order=edge_order)
            assert_almost_equal(res1, exp_res.T)

            res1 = gradient(f, x_uneven, axis=1, edge_order=edge_order)
            assert_almost_equal(res1, exp_res)

        # mixed
        res1 = gradient(f, x_even, x_uneven, axis=(0, 1), edge_order=1)
        res2 = gradient(f, x_uneven, x_even, axis=(1, 0), edge_order=1)
        assert_array_equal(res1[0], res2[1])
        assert_array_equal(res1[1], res2[0])
        assert_almost_equal(res1[0], fdx_even_ord1.T)
        assert_almost_equal(res1[1], fdx_uneven_ord1)

        res1 = gradient(f, x_even, x_uneven, axis=(0, 1), edge_order=2)
        res2 = gradient(f, x_uneven, x_even, axis=(1, 0), edge_order=2)
        assert_array_equal(res1[0], res2[1])
        assert_array_equal(res1[1], res2[0])
        assert_almost_equal(res1[0], fdx_even_ord2.T)
        assert_almost_equal(res1[1], fdx_uneven_ord2)

    def test_specific_axes(self):
        # Testing that gradient can work on a given axis only
        v = [[1, 1], [3, 4]]
        x = np.array(v)
        dx = [np.array([[2., 3.], [2., 3.]]),
              np.array([[0., 0.], [1., 1.]])]
        assert_array_equal(gradient(x, axis=0), dx[0])
        assert_array_equal(gradient(x, axis=1), dx[1])
        assert_array_equal(gradient(x, axis=-1), dx[1])
        assert_array_equal(gradient(x, axis=(1, 0)), [dx[1], dx[0]])

        # test axis=None which means all axes
        assert_almost_equal(gradient(x, axis=None), [dx[0], dx[1]])
        # and is the same as no axis keyword given
        assert_almost_equal(gradient(x, axis=None), gradient(x))

        # test vararg order
        assert_array_equal(gradient(x, 2, 3, axis=(1, 0)),
                           [dx[1] / 2.0, dx[0] / 3.0])
        # test maximal number of varargs
        assert_raises(TypeError, gradient, x, 1, 2, axis=1)

        assert_raises(AxisError, gradient, x, axis=3)
        assert_raises(AxisError, gradient, x, axis=-3)
        # assert_raises(TypeError, gradient, x, axis=[1,])

    def test_timedelta64(self):
        # Make sure gradient() can handle special types like timedelta64
        x = np.array(
            [-5, -3, 10, 12, 61, 321, 300],
            dtype='timedelta64[D]')
        dx = np.array(
            [2, 7, 7, 25, 154, 119, -21],
            dtype='timedelta64[D]')
        assert_array_equal(gradient(x), dx)
        assert_(dx.dtype == np.dtype('timedelta64[D]'))

    def test_inexact_dtypes(self):
        for dt in [np.float16, np.float32, np.float64]:
            # dtypes should not be promoted in a different way to what diff does
            x = np.array([1, 2, 3], dtype=dt)
            assert_equal(gradient(x).dtype, np.diff(x).dtype)

    def test_values(self):
        # needs at least 2 points for edge_order ==1
        gradient(np.arange(2), edge_order=1)
        # needs at least 3 points for edge_order ==1
        gradient(np.arange(3), edge_order=2)

        assert_raises(ValueError, gradient, np.arange(0), edge_order=1)
        assert_raises(ValueError, gradient, np.arange(0), edge_order=2)
        assert_raises(ValueError, gradient, np.arange(1), edge_order=1)
        assert_raises(ValueError, gradient, np.arange(1), edge_order=2)
        assert_raises(ValueError, gradient, np.arange(2), edge_order=2)

    @pytest.mark.parametrize('f_dtype', [np.uint8, np.uint16,
                                         np.uint32, np.uint64])
    def test_f_decreasing_unsigned_int(self, f_dtype):
        f = np.array([5, 4, 3, 2, 1], dtype=f_dtype)
        g = gradient(f)
        assert_array_equal(g, [-1] * len(f))

    @pytest.mark.parametrize('f_dtype', [np.int8, np.int16,
                                         np.int32, np.int64])
    def test_f_signed_int_big_jump(self, f_dtype):
        maxint = np.iinfo(f_dtype).max
        x = np.array([1, 3])
        f = np.array([-1, maxint], dtype=f_dtype)
        dfdx = gradient(f, x)
        assert_array_equal(dfdx, [(maxint + 1) // 2] * 2)

    @pytest.mark.parametrize('x_dtype', [np.uint8, np.uint16,
                                         np.uint32, np.uint64])
    def test_x_decreasing_unsigned(self, x_dtype):
        x = np.array([3, 2, 1], dtype=x_dtype)
        f = np.array([0, 2, 4])
        dfdx = gradient(f, x)
        assert_array_equal(dfdx, [-2] * len(x))

    @pytest.mark.parametrize('x_dtype', [np.int8, np.int16,
                                         np.int32, np.int64])
    def test_x_signed_int_big_jump(self, x_dtype):
        minint = np.iinfo(x_dtype).min
        maxint = np.iinfo(x_dtype).max
        x = np.array([-1, maxint], dtype=x_dtype)
        f = np.array([minint // 2, 0])
        dfdx = gradient(f, x)
        assert_array_equal(dfdx, [0.5, 0.5])

    def test_return_type(self):
        res = np.gradient(([1, 2], [2, 3]))
        assert type(res) is tuple


class TestAngle:

    def test_basic(self):
        x = [1 + 3j, np.sqrt(2) / 2.0 + 1j * np.sqrt(2) / 2,
             1, 1j, -1, -1j, 1 - 3j, -1 + 3j]
        y = angle(x)
        yo = [
            np.arctan(3.0 / 1.0),
            np.arctan(1.0), 0, np.pi / 2, np.pi, -np.pi / 2.0,
            -np.arctan(3.0 / 1.0), np.pi - np.arctan(3.0 / 1.0)]
        z = angle(x, deg=True)
        zo = np.array(yo) * 180 / np.pi
        assert_array_almost_equal(y, yo, 11)
        assert_array_almost_equal(z, zo, 11)

    def test_subclass(self):
        x = np.ma.array([1 + 3j, 1, np.sqrt(2) / 2 * (1 + 1j)])
        x[1] = np.ma.masked
        expected = np.ma.array([np.arctan(3.0 / 1.0), 0, np.arctan(1.0)])
        expected[1] = np.ma.masked
        actual = angle(x)
        assert_equal(type(actual), type(expected))
        assert_equal(actual.mask, expected.mask)
        assert_equal(actual, expected)


class TestTrimZeros:

    a = np.array([0, 0, 1, 0, 2, 3, 4, 0])
    b = a.astype(float)
    c = a.astype(complex)
    d = a.astype(object)

    def values(self):
        attr_names = ('a', 'b', 'c', 'd')
        return (getattr(self, name) for name in attr_names)

    def test_basic(self):
        slc = np.s_[2:-1]
        for arr in self.values():
            res = trim_zeros(arr)
            assert_array_equal(res, arr[slc])

    def test_leading_skip(self):
        slc = np.s_[:-1]
        for arr in self.values():
            res = trim_zeros(arr, trim='b')
            assert_array_equal(res, arr[slc])

    def test_trailing_skip(self):
        slc = np.s_[2:]
        for arr in self.values():
            res = trim_zeros(arr, trim='F')
            assert_array_equal(res, arr[slc])

    def test_all_zero(self):
        for _arr in self.values():
            arr = np.zeros_like(_arr, dtype=_arr.dtype)

            res1 = trim_zeros(arr, trim='B')
            assert len(res1) == 0

            res2 = trim_zeros(arr, trim='f')
            assert len(res2) == 0

    def test_size_zero(self):
        arr = np.zeros(0)
        res = trim_zeros(arr)
        assert_array_equal(arr, res)

    @pytest.mark.parametrize(
        'arr',
        [np.array([0, 2**62, 0]),
         np.array([0, 2**63, 0]),
         np.array([0, 2**64, 0])]
    )
    def test_overflow(self, arr):
        slc = np.s_[1:2]
        res = trim_zeros(arr)
        assert_array_equal(res, arr[slc])

    def test_no_trim(self):
        arr = np.array([None, 1, None])
        res = trim_zeros(arr)
        assert_array_equal(arr, res)

    def test_list_to_list(self):
        res = trim_zeros(self.a.tolist())
        assert isinstance(res, list)

    @pytest.mark.parametrize("ndim", (0, 1, 2, 3, 10))
    def test_nd_basic(self, ndim):
        a = np.ones((2,) * ndim)
        b = np.pad(a, (2, 1), mode="constant", constant_values=0)
        res = trim_zeros(b, axis=None)
        assert_array_equal(a, res)

    @pytest.mark.parametrize("ndim", (0, 1, 2, 3))
    def test_allzero(self, ndim):
        a = np.zeros((3,) * ndim)
        res = trim_zeros(a, axis=None)
        assert_array_equal(res, np.zeros((0,) * ndim))

    def test_trim_arg(self):
        a = np.array([0, 1, 2, 0])

        res = trim_zeros(a, trim='f')
        assert_array_equal(res, [1, 2, 0])

        res = trim_zeros(a, trim='b')
        assert_array_equal(res, [0, 1, 2])

    @pytest.mark.parametrize("trim", ("front", ""))
    def test_unexpected_trim_value(self, trim):
        arr = self.a
        with pytest.raises(ValueError, match=r"unexpected character\(s\) in `trim`"):
            trim_zeros(arr, trim=trim)


class TestExtins:

    def test_basic(self):
        a = np.array([1, 3, 2, 1, 2, 3, 3])
        b = extract(a > 1, a)
        assert_array_equal(b, [3, 2, 2, 3, 3])

    def test_place(self):
        # Make sure that non-np.ndarray objects
        # raise an error instead of doing nothing
        assert_raises(TypeError, place, [1, 2, 3], [True, False], [0, 1])

        a = np.array([1, 4, 3, 2, 5, 8, 7])
        place(a, [0, 1, 0, 1, 0, 1, 0], [2, 4, 6])
        assert_array_equal(a, [1, 2, 3, 4, 5, 6, 7])

        place(a, np.zeros(7), [])
        assert_array_equal(a, np.arange(1, 8))

        place(a, [1, 0, 1, 0, 1, 0, 1], [8, 9])
        assert_array_equal(a, [8, 2, 9, 4, 8, 6, 9])
        assert_raises_regex(ValueError, "Cannot insert from an empty array",
                            lambda: place(a, [0, 0, 0, 0, 0, 1, 0], []))

        # See Issue #6974
        a = np.array(['12', '34'])
        place(a, [0, 1], '9')
        assert_array_equal(a, ['12', '9'])

    def test_both(self):
        a = rand(10)
        mask = a > 0.5
        ac = a.copy()
        c = extract(mask, a)
        place(a, mask, 0)
        place(a, mask, c)
        assert_array_equal(a, ac)


# _foo1 and _foo2 are used in some tests in TestVectorize.

def _foo1(x, y=1.0):
    return y * math.floor(x)


def _foo2(x, y=1.0, z=0.0):
    return y * math.floor(x) + z


class TestVectorize:

    def test_simple(self):
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        f = vectorize(addsubtract)
        r = f([0, 3, 6, 9], [1, 3, 5, 7])
        assert_array_equal(r, [1, 6, 1, 2])

    def test_scalar(self):
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        f = vectorize(addsubtract)
        r = f([0, 3, 6, 9], 5)
        assert_array_equal(r, [5, 8, 1, 4])

    def test_large(self):
        x = np.linspace(-3, 2, 10000)
        f = vectorize(lambda x: x)
        y = f(x)
        assert_array_equal(y, x)

    def test_ufunc(self):
        f = vectorize(math.cos)
        args = np.array([0, 0.5 * np.pi, np.pi, 1.5 * np.pi, 2 * np.pi])
        r1 = f(args)
        r2 = np.cos(args)
        assert_array_almost_equal(r1, r2)

    def test_keywords(self):

        def foo(a, b=1):
            return a + b

        f = vectorize(foo)
        args = np.array([1, 2, 3])
        r1 = f(args)
        r2 = np.array([2, 3, 4])
        assert_array_equal(r1, r2)
        r1 = f(args, 2)
        r2 = np.array([3, 4, 5])
        assert_array_equal(r1, r2)

    def test_keywords_with_otypes_order1(self):
        # gh-1620: The second call of f would crash with
        # `ValueError: invalid number of arguments`.
        f = vectorize(_foo1, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(np.arange(3.0), 1.0)
        r2 = f(np.arange(3.0))
        assert_array_equal(r1, r2)

    def test_keywords_with_otypes_order2(self):
        # gh-1620: The second call of f would crash with
        # `ValueError: non-broadcastable output operand with shape ()
        # doesn't match the broadcast shape (3,)`.
        f = vectorize(_foo1, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(np.arange(3.0))
        r2 = f(np.arange(3.0), 1.0)
        assert_array_equal(r1, r2)

    def test_keywords_with_otypes_order3(self):
        # gh-1620: The third call of f would crash with
        # `ValueError: invalid number of arguments`.
        f = vectorize(_foo1, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(np.arange(3.0))
        r2 = f(np.arange(3.0), y=1.0)
        r3 = f(np.arange(3.0))
        assert_array_equal(r1, r2)
        assert_array_equal(r1, r3)

    def test_keywords_with_otypes_several_kwd_args1(self):
        # gh-1620 Make sure different uses of keyword arguments
        # don't break the vectorized function.
        f = vectorize(_foo2, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(10.4, z=100)
        r2 = f(10.4, y=-1)
        r3 = f(10.4)
        assert_equal(r1, _foo2(10.4, z=100))
        assert_equal(r2, _foo2(10.4, y=-1))
        assert_equal(r3, _foo2(10.4))

    def test_keywords_with_otypes_several_kwd_args2(self):
        # gh-1620 Make sure different uses of keyword arguments
        # don't break the vectorized function.
        f = vectorize(_foo2, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(z=100, x=10.4, y=-1)
        r2 = f(1, 2, 3)
        assert_equal(r1, _foo2(z=100, x=10.4, y=-1))
        assert_equal(r2, _foo2(1, 2, 3))

    def test_keywords_no_func_code(self):
        # This needs to test a function that has keywords but
        # no func_code attribute, since otherwise vectorize will
        # inspect the func_code.
        import random
        try:
            vectorize(random.randrange)  # Should succeed
        except Exception:
            raise AssertionError

    def test_keywords2_ticket_2100(self):
        # Test kwarg support: enhancement ticket 2100

        def foo(a, b=1):
            return a + b

        f = vectorize(foo)
        args = np.array([1, 2, 3])
        r1 = f(a=args)
        r2 = np.array([2, 3, 4])
        assert_array_equal(r1, r2)
        r1 = f(b=1, a=args)
        assert_array_equal(r1, r2)
        r1 = f(args, b=2)
        r2 = np.array([3, 4, 5])
        assert_array_equal(r1, r2)

    def test_keywords3_ticket_2100(self):
        # Test excluded with mixed positional and kwargs: ticket 2100
        def mypolyval(x, p):
            _p = list(p)
            res = _p.pop(0)
            while _p:
                res = res * x + _p.pop(0)
            return res

        vpolyval = np.vectorize(mypolyval, excluded=['p', 1])
        ans = [3, 6]
        assert_array_equal(ans, vpolyval(x=[0, 1], p=[1, 2, 3]))
        assert_array_equal(ans, vpolyval([0, 1], p=[1, 2, 3]))
        assert_array_equal(ans, vpolyval([0, 1], [1, 2, 3]))

    def test_keywords4_ticket_2100(self):
        # Test vectorizing function with no positional args.
        @vectorize
        def f(**kw):
            res = 1.0
            for _k in kw:
                res *= kw[_k]
            return res

        assert_array_equal(f(a=[1, 2], b=[3, 4]), [3, 8])

    def test_keywords5_ticket_2100(self):
        # Test vectorizing function with no kwargs args.
        @vectorize
        def f(*v):
            return np.prod(v)

        assert_array_equal(f([1, 2], [3, 4]), [3, 8])

    def test_coverage1_ticket_2100(self):
        def foo():
            return 1

        f = vectorize(foo)
        assert_array_equal(f(), 1)

    def test_assigning_docstring(self):
        def foo(x):
            """Original documentation"""
            return x

        f = vectorize(foo)
        assert_equal(f.__doc__, foo.__doc__)

        doc = "Provided documentation"
        f = vectorize(foo, doc=doc)
        assert_equal(f.__doc__, doc)

    def test_UnboundMethod_ticket_1156(self):
        # Regression test for issue 1156
        class Foo:
            b = 2

            def bar(self, a):
                return a ** self.b

        assert_array_equal(vectorize(Foo().bar)(np.arange(9)),
                           np.arange(9) ** 2)
        assert_array_equal(vectorize(Foo.bar)(Foo(), np.arange(9)),
                           np.arange(9) ** 2)

    def test_execution_order_ticket_1487(self):
        # Regression test for dependence on execution order: issue 1487
        f1 = vectorize(lambda x: x)
        res1a = f1(np.arange(3))
        res1b = f1(np.arange(0.1, 3))
        f2 = vectorize(lambda x: x)
        res2b = f2(np.arange(0.1, 3))
        res2a = f2(np.arange(3))
        assert_equal(res1a, res2a)
        assert_equal(res1b, res2b)

    def test_string_ticket_1892(self):
        # Test vectorization over strings: issue 1892.
        f = np.vectorize(lambda x: x)
        s = '0123456789' * 10
        assert_equal(s, f(s))

    def test_dtype_promotion_gh_29189(self):
        # dtype should not be silently promoted (int32 -> int64)
        dtypes = [np.int16, np.int32, np.int64, np.float16, np.float32, np.float64]

        for dtype in dtypes:
            x = np.asarray([1, 2, 3], dtype=dtype)
            y = np.vectorize(lambda x: x + x)(x)
            assert x.dtype == y.dtype

    def test_cache(self):
        # Ensure that vectorized func called exactly once per argument.
        _calls = [0]

        @vectorize
        def f(x):
            _calls[0] += 1
            return x ** 2

        f.cache = True
        x = np.arange(5)
        assert_array_equal(f(x), x * x)
        assert_equal(_calls[0], len(x))

    def test_otypes(self):
        f = np.vectorize(lambda x: x)
        f.otypes = 'i'
        x = np.arange(5)
        assert_array_equal(f(x), x)

    def test_otypes_object_28624(self):
        # with object otype, the vectorized function should return y
        # wrapped into an object array
        y = np.arange(3)
        f = vectorize(lambda x: y, otypes=[object])

        assert f(None).item() is y
        assert f([None]).item() is y

        y = [1, 2, 3]
        f = vectorize(lambda x: y, otypes=[object])

        assert f(None).item() is y
        assert f([None]).item() is y

    def test_parse_gufunc_signature(self):
        assert_equal(nfb._parse_gufunc_signature('(x)->()'), ([('x',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x,y)->()'),
                     ([('x', 'y')], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x),(y)->()'),
                     ([('x',), ('y',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x)->(y)'),
                     ([('x',)], [('y',)]))
        assert_equal(nfb._parse_gufunc_signature('(x)->(y),()'),
                     ([('x',)], [('y',), ()]))
        assert_equal(nfb._parse_gufunc_signature('(),(a,b,c),(d)->(d,e)'),
                     ([(), ('a', 'b', 'c'), ('d',)], [('d', 'e')]))

        # Tests to check if whitespaces are ignored
        assert_equal(nfb._parse_gufunc_signature('(x )->()'), ([('x',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('( x , y )->(  )'),
                     ([('x', 'y')], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x),( y) ->()'),
                     ([('x',), ('y',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('(  x)-> (y )  '),
                     ([('x',)], [('y',)]))
        assert_equal(nfb._parse_gufunc_signature(' (x)->( y),( )'),
                     ([('x',)], [('y',), ()]))
        assert_equal(nfb._parse_gufunc_signature(
                     '(  ), ( a,  b,c )  ,(  d)   ->   (d  ,  e)'),
                     ([(), ('a', 'b', 'c'), ('d',)], [('d', 'e')]))

        with assert_raises(ValueError):
            nfb._parse_gufunc_signature('(x)(y)->()')
        with assert_raises(ValueError):
            nfb._parse_gufunc_signature('(x),(y)->')
        with assert_raises(ValueError):
            nfb._parse_gufunc_signature('((x))->(x)')

    def test_signature_simple(self):
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        f = vectorize(addsubtract, signature='(),()->()')
        r = f([0, 3, 6, 9], [1, 3, 5, 7])
        assert_array_equal(r, [1, 6, 1, 2])

    def test_signature_mean_last(self):
        def mean(a):
            return a.mean()

        f = vectorize(mean, signature='(n)->()')
        r = f([[1, 3], [2, 4]])
        assert_array_equal(r, [2, 3])

    def test_signature_center(self):
        def center(a):
            return a - a.mean()

        f = vectorize(center, signature='(n)->(n)')
        r = f([[1, 3], [2, 4]])
        assert_array_equal(r, [[-1, 1], [-1, 1]])

    def test_signature_two_outputs(self):
        f = vectorize(lambda x: (x, x), signature='()->(),()')
        r = f([1, 2, 3])
        assert_(isinstance(r, tuple) and len(r) == 2)
        assert_array_equal(r[0], [1, 2, 3])
        assert_array_equal(r[1], [1, 2, 3])

    def test_signature_outer(self):
        f = vectorize(np.outer, signature='(a),(b)->(a,b)')
        r = f([1, 2], [1, 2, 3])
        assert_array_equal(r, [[1, 2, 3], [2, 4, 6]])

        r = f([[[1, 2]]], [1, 2, 3])
        assert_array_equal(r, [[[[1, 2, 3], [2, 4, 6]]]])

        r = f([[1, 0], [2, 0]], [1, 2, 3])
        assert_array_equal(r, [[[1, 2, 3], [0, 0, 0]],
                               [[2, 4, 6], [0, 0, 0]]])

        r = f([1, 2], [[1, 2, 3], [0, 0, 0]])
        assert_array_equal(r, [[[1, 2, 3], [2, 4, 6]],
                               [[0, 0, 0], [0, 0, 0]]])

    def test_signature_computed_size(self):
        f = vectorize(lambda x: x[:-1], signature='(n)->(m)')
        r = f([1, 2, 3])
        assert_array_equal(r, [1, 2])

        r = f([[1, 2, 3], [2, 3, 4]])
        assert_array_equal(r, [[1, 2], [2, 3]])

    def test_signature_excluded(self):

        def foo(a, b=1):
            return a + b

        f = vectorize(foo, signature='()->()', excluded={'b'})
        assert_array_equal(f([1, 2, 3]), [2, 3, 4])
        assert_array_equal(f([1, 2, 3], b=0), [1, 2, 3])

    def test_signature_otypes(self):
        f = vectorize(lambda x: x, signature='(n)->(n)', otypes=['float64'])
        r = f([1, 2, 3])
        assert_equal(r.dtype, np.dtype('float64'))
        assert_array_equal(r, [1, 2, 3])

    def test_signature_invalid_inputs(self):
        f = vectorize(operator.add, signature='(n),(n)->(n)')
        with assert_raises_regex(TypeError, 'wrong number of positional'):
            f([1, 2])
        with assert_raises_regex(
                ValueError, 'does not have enough dimensions'):
            f(1, 2)
        with assert_raises_regex(
                ValueError, 'inconsistent size for core dimension'):
            f([1, 2], [1, 2, 3])

        f = vectorize(operator.add, signature='()->()')
        with assert_raises_regex(TypeError, 'wrong number of positional'):
            f(1, 2)

    def test_signature_invalid_outputs(self):

        f = vectorize(lambda x: x[:-1], signature='(n)->(n)')
        with assert_raises_regex(
                ValueError, 'inconsistent size for core dimension'):
            f([1, 2, 3])

        f = vectorize(lambda x: x, signature='()->(),()')
        with assert_raises_regex(ValueError, 'wrong number of outputs'):
            f(1)

        f = vectorize(lambda x: (x, x), signature='()->()')
        with assert_raises_regex(ValueError, 'wrong number of outputs'):
            f([1, 2])

    def test_size_zero_output(self):
        # see issue 5868
        f = np.vectorize(lambda x: x)
        x = np.zeros([0, 5], dtype=int)
        with assert_raises_regex(ValueError, 'otypes'):
            f(x)

        f.otypes = 'i'
        assert_array_equal(f(x), x)

        f = np.vectorize(lambda x: x, signature='()->()')
        with assert_raises_regex(ValueError, 'otypes'):
            f(x)

        f = np.vectorize(lambda x: x, signature='()->()', otypes='i')
        assert_array_equal(f(x), x)

        f = np.vectorize(lambda x: x, signature='(n)->(n)', otypes='i')
        assert_array_equal(f(x), x)

        f = np.vectorize(lambda x: x, signature='(n)->(n)')
        assert_array_equal(f(x.T), x.T)

        f = np.vectorize(lambda x: [x], signature='()->(n)', otypes='i')
        with assert_raises_regex(ValueError, 'new output dimensions'):
            f(x)

    def test_subclasses(self):
        class subclass(np.ndarray):
            pass

        m = np.array([[1., 0., 0.],
                      [0., 0., 1.],
                      [0., 1., 0.]]).view(subclass)
        v = np.array([[1., 2., 3.], [4., 5., 6.], [7., 8., 9.]]).view(subclass)
        # generalized (gufunc)
        matvec = np.vectorize(np.matmul, signature='(m,m),(m)->(m)')
        r = matvec(m, v)
        assert_equal(type(r), subclass)
        assert_equal(r, [[1., 3., 2.], [4., 6., 5.], [7., 9., 8.]])

        # element-wise (ufunc)
        mult = np.vectorize(lambda x, y: x * y)
        r = mult(m, v)
        assert_equal(type(r), subclass)
        assert_equal(r, m * v)

    def test_name(self):
        # gh-23021
        @np.vectorize
        def f2(a, b):
            return a + b

        assert f2.__name__ == 'f2'

    def test_decorator(self):
        @vectorize
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        r = addsubtract([0, 3, 6, 9], [1, 3, 5, 7])
        assert_array_equal(r, [1, 6, 1, 2])

    def test_docstring(self):
        @vectorize
        def f(x):
            """Docstring"""
            return x

        if sys.flags.optimize < 2:
            assert f.__doc__ == "Docstring"

    def test_partial(self):
        def foo(x, y):
            return x + y

        bar = partial(foo, 3)
        vbar = np.vectorize(bar)
        assert vbar(1) == 4

    def test_signature_otypes_decorator(self):
        @vectorize(signature='(n)->(n)', otypes=['float64'])
        def f(x):
            return x

        r = f([1, 2, 3])
        assert_equal(r.dtype, np.dtype('float64'))
        assert_array_equal(r, [1, 2, 3])
        assert f.__name__ == 'f'

    def test_bad_input(self):
        with assert_raises(TypeError):
            A = np.vectorize(pyfunc=3)

    def test_no_keywords(self):
        with assert_raises(TypeError):
            @np.vectorize("string")
            def foo():
                return "bar"

    def test_positional_regression_9477(self):
        # This supplies the first keyword argument as a positional,
        # to ensure that they are still properly forwarded after the
        # enhancement for #9477
        f = vectorize((lambda x: x), ['float64'])
        r = f([2])
        assert_equal(r.dtype, np.dtype('float64'))

    def test_datetime_conversion(self):
        otype = "datetime64[ns]"
        arr = np.array(['2024-01-01', '2024-01-02', '2024-01-03'],
                       dtype='datetime64[ns]')
        assert_array_equal(np.vectorize(lambda x: x, signature="(i)->(j)",
                                        otypes=[otype])(arr), arr)


class TestLeaks:
    class A:
        iters = 20

        def bound(self, *args):
            return 0

        @staticmethod
        def unbound(*args):
            return 0

    @pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
    @pytest.mark.skipif(NOGIL_BUILD,
                        reason=("Functions are immortalized if a thread is "
                                "launched, making this test flaky"))
    @pytest.mark.parametrize('name, incr', [
            ('bound', A.iters),
            ('unbound', 0),
            ])
    def test_frompyfunc_leaks(self, name, incr):
        # exposed in gh-11867 as np.vectorized, but the problem stems from
        # frompyfunc.
        # class.attribute = np.frompyfunc(<method>) creates a
        # reference cycle if <method> is a bound class method.
        # It requires a gc collection cycle to break the cycle.
        import gc
        A_func = getattr(self.A, name)
        gc.disable()
        try:
            refcount = sys.getrefcount(A_func)
            for i in range(self.A.iters):
                a = self.A()
                a.f = np.frompyfunc(getattr(a, name), 1, 1)
                out = a.f(np.arange(10))
            a = None
            # A.func is part of a reference cycle if incr is non-zero
            assert_equal(sys.getrefcount(A_func), refcount + incr)
            for i in range(5):
                gc.collect()
            assert_equal(sys.getrefcount(A_func), refcount)
        finally:
            gc.enable()


class TestDigitize:

    def test_forward(self):
        x = np.arange(-6, 5)
        bins = np.arange(-5, 5)
        assert_array_equal(digitize(x, bins), np.arange(11))

    def test_reverse(self):
        x = np.arange(5, -6, -1)
        bins = np.arange(5, -5, -1)
        assert_array_equal(digitize(x, bins), np.arange(11))

    def test_random(self):
        x = rand(10)
        bin = np.linspace(x.min(), x.max(), 10)
        assert_(np.all(digitize(x, bin) != 0))

    def test_right_basic(self):
        x = [1, 5, 4, 10, 8, 11, 0]
        bins = [1, 5, 10]
        default_answer = [1, 2, 1, 3, 2, 3, 0]
        assert_array_equal(digitize(x, bins), default_answer)
        right_answer = [0, 1, 1, 2, 2, 3, 0]
        assert_array_equal(digitize(x, bins, True), right_answer)

    def test_right_open(self):
        x = np.arange(-6, 5)
        bins = np.arange(-6, 4)
        assert_array_equal(digitize(x, bins, True), np.arange(11))

    def test_right_open_reverse(self):
        x = np.arange(5, -6, -1)
        bins = np.arange(4, -6, -1)
        assert_array_equal(digitize(x, bins, True), np.arange(11))

    def test_right_open_random(self):
        x = rand(10)
        bins = np.linspace(x.min(), x.max(), 10)
        assert_(np.all(digitize(x, bins, True) != 10))

    def test_monotonic(self):
        x = [-1, 0, 1, 2]
        bins = [0, 0, 1]
        assert_array_equal(digitize(x, bins, False), [0, 2, 3, 3])
        assert_array_equal(digitize(x, bins, True), [0, 0, 2, 3])
        bins = [1, 1, 0]
        assert_array_equal(digitize(x, bins, False), [3, 2, 0, 0])
        assert_array_equal(digitize(x, bins, True), [3, 3, 2, 0])
        bins = [1, 1, 1, 1]
        assert_array_equal(digitize(x, bins, False), [0, 0, 4, 4])
        assert_array_equal(digitize(x, bins, True), [0, 0, 0, 4])
        bins = [0, 0, 1, 0]
        assert_raises(ValueError, digitize, x, bins)
        bins = [1, 1, 0, 1]
        assert_raises(ValueError, digitize, x, bins)

    def test_casting_error(self):
        x = [1, 2, 3 + 1.j]
        bins = [1, 2, 3]
        assert_raises(TypeError, digitize, x, bins)
        x, bins = bins, x
        assert_raises(TypeError, digitize, x, bins)

    def test_return_type(self):
        # Functions returning indices should always return base ndarrays
        class A(np.ndarray):
            pass
        a = np.arange(5).view(A)
        b = np.arange(1, 3).view(A)
        assert_(not isinstance(digitize(b, a, False), A))
        assert_(not isinstance(digitize(b, a, True), A))

    def test_large_integers_increasing(self):
        # gh-11022
        x = 2**54  # loses precision in a float
        assert_equal(np.digitize(x, [x - 1, x + 1]), 1)

    @pytest.mark.xfail(
        reason="gh-11022: np._core.multiarray._monoticity loses precision")
    def test_large_integers_decreasing(self):
        # gh-11022
        x = 2**54  # loses precision in a float
        assert_equal(np.digitize(x, [x + 1, x - 1]), 1)


class TestUnwrap:

    def test_simple(self):
        # check that unwrap removes jumps greater that 2*pi
        assert_array_equal(unwrap([1, 1 + 2 * np.pi]), [1, 1])
        # check that unwrap maintains continuity
        assert_(np.all(diff(unwrap(rand(10) * 100)) < np.pi))

    def test_period(self):
        # check that unwrap removes jumps greater that 255
        assert_array_equal(unwrap([1, 1 + 256], period=255), [1, 2])
        # check that unwrap maintains continuity
        assert_(np.all(diff(unwrap(rand(10) * 1000, period=255)) < 255))
        # check simple case
        simple_seq = np.array([0, 75, 150, 225, 300])
        wrap_seq = np.mod(simple_seq, 255)
        assert_array_equal(unwrap(wrap_seq, period=255), simple_seq)
        # check custom discont value
        uneven_seq = np.array([0, 75, 150, 225, 300, 430])
        wrap_uneven = np.mod(uneven_seq, 250)
        no_discont = unwrap(wrap_uneven, period=250)
        assert_array_equal(no_discont, [0, 75, 150, 225, 300, 180])
        sm_discont = unwrap(wrap_uneven, period=250, discont=140)
        assert_array_equal(sm_discont, [0, 75, 150, 225, 300, 430])
        assert sm_discont.dtype == wrap_uneven.dtype


@pytest.mark.parametrize(
    "dtype", "O" + np.typecodes["AllInteger"] + np.typecodes["Float"]
)
@pytest.mark.parametrize("M", [0, 1, 10])
class TestFilterwindows:

    def test_hanning(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = hanning(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 4.500, 4)

    def test_hamming(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = hamming(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 4.9400, 4)

    def test_bartlett(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = bartlett(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 4.4444, 4)

    def test_blackman(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = blackman(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 3.7800, 4)

    def test_kaiser(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = kaiser(scalar, 0)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 10, 15)


class TestTrapezoid:

    def test_simple(self):
        x = np.arange(-10, 10, .1)
        r = trapezoid(np.exp(-.5 * x ** 2) / np.sqrt(2 * np.pi), dx=0.1)
        # check integral of normal equals 1
        assert_almost_equal(r, 1, 7)

    def test_ndim(self):
        x = np.linspace(0, 1, 3)
        y = np.linspace(0, 2, 8)
        z = np.linspace(0, 3, 13)

        wx = np.ones_like(x) * (x[1] - x[0])
        wx[0] /= 2
        wx[-1] /= 2
        wy = np.ones_like(y) * (y[1] - y[0])
        wy[0] /= 2
        wy[-1] /= 2
        wz = np.ones_like(z) * (z[1] - z[0])
        wz[0] /= 2
        wz[-1] /= 2

        q = x[:, None, None] + y[None, :, None] + z[None, None, :]

        qx = (q * wx[:, None, None]).sum(axis=0)
        qy = (q * wy[None, :, None]).sum(axis=1)
        qz = (q * wz[None, None, :]).sum(axis=2)

        # n-d `x`
        r = trapezoid(q, x=x[:, None, None], axis=0)
        assert_almost_equal(r, qx)
        r = trapezoid(q, x=y[None, :, None], axis=1)
        assert_almost_equal(r, qy)
        r = trapezoid(q, x=z[None, None, :], axis=2)
        assert_almost_equal(r, qz)

        # 1-d `x`
        r = trapezoid(q, x=x, axis=0)
        assert_almost_equal(r, qx)
        r = trapezoid(q, x=y, axis=1)
        assert_almost_equal(r, qy)
        r = trapezoid(q, x=z, axis=2)
        assert_almost_equal(r, qz)

    def test_masked(self):
        # Testing that masked arrays behave as if the function is 0 where
        # masked
        x = np.arange(5)
        y = x * x
        mask = x == 2
        ym = np.ma.array(y, mask=mask)
        r = 13.0  # sum(0.5 * (0 + 1) * 1.0 + 0.5 * (9 + 16))
        assert_almost_equal(trapezoid(ym, x), r)

        xm = np.ma.array(x, mask=mask)
        assert_almost_equal(trapezoid(ym, xm), r)

        xm = np.ma.array(x, mask=mask)
        assert_almost_equal(trapezoid(y, xm), r)


class TestSinc:

    def test_simple(self):
        assert_(sinc(0) == 1)
        w = sinc(np.linspace(-1, 1, 100))
        # check symmetry
        assert_array_almost_equal(w, flipud(w), 7)

    def test_array_like(self):
        x = [0, 0.5]
        y1 = sinc(np.array(x))
        y2 = sinc(list(x))
        y3 = sinc(tuple(x))
        assert_array_equal(y1, y2)
        assert_array_equal(y1, y3)

    def test_bool_dtype(self):
        x = (np.arange(4, dtype=np.uint8) % 2 == 1)
        actual = sinc(x)
        expected = sinc(x.astype(np.float64))
        assert_allclose(actual, expected)
        assert actual.dtype == np.float64

    @pytest.mark.parametrize('dtype', [np.uint8, np.int16, np.uint64])
    def test_int_dtypes(self, dtype):
        x = np.arange(4, dtype=dtype)
        actual = sinc(x)
        expected = sinc(x.astype(np.float64))
        assert_allclose(actual, expected)
        assert actual.dtype == np.float64

    @pytest.mark.parametrize(
            'dtype',
            [np.float16, np.float32, np.longdouble, np.complex64, np.complex128]
    )
    def test_float_dtypes(self, dtype):
        x = np.arange(4, dtype=dtype)
        assert sinc(x).dtype == x.dtype

    def test_float16_underflow(self):
        x = np.float16(0)
        # before gh-27784, fill value for 0 in input would underflow float16,
        # resulting in nan
        assert_array_equal(sinc(x), np.asarray(1.0))

class TestUnique:

    def test_simple(self):
        x = np.array([4, 3, 2, 1, 1, 2, 3, 4, 0])
        assert_(np.all(unique(x) == [0, 1, 2, 3, 4]))
        assert_(unique(np.array([1, 1, 1, 1, 1])) == np.array([1]))
        x = ['widget', 'ham', 'foo', 'bar', 'foo', 'ham']
        assert_(np.all(unique(x) == ['bar', 'foo', 'ham', 'widget']))
        x = np.array([5 + 6j, 1 + 1j, 1 + 10j, 10, 5 + 6j])
        assert_(np.all(unique(x) == [1 + 1j, 1 + 10j, 5 + 6j, 10]))


class TestCheckFinite:

    def test_simple(self):
        a = [1, 2, 3]
        b = [1, 2, np.inf]
        c = [1, 2, np.nan]
        np.asarray_chkfinite(a)
        assert_raises(ValueError, np.asarray_chkfinite, b)
        assert_raises(ValueError, np.asarray_chkfinite, c)

    def test_dtype_order(self):
        # Regression test for missing dtype and order arguments
        a = [1, 2, 3]
        a = np.asarray_chkfinite(a, order='F', dtype=np.float64)
        assert_(a.dtype == np.float64)


class TestCorrCoef:
    A = np.array(
        [[0.15391142, 0.18045767, 0.14197213],
         [0.70461506, 0.96474128, 0.27906989],
         [0.9297531, 0.32296769, 0.19267156]])
    B = np.array(
        [[0.10377691, 0.5417086, 0.49807457],
         [0.82872117, 0.77801674, 0.39226705],
         [0.9314666, 0.66800209, 0.03538394]])
    res1 = np.array(
        [[1., 0.9379533, -0.04931983],
         [0.9379533, 1., 0.30007991],
         [-0.04931983, 0.30007991, 1.]])
    res2 = np.array(
        [[1., 0.9379533, -0.04931983, 0.30151751, 0.66318558, 0.51532523],
         [0.9379533, 1., 0.30007991, -0.04781421, 0.88157256, 0.78052386],
         [-0.04931983, 0.30007991, 1., -0.96717111, 0.71483595, 0.83053601],
         [0.30151751, -0.04781421, -0.96717111, 1., -0.51366032, -0.66173113],
         [0.66318558, 0.88157256, 0.71483595, -0.51366032, 1., 0.98317823],
         [0.51532523, 0.78052386, 0.83053601, -0.66173113, 0.98317823, 1.]])

    def test_non_array(self):
        assert_almost_equal(np.corrcoef([0, 1, 0], [1, 0, 1]),
                            [[1., -1.], [-1., 1.]])

    def test_simple(self):
        tgt1 = corrcoef(self.A)
        assert_almost_equal(tgt1, self.res1)
        assert_(np.all(np.abs(tgt1) <= 1.0))

        tgt2 = corrcoef(self.A, self.B)
        assert_almost_equal(tgt2, self.res2)
        assert_(np.all(np.abs(tgt2) <= 1.0))

    def test_ddof(self):
        # ddof raises DeprecationWarning
        with suppress_warnings() as sup:
            warnings.simplefilter("always")
            assert_warns(DeprecationWarning, corrcoef, self.A, ddof=-1)
            sup.filter(DeprecationWarning)
            # ddof has no or negligible effect on the function
            assert_almost_equal(corrcoef(self.A, ddof=-1), self.res1)
            assert_almost_equal(corrcoef(self.A, self.B, ddof=-1), self.res2)
            assert_almost_equal(corrcoef(self.A, ddof=3), self.res1)
            assert_almost_equal(corrcoef(self.A, self.B, ddof=3), self.res2)

    def test_bias(self):
        # bias raises DeprecationWarning
        with suppress_warnings() as sup:
            warnings.simplefilter("always")
            assert_warns(DeprecationWarning, corrcoef, self.A, self.B, 1, 0)
            assert_warns(DeprecationWarning, corrcoef, self.A, bias=0)
            sup.filter(DeprecationWarning)
            # bias has no or negligible effect on the function
            assert_almost_equal(corrcoef(self.A, bias=1), self.res1)

    def test_complex(self):
        x = np.array([[1, 2, 3], [1j, 2j, 3j]])
        res = corrcoef(x)
        tgt = np.array([[1., -1.j], [1.j, 1.]])
        assert_allclose(res, tgt)
        assert_(np.all(np.abs(res) <= 1.0))

    def test_xy(self):
        x = np.array([[1, 2, 3]])
        y = np.array([[1j, 2j, 3j]])
        assert_allclose(np.corrcoef(x, y), np.array([[1., -1.j], [1.j, 1.]]))

    def test_empty(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RuntimeWarning)
            assert_array_equal(corrcoef(np.array([])), np.nan)
            assert_array_equal(corrcoef(np.array([]).reshape(0, 2)),
                               np.array([]).reshape(0, 0))
            assert_array_equal(corrcoef(np.array([]).reshape(2, 0)),
                               np.array([[np.nan, np.nan], [np.nan, np.nan]]))

    def test_extreme(self):
        x = [[1e-100, 1e100], [1e100, 1e-100]]
        with np.errstate(all='raise'):
            c = corrcoef(x)
        assert_array_almost_equal(c, np.array([[1., -1.], [-1., 1.]]))
        assert_(np.all(np.abs(c) <= 1.0))

    @pytest.mark.parametrize("test_type", [np.half, np.single, np.double, np.longdouble])
    def test_corrcoef_dtype(self, test_type):
        cast_A = self.A.astype(test_type)
        res = corrcoef(cast_A, dtype=test_type)
        assert test_type == res.dtype


class TestCov:
    x1 = np.array([[0, 2], [1, 1], [2, 0]]).T
    res1 = np.array([[1., -1.], [-1., 1.]])
    x2 = np.array([0.0, 1.0, 2.0], ndmin=2)
    frequencies = np.array([1, 4, 1])
    x2_repeats = np.array([[0.0], [1.0], [1.0], [1.0], [1.0], [2.0]]).T
    res2 = np.array([[0.4, -0.4], [-0.4, 0.4]])
    unit_frequencies = np.ones(3, dtype=np.int_)
    weights = np.array([1.0, 4.0, 1.0])
    res3 = np.array([[2. / 3., -2. / 3.], [-2. / 3., 2. / 3.]])
    unit_weights = np.ones(3)
    x3 = np.array([0.3942, 0.5969, 0.7730, 0.9918, 0.7964])

    def test_basic(self):
        assert_allclose(cov(self.x1), self.res1)

    def test_complex(self):
        x = np.array([[1, 2, 3], [1j, 2j, 3j]])
        res = np.array([[1., -1.j], [1.j, 1.]])
        assert_allclose(cov(x), res)
        assert_allclose(cov(x, aweights=np.ones(3)), res)

    def test_xy(self):
        x = np.array([[1, 2, 3]])
        y = np.array([[1j, 2j, 3j]])
        assert_allclose(cov(x, y), np.array([[1., -1.j], [1.j, 1.]]))

    def test_empty(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RuntimeWarning)
            assert_array_equal(cov(np.array([])), np.nan)
            assert_array_equal(cov(np.array([]).reshape(0, 2)),
                               np.array([]).reshape(0, 0))
            assert_array_equal(cov(np.array([]).reshape(2, 0)),
                               np.array([[np.nan, np.nan], [np.nan, np.nan]]))

    def test_wrong_ddof(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RuntimeWarning)
            assert_array_equal(cov(self.x1, ddof=5),
                               np.array([[np.inf, -np.inf],
                                         [-np.inf, np.inf]]))

    def test_1D_rowvar(self):
        assert_allclose(cov(self.x3), cov(self.x3, rowvar=False))
        y = np.array([0.0780, 0.3107, 0.2111, 0.0334, 0.8501])
        assert_allclose(cov(self.x3, y), cov(self.x3, y, rowvar=False))

    def test_1D_variance(self):
        assert_allclose(cov(self.x3, ddof=1), np.var(self.x3, ddof=1))

    def test_fweights(self):
        assert_allclose(cov(self.x2, fweights=self.frequencies),
                        cov(self.x2_repeats))
        assert_allclose(cov(self.x1, fweights=self.frequencies),
                        self.res2)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies),
                        self.res1)
        nonint = self.frequencies + 0.5
        assert_raises(TypeError, cov, self.x1, fweights=nonint)
        f = np.ones((2, 3), dtype=np.int_)
        assert_raises(RuntimeError, cov, self.x1, fweights=f)
        f = np.ones(2, dtype=np.int_)
        assert_raises(RuntimeError, cov, self.x1, fweights=f)
        f = -1 * np.ones(3, dtype=np.int_)
        assert_raises(ValueError, cov, self.x1, fweights=f)

    def test_aweights(self):
        assert_allclose(cov(self.x1, aweights=self.weights), self.res3)
        assert_allclose(cov(self.x1, aweights=3.0 * self.weights),
                        cov(self.x1, aweights=self.weights))
        assert_allclose(cov(self.x1, aweights=self.unit_weights), self.res1)
        w = np.ones((2, 3))
        assert_raises(RuntimeError, cov, self.x1, aweights=w)
        w = np.ones(2)
        assert_raises(RuntimeError, cov, self.x1, aweights=w)
        w = -1.0 * np.ones(3)
        assert_raises(ValueError, cov, self.x1, aweights=w)

    def test_unit_fweights_and_aweights(self):
        assert_allclose(cov(self.x2, fweights=self.frequencies,
                            aweights=self.unit_weights),
                        cov(self.x2_repeats))
        assert_allclose(cov(self.x1, fweights=self.frequencies,
                            aweights=self.unit_weights),
                        self.res2)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=self.unit_weights),
                        self.res1)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=self.weights),
                        self.res3)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=3.0 * self.weights),
                        cov(self.x1, aweights=self.weights))
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=self.unit_weights),
                        self.res1)

    @pytest.mark.parametrize("test_type", [np.half, np.single, np.double, np.longdouble])
    def test_cov_dtype(self, test_type):
        cast_x1 = self.x1.astype(test_type)
        res = cov(cast_x1, dtype=test_type)
        assert test_type == res.dtype

    def test_gh_27658(self):
        x = np.ones((3, 1))
        expected = np.cov(x, ddof=0, rowvar=True)
        actual = np.cov(x.T, ddof=0, rowvar=False)
        assert_allclose(actual, expected, strict=True)


class Test_I0:

    def test_simple(self):
        assert_almost_equal(
            i0(0.5),
            np.array(1.0634833707413234))

        # need at least one test above 8, as the implementation is piecewise
        A = np.array([0.49842636, 0.6969809, 0.22011976, 0.0155549, 10.0])
        expected = np.array([1.06307822, 1.12518299, 1.01214991, 1.00006049, 2815.71662847])
        assert_almost_equal(i0(A), expected)
        assert_almost_equal(i0(-A), expected)

        B = np.array([[0.827002, 0.99959078],
                      [0.89694769, 0.39298162],
                      [0.37954418, 0.05206293],
                      [0.36465447, 0.72446427],
                      [0.48164949, 0.50324519]])
        assert_almost_equal(
            i0(B),
            np.array([[1.17843223, 1.26583466],
                      [1.21147086, 1.03898290],
                      [1.03633899, 1.00067775],
                      [1.03352052, 1.13557954],
                      [1.05884290, 1.06432317]]))
        # Regression test for gh-11205
        i0_0 = np.i0([0.])
        assert_equal(i0_0.shape, (1,))
        assert_array_equal(np.i0([0.]), np.array([1.]))

    def test_non_array(self):
        a = np.arange(4)

        class array_like:
            __array_interface__ = a.__array_interface__

            def __array_wrap__(self, arr, context, return_scalar):
                return self

        # E.g. pandas series survive ufunc calls through array-wrap:
        assert isinstance(np.abs(array_like()), array_like)
        exp = np.i0(a)
        res = np.i0(array_like())

        assert_array_equal(exp, res)

    def test_complex(self):
        a = np.array([0, 1 + 2j])
        with pytest.raises(TypeError, match="i0 not supported for complex values"):
            res = i0(a)


class TestKaiser:

    def test_simple(self):
        assert_(np.isfinite(kaiser(1, 1.0)))
        assert_almost_equal(kaiser(0, 1.0),
                            np.array([]))
        assert_almost_equal(kaiser(2, 1.0),
                            np.array([0.78984831, 0.78984831]))
        assert_almost_equal(kaiser(5, 1.0),
                            np.array([0.78984831, 0.94503323, 1.,
                                      0.94503323, 0.78984831]))
        assert_almost_equal(kaiser(5, 1.56789),
                            np.array([0.58285404, 0.88409679, 1.,
                                      0.88409679, 0.58285404]))

    def test_int_beta(self):
        kaiser(3, 4)


class TestMeshgrid:

    def test_simple(self):
        [X, Y] = meshgrid([1, 2, 3], [4, 5, 6, 7])
        assert_array_equal(X, np.array([[1, 2, 3],
                                        [1, 2, 3],
                                        [1, 2, 3],
                                        [1, 2, 3]]))
        assert_array_equal(Y, np.array([[4, 4, 4],
                                        [5, 5, 5],
                                        [6, 6, 6],
                                        [7, 7, 7]]))

    def test_single_input(self):
        [X] = meshgrid([1, 2, 3, 4])
        assert_array_equal(X, np.array([1, 2, 3, 4]))

    def test_no_input(self):
        args = []
        assert_array_equal([], meshgrid(*args))
        assert_array_equal([], meshgrid(*args, copy=False))

    def test_indexing(self):
        x = [1, 2, 3]
        y = [4, 5, 6, 7]
        [X, Y] = meshgrid(x, y, indexing='ij')
        assert_array_equal(X, np.array([[1, 1, 1, 1],
                                        [2, 2, 2, 2],
                                        [3, 3, 3, 3]]))
        assert_array_equal(Y, np.array([[4, 5, 6, 7],
                                        [4, 5, 6, 7],
                                        [4, 5, 6, 7]]))

        # Test expected shapes:
        z = [8, 9]
        assert_(meshgrid(x, y)[0].shape == (4, 3))
        assert_(meshgrid(x, y, indexing='ij')[0].shape == (3, 4))
        assert_(meshgrid(x, y, z)[0].shape == (4, 3, 2))
        assert_(meshgrid(x, y, z, indexing='ij')[0].shape == (3, 4, 2))

        assert_raises(ValueError, meshgrid, x, y, indexing='notvalid')

    def test_sparse(self):
        [X, Y] = meshgrid([1, 2, 3], [4, 5, 6, 7], sparse=True)
        assert_array_equal(X, np.array([[1, 2, 3]]))
        assert_array_equal(Y, np.array([[4], [5], [6], [7]]))

    def test_invalid_arguments(self):
        # Test that meshgrid complains about invalid arguments
        # Regression test for issue #4755:
        # https://github.com/numpy/numpy/issues/4755
        assert_raises(TypeError, meshgrid,
                      [1, 2, 3], [4, 5, 6, 7], indices='ij')

    def test_return_type(self):
        # Test for appropriate dtype in returned arrays.
        # Regression test for issue #5297
        # https://github.com/numpy/numpy/issues/5297
        x = np.arange(0, 10, dtype=np.float32)
        y = np.arange(10, 20, dtype=np.float64)

        X, Y = np.meshgrid(x, y)

        assert_(X.dtype == x.dtype)
        assert_(Y.dtype == y.dtype)

        # copy
        X, Y = np.meshgrid(x, y, copy=True)

        assert_(X.dtype == x.dtype)
        assert_(Y.dtype == y.dtype)

        # sparse
        X, Y = np.meshgrid(x, y, sparse=True)

        assert_(X.dtype == x.dtype)
        assert_(Y.dtype == y.dtype)

    def test_writeback(self):
        # Issue 8561
        X = np.array([1.1, 2.2])
        Y = np.array([3.3, 4.4])
        x, y = np.meshgrid(X, Y, sparse=False, copy=True)

        x[0, :] = 0
        assert_equal(x[0, :], 0)
        assert_equal(x[1, :], X)

    def test_nd_shape(self):
        a, b, c, d, e = np.meshgrid(*([0] * i for i in range(1, 6)))
        expected_shape = (2, 1, 3, 4, 5)
        assert_equal(a.shape, expected_shape)
        assert_equal(b.shape, expected_shape)
        assert_equal(c.shape, expected_shape)
        assert_equal(d.shape, expected_shape)
        assert_equal(e.shape, expected_shape)

    def test_nd_values(self):
        a, b, c = np.meshgrid([0], [1, 2], [3, 4, 5])
        assert_equal(a, [[[0, 0, 0]], [[0, 0, 0]]])
        assert_equal(b, [[[1, 1, 1]], [[2, 2, 2]]])
        assert_equal(c, [[[3, 4, 5]], [[3, 4, 5]]])

    def test_nd_indexing(self):
        a, b, c = np.meshgrid([0], [1, 2], [3, 4, 5], indexing='ij')
        assert_equal(a, [[[0, 0, 0], [0, 0, 0]]])
        assert_equal(b, [[[1, 1, 1], [2, 2, 2]]])
        assert_equal(c, [[[3, 4, 5], [3, 4, 5]]])


class TestPiecewise:

    def test_simple(self):
        # Condition is single bool list
        x = piecewise([0, 0], [True, False], [1])
        assert_array_equal(x, [1, 0])

        # List of conditions: single bool list
        x = piecewise([0, 0], [[True, False]], [1])
        assert_array_equal(x, [1, 0])

        # Conditions is single bool array
        x = piecewise([0, 0], np.array([True, False]), [1])
        assert_array_equal(x, [1, 0])

        # Condition is single int array
        x = piecewise([0, 0], np.array([1, 0]), [1])
        assert_array_equal(x, [1, 0])

        # List of conditions: int array
        x = piecewise([0, 0], [np.array([1, 0])], [1])
        assert_array_equal(x, [1, 0])

        x = piecewise([0, 0], [[False, True]], [lambda x:-1])
        assert_array_equal(x, [0, -1])

        assert_raises_regex(ValueError, '1 or 2 functions are expected',
            piecewise, [0, 0], [[False, True]], [])
        assert_raises_regex(ValueError, '1 or 2 functions are expected',
            piecewise, [0, 0], [[False, True]], [1, 2, 3])

    def test_two_conditions(self):
        x = piecewise([1, 2], [[True, False], [False, True]], [3, 4])
        assert_array_equal(x, [3, 4])

    def test_scalar_domains_three_conditions(self):
        x = piecewise(3, [True, False, False], [4, 2, 0])
        assert_equal(x, 4)

    def test_default(self):
        # No value specified for x[1], should be 0
        x = piecewise([1, 2], [True, False], [2])
        assert_array_equal(x, [2, 0])

        # Should set x[1] to 3
        x = piecewise([1, 2], [True, False], [2, 3])
        assert_array_equal(x, [2, 3])

    def test_0d(self):
        x = np.array(3)
        y = piecewise(x, x > 3, [4, 0])
        assert_(y.ndim == 0)
        assert_(y == 0)

        x = 5
        y = piecewise(x, [True, False], [1, 0])
        assert_(y.ndim == 0)
        assert_(y == 1)

        # With 3 ranges (It was failing, before)
        y = piecewise(x, [False, False, True], [1, 2, 3])
        assert_array_equal(y, 3)

    def test_0d_comparison(self):
        x = 3
        y = piecewise(x, [x <= 3, x > 3], [4, 0])  # Should succeed.
        assert_equal(y, 4)

        # With 3 ranges (It was failing, before)
        x = 4
        y = piecewise(x, [x <= 3, (x > 3) * (x <= 5), x > 5], [1, 2, 3])
        assert_array_equal(y, 2)

        assert_raises_regex(ValueError, '2 or 3 functions are expected',
            piecewise, x, [x <= 3, x > 3], [1])
        assert_raises_regex(ValueError, '2 or 3 functions are expected',
            piecewise, x, [x <= 3, x > 3], [1, 1, 1, 1])

    def test_0d_0d_condition(self):
        x = np.array(3)
        c = np.array(x > 3)
        y = piecewise(x, [c], [1, 2])
        assert_equal(y, 2)

    def test_multidimensional_extrafunc(self):
        x = np.array([[-2.5, -1.5, -0.5],
                      [0.5, 1.5, 2.5]])
        y = piecewise(x, [x < 0, x >= 2], [-1, 1, 3])
        assert_array_equal(y, np.array([[-1., -1., -1.],
                                        [3., 3., 1.]]))

    def test_subclasses(self):
        class subclass(np.ndarray):
            pass
        x = np.arange(5.).view(subclass)
        r = piecewise(x, [x < 2., x >= 4], [-1., 1., 0.])
        assert_equal(type(r), subclass)
        assert_equal(r, [-1., -1., 0., 0., 1.])


class TestBincount:

    def test_simple(self):
        y = np.bincount(np.arange(4))
        assert_array_equal(y, np.ones(4))

    def test_simple2(self):
        y = np.bincount(np.array([1, 5, 2, 4, 1]))
        assert_array_equal(y, np.array([0, 2, 1, 0, 1, 1]))

    def test_simple_weight(self):
        x = np.arange(4)
        w = np.array([0.2, 0.3, 0.5, 0.1])
        y = np.bincount(x, w)
        assert_array_equal(y, w)

    def test_simple_weight2(self):
        x = np.array([1, 2, 4, 5, 2])
        w = np.array([0.2, 0.3, 0.5, 0.1, 0.2])
        y = np.bincount(x, w)
        assert_array_equal(y, np.array([0, 0.2, 0.5, 0, 0.5, 0.1]))

    def test_with_minlength(self):
        x = np.array([0, 1, 0, 1, 1])
        y = np.bincount(x, minlength=3)
        assert_array_equal(y, np.array([2, 3, 0]))
        x = []
        y = np.bincount(x, minlength=0)
        assert_array_equal(y, np.array([]))

    def test_with_minlength_smaller_than_maxvalue(self):
        x = np.array([0, 1, 1, 2, 2, 3, 3])
        y = np.bincount(x, minlength=2)
        assert_array_equal(y, np.array([1, 2, 2, 2]))
        y = np.bincount(x, minlength=0)
        assert_array_equal(y, np.array([1, 2, 2, 2]))

    def test_with_minlength_and_weights(self):
        x = np.array([1, 2, 4, 5, 2])
        w = np.array([0.2, 0.3, 0.5, 0.1, 0.2])
        y = np.bincount(x, w, 8)
        assert_array_equal(y, np.array([0, 0.2, 0.5, 0, 0.5, 0.1, 0, 0]))

    def test_empty(self):
        x = np.array([], dtype=int)
        y = np.bincount(x)
        assert_array_equal(x, y)

    def test_empty_with_minlength(self):
        x = np.array([], dtype=int)
        y = np.bincount(x, minlength=5)
        assert_array_equal(y, np.zeros(5, dtype=int))

    @pytest.mark.parametrize('minlength', [0, 3])
    def test_empty_list(self, minlength):
        assert_array_equal(np.bincount([], minlength=minlength),
                           np.zeros(minlength, dtype=int))

    def test_with_incorrect_minlength(self):
        x = np.array([], dtype=int)
        assert_raises_regex(TypeError,
                            "'str' object cannot be interpreted",
                            lambda: np.bincount(x, minlength="foobar"))
        assert_raises_regex(ValueError,
                            "must not be negative",
                            lambda: np.bincount(x, minlength=-1))

        x = np.arange(5)
        assert_raises_regex(TypeError,
                            "'str' object cannot be interpreted",
                            lambda: np.bincount(x, minlength="foobar"))
        assert_raises_regex(ValueError,
                            "must not be negative",
                            lambda: np.bincount(x, minlength=-1))

    @pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
    def test_dtype_reference_leaks(self):
        # gh-6805
        intp_refcount = sys.getrefcount(np.dtype(np.intp))
        double_refcount = sys.getrefcount(np.dtype(np.double))

        for j in range(10):
            np.bincount([1, 2, 3])
        assert_equal(sys.getrefcount(np.dtype(np.intp)), intp_refcount)
        assert_equal(sys.getrefcount(np.dtype(np.double)), double_refcount)

        for j in range(10):
            np.bincount([1, 2, 3], [4, 5, 6])
        assert_equal(sys.getrefcount(np.dtype(np.intp)), intp_refcount)
        assert_equal(sys.getrefcount(np.dtype(np.double)), double_refcount)

    @pytest.mark.parametrize("vals", [[[2, 2]], 2])
    def test_error_not_1d(self, vals):
        # Test that values has to be 1-D (both as array and nested list)
        vals_arr = np.asarray(vals)
        with assert_raises(ValueError):
            np.bincount(vals_arr)
        with assert_raises(ValueError):
            np.bincount(vals)

    @pytest.mark.parametrize("dt", np.typecodes["AllInteger"])
    def test_gh_28354(self, dt):
        a = np.array([0, 1, 1, 3, 2, 1, 7], dtype=dt)
        actual = np.bincount(a)
        expected = [1, 3, 1, 1, 0, 0, 0, 1]
        assert_array_equal(actual, expected)

    def test_contiguous_handling(self):
        # check for absence of hard crash
        np.bincount(np.arange(10000)[::2])

    def test_gh_28354_array_like(self):
        class A:
            def __array__(self):
                return np.array([0, 1, 1, 3, 2, 1, 7], dtype=np.uint64)

        a = A()
        actual = np.bincount(a)
        expected = [1, 3, 1, 1, 0, 0, 0, 1]
        assert_array_equal(actual, expected)


class TestInterp:

    def test_exceptions(self):
        assert_raises(ValueError, interp, 0, [], [])
        assert_raises(ValueError, interp, 0, [0], [1, 2])
        assert_raises(ValueError, interp, 0, [0, 1], [1, 2], period=0)
        assert_raises(ValueError, interp, 0, [], [], period=360)
        assert_raises(ValueError, interp, 0, [0], [1, 2], period=360)

    def test_basic(self):
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5)
        x0 = np.linspace(0, 1, 50)
        assert_almost_equal(np.interp(x0, x, y), x0)

    def test_right_left_behavior(self):
        # Needs range of sizes to test different code paths.
        # size ==1 is special cased, 1 < size < 5 is linear search, and
        # size >= 5 goes through local search and possibly binary search.
        for size in range(1, 10):
            xp = np.arange(size, dtype=np.double)
            yp = np.ones(size, dtype=np.double)
            incpts = np.array([-1, 0, size - 1, size], dtype=np.double)
            decpts = incpts[::-1]

            incres = interp(incpts, xp, yp)
            decres = interp(decpts, xp, yp)
            inctgt = np.array([1, 1, 1, 1], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

            incres = interp(incpts, xp, yp, left=0)
            decres = interp(decpts, xp, yp, left=0)
            inctgt = np.array([0, 1, 1, 1], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

            incres = interp(incpts, xp, yp, right=2)
            decres = interp(decpts, xp, yp, right=2)
            inctgt = np.array([1, 1, 1, 2], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

            incres = interp(incpts, xp, yp, left=0, right=2)
            decres = interp(decpts, xp, yp, left=0, right=2)
            inctgt = np.array([0, 1, 1, 2], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

    def test_scalar_interpolation_point(self):
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5)
        x0 = 0
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = .3
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = np.float32(.3)
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = np.float64(.3)
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = np.nan
        assert_almost_equal(np.interp(x0, x, y), x0)

    def test_non_finite_behavior_exact_x(self):
        x = [1, 2, 2.5, 3, 4]
        xp = [1, 2, 3, 4]
        fp = [1, 2, np.inf, 4]
        assert_almost_equal(np.interp(x, xp, fp), [1, 2, np.inf, np.inf, 4])
        fp = [1, 2, np.nan, 4]
        assert_almost_equal(np.interp(x, xp, fp), [1, 2, np.nan, np.nan, 4])

    @pytest.fixture(params=[
        np.float64,
        lambda x: _make_complex(x, 0),
        lambda x: _make_complex(0, x),
        lambda x: _make_complex(x, np.multiply(x, -2))
    ], ids=[
        'real',
        'complex-real',
        'complex-imag',
        'complex-both'
    ])
    def sc(self, request):
        """ scale function used by the below tests """
        return request.param

    def test_non_finite_any_nan(self, sc):
        """ test that nans are propagated """
        assert_equal(np.interp(0.5, [np.nan,      1], sc([     0,     10])), sc(np.nan))
        assert_equal(np.interp(0.5, [     0, np.nan], sc([     0,     10])), sc(np.nan))
        assert_equal(np.interp(0.5, [     0,      1], sc([np.nan,     10])), sc(np.nan))
        assert_equal(np.interp(0.5, [     0,      1], sc([     0, np.nan])), sc(np.nan))

    def test_non_finite_inf(self, sc):
        """ Test that interp between opposite infs gives nan """
        assert_equal(np.interp(0.5, [-np.inf, +np.inf], sc([      0,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0,       1], sc([-np.inf, +np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0,       1], sc([+np.inf, -np.inf])), sc(np.nan))

        # unless the y values are equal
        assert_equal(np.interp(0.5, [-np.inf, +np.inf], sc([     10,      10])), sc(10))

    def test_non_finite_half_inf_xf(self, sc):
        """ Test that interp where both axes have a bound at inf gives nan """
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([-np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([+np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([      0, -np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([      0, +np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([-np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([+np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([      0, -np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([      0, +np.inf])), sc(np.nan))

    def test_non_finite_half_inf_x(self, sc):
        """ Test interp where the x axis has a bound at inf """
        assert_equal(np.interp(0.5, [-np.inf, -np.inf], sc([0, 10])), sc(10))
        assert_equal(np.interp(0.5, [-np.inf, 1      ], sc([0, 10])), sc(10))  # noqa: E202
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([0, 10])), sc(0))
        assert_equal(np.interp(0.5, [+np.inf, +np.inf], sc([0, 10])), sc(0))

    def test_non_finite_half_inf_f(self, sc):
        """ Test interp where the f axis has a bound at inf """
        assert_equal(np.interp(0.5, [0, 1], sc([      0, -np.inf])), sc(-np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([      0, +np.inf])), sc(+np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([-np.inf,      10])), sc(-np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([+np.inf,      10])), sc(+np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([-np.inf, -np.inf])), sc(-np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([+np.inf, +np.inf])), sc(+np.inf))

    def test_complex_interp(self):
        # test complex interpolation
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5) + (1 + np.linspace(0, 1, 5)) * 1.0j
        x0 = 0.3
        y0 = x0 + (1 + x0) * 1.0j
        assert_almost_equal(np.interp(x0, x, y), y0)
        # test complex left and right
        x0 = -1
        left = 2 + 3.0j
        assert_almost_equal(np.interp(x0, x, y, left=left), left)
        x0 = 2.0
        right = 2 + 3.0j
        assert_almost_equal(np.interp(x0, x, y, right=right), right)
        # test complex non finite
        x = [1, 2, 2.5, 3, 4]
        xp = [1, 2, 3, 4]
        fp = [1, 2 + 1j, np.inf, 4]
        y = [1, 2 + 1j, np.inf + 0.5j, np.inf, 4]
        assert_almost_equal(np.interp(x, xp, fp), y)
        # test complex periodic
        x = [-180, -170, -185, 185, -10, -5, 0, 365]
        xp = [190, -190, 350, -350]
        fp = [5 + 1.0j, 10 + 2j, 3 + 3j, 4 + 4j]
        y = [7.5 + 1.5j, 5. + 1.0j, 8.75 + 1.75j, 6.25 + 1.25j, 3. + 3j, 3.25 + 3.25j,
             3.5 + 3.5j, 3.75 + 3.75j]
        assert_almost_equal(np.interp(x, xp, fp, period=360), y)

    def test_zero_dimensional_interpolation_point(self):
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5)
        x0 = np.array(.3)
        assert_almost_equal(np.interp(x0, x, y), x0)

        xp = np.array([0, 2, 4])
        fp = np.array([1, -1, 1])

        actual = np.interp(np.array(1), xp, fp)
        assert_equal(actual, 0)
        assert_(isinstance(actual, np.float64))

        actual = np.interp(np.array(4.5), xp, fp, period=4)
        assert_equal(actual, 0.5)
        assert_(isinstance(actual, np.float64))

    def test_if_len_x_is_small(self):
        xp = np.arange(0, 10, 0.0001)
        fp = np.sin(xp)
        assert_almost_equal(np.interp(np.pi, xp, fp), 0.0)

    def test_period(self):
        x = [-180, -170, -185, 185, -10, -5, 0, 365]
        xp = [190, -190, 350, -350]
        fp = [5, 10, 3, 4]
        y = [7.5, 5., 8.75, 6.25, 3., 3.25, 3.5, 3.75]
        assert_almost_equal(np.interp(x, xp, fp, period=360), y)
        x = np.array(x, order='F').reshape(2, -1)
        y = np.array(y, order='C').reshape(2, -1)
        assert_almost_equal(np.interp(x, xp, fp, period=360), y)


class TestPercentile:

    def test_basic(self):
        x = np.arange(8) * 0.5
        assert_equal(np.percentile(x, 0), 0.)
        assert_equal(np.percentile(x, 100), 3.5)
        assert_equal(np.percentile(x, 50), 1.75)
        x[1] = np.nan
        assert_equal(np.percentile(x, 0), np.nan)
        assert_equal(np.percentile(x, 0, method='nearest'), np.nan)
        assert_equal(np.percentile(x, 0, method='inverted_cdf'), np.nan)
        assert_equal(
            np.percentile(x, 0, method='inverted_cdf',
                          weights=np.ones_like(x)),
            np.nan,
        )

    def test_fraction(self):
        x = [Fraction(i, 2) for i in range(8)]

        p = np.percentile(x, Fraction(0))
        assert_equal(p, Fraction(0))
        assert_equal(type(p), Fraction)

        p = np.percentile(x, Fraction(100))
        assert_equal(p, Fraction(7, 2))
        assert_equal(type(p), Fraction)

        p = np.percentile(x, Fraction(50))
        assert_equal(p, Fraction(7, 4))
        assert_equal(type(p), Fraction)

        p = np.percentile(x, [Fraction(50)])
        assert_equal(p, np.array([Fraction(7, 4)]))
        assert_equal(type(p), np.ndarray)

    def test_api(self):
        d = np.ones(5)
        np.percentile(d, 5, None, None, False)
        np.percentile(d, 5, None, None, False, 'linear')
        o = np.ones((1,))
        np.percentile(d, 5, None, o, False, 'linear')

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.percentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.percentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.percentile, arr_c, 0.5)

    def test_2D(self):
        x = np.array([[1, 1, 1],
                      [1, 1, 1],
                      [4, 4, 3],
                      [1, 1, 1],
                      [1, 1, 1]])
        assert_array_equal(np.percentile(x, 50, axis=0), [1, 1, 1])

    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    def test_linear_nan_1D(self, dtype):
        # METHOD 1 of H&F
        arr = np.asarray([15.0, np.nan, 35.0, 40.0, 50.0], dtype=dtype)
        res = np.percentile(
            arr,
            40.0,
            method="linear")
        np.testing.assert_equal(res, np.nan)
        np.testing.assert_equal(res.dtype, arr.dtype)

    H_F_TYPE_CODES = [(int_type, np.float64)
                      for int_type in np.typecodes["AllInteger"]
                      ] + [(np.float16, np.float16),
                           (np.float32, np.float32),
                           (np.float64, np.float64),
                           (np.longdouble, np.longdouble),
                           (np.dtype("O"), np.float64)]

    @pytest.mark.parametrize(["function", "quantile"],
                             [(np.quantile, 0.4),
                              (np.percentile, 40.0)])
    @pytest.mark.parametrize(["input_dtype", "expected_dtype"], H_F_TYPE_CODES)
    @pytest.mark.parametrize(["method", "weighted", "expected"],
                              [("inverted_cdf", False, 20),
                              ("inverted_cdf", True, 20),
                              ("averaged_inverted_cdf", False, 27.5),
                              ("closest_observation", False, 20),
                              ("interpolated_inverted_cdf", False, 20),
                              ("hazen", False, 27.5),
                              ("weibull", False, 26),
                              ("linear", False, 29),
                              ("median_unbiased", False, 27),
                              ("normal_unbiased", False, 27.125),
                               ])
    def test_linear_interpolation(self,
                                  function,
                                  quantile,
                                  method,
                                  weighted,
                                  expected,
                                  input_dtype,
                                  expected_dtype):
        expected_dtype = np.dtype(expected_dtype)

        arr = np.asarray([15.0, 20.0, 35.0, 40.0, 50.0], dtype=input_dtype)
        weights = np.ones_like(arr) if weighted else None
        if input_dtype is np.longdouble:
            if function is np.quantile:
                # 0.4 is not exactly representable and it matters
                # for "averaged_inverted_cdf", so we need to cheat.
                quantile = input_dtype("0.4")
            # We want to use nulp, but that does not work for longdouble
            test_function = np.testing.assert_almost_equal
        else:
            test_function = np.testing.assert_array_almost_equal_nulp

        actual = function(arr, quantile, method=method, weights=weights)

        test_function(actual, expected_dtype.type(expected))

        if method in ["inverted_cdf", "closest_observation"]:
            if input_dtype == "O":
                np.testing.assert_equal(np.asarray(actual).dtype, np.float64)
            else:
                np.testing.assert_equal(np.asarray(actual).dtype,
                                        np.dtype(input_dtype))
        else:
            np.testing.assert_equal(np.asarray(actual).dtype,
                                    np.dtype(expected_dtype))

    TYPE_CODES = np.typecodes["AllInteger"] + np.typecodes["Float"] + "O"

    @pytest.mark.parametrize("dtype", TYPE_CODES)
    def test_lower_higher(self, dtype):
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 50,
                                   method='lower'), 4)
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 50,
                                   method='higher'), 5)

    @pytest.mark.parametrize("dtype", TYPE_CODES)
    def test_midpoint(self, dtype):
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 51,
                                   method='midpoint'), 4.5)
        assert_equal(np.percentile(np.arange(9, dtype=dtype) + 1, 50,
                                   method='midpoint'), 5)
        assert_equal(np.percentile(np.arange(11, dtype=dtype), 51,
                                   method='midpoint'), 5.5)
        assert_equal(np.percentile(np.arange(11, dtype=dtype), 50,
                                   method='midpoint'), 5)

    @pytest.mark.parametrize("dtype", TYPE_CODES)
    def test_nearest(self, dtype):
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 51,
                                   method='nearest'), 5)
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 49,
                                   method='nearest'), 4)

    def test_linear_interpolation_extrapolation(self):
        arr = np.random.rand(5)

        actual = np.percentile(arr, 100)
        np.testing.assert_equal(actual, arr.max())

        actual = np.percentile(arr, 0)
        np.testing.assert_equal(actual, arr.min())

    def test_sequence(self):
        x = np.arange(8) * 0.5
        assert_equal(np.percentile(x, [0, 100, 50]), [0, 3.5, 1.75])

    def test_axis(self):
        x = np.arange(12).reshape(3, 4)

        assert_equal(np.percentile(x, (25, 50, 100)), [2.75, 5.5, 11.0])

        r0 = [[2, 3, 4, 5], [4, 5, 6, 7], [8, 9, 10, 11]]
        assert_equal(np.percentile(x, (25, 50, 100), axis=0), r0)

        r1 = [[0.75, 1.5, 3], [4.75, 5.5, 7], [8.75, 9.5, 11]]
        assert_equal(np.percentile(x, (25, 50, 100), axis=1), np.array(r1).T)

        # ensure qth axis is always first as with np.array(old_percentile(..))
        x = np.arange(3 * 4 * 5 * 6).reshape(3, 4, 5, 6)
        assert_equal(np.percentile(x, (25, 50)).shape, (2,))
        assert_equal(np.percentile(x, (25, 50, 75)).shape, (3,))
        assert_equal(np.percentile(x, (25, 50), axis=0).shape, (2, 4, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=1).shape, (2, 3, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=2).shape, (2, 3, 4, 6))
        assert_equal(np.percentile(x, (25, 50), axis=3).shape, (2, 3, 4, 5))
        assert_equal(
            np.percentile(x, (25, 50, 75), axis=1).shape, (3, 3, 5, 6))
        assert_equal(np.percentile(x, (25, 50),
                                   method="higher").shape, (2,))
        assert_equal(np.percentile(x, (25, 50, 75),
                                   method="higher").shape, (3,))
        assert_equal(np.percentile(x, (25, 50), axis=0,
                                   method="higher").shape, (2, 4, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=1,
                                   method="higher").shape, (2, 3, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=2,
                                   method="higher").shape, (2, 3, 4, 6))
        assert_equal(np.percentile(x, (25, 50), axis=3,
                                   method="higher").shape, (2, 3, 4, 5))
        assert_equal(np.percentile(x, (25, 50, 75), axis=1,
                                   method="higher").shape, (3, 3, 5, 6))

    def test_scalar_q(self):
        # test for no empty dimensions for compatibility with old percentile
        x = np.arange(12).reshape(3, 4)
        assert_equal(np.percentile(x, 50), 5.5)
        assert_(np.isscalar(np.percentile(x, 50)))
        r0 = np.array([4., 5., 6., 7.])
        assert_equal(np.percentile(x, 50, axis=0), r0)
        assert_equal(np.percentile(x, 50, axis=0).shape, r0.shape)
        r1 = np.array([1.5, 5.5, 9.5])
        assert_almost_equal(np.percentile(x, 50, axis=1), r1)
        assert_equal(np.percentile(x, 50, axis=1).shape, r1.shape)

        out = np.empty(1)
        assert_equal(np.percentile(x, 50, out=out), 5.5)
        assert_equal(out, 5.5)
        out = np.empty(4)
        assert_equal(np.percentile(x, 50, axis=0, out=out), r0)
        assert_equal(out, r0)
        out = np.empty(3)
        assert_equal(np.percentile(x, 50, axis=1, out=out), r1)
        assert_equal(out, r1)

        # test for no empty dimensions for compatibility with old percentile
        x = np.arange(12).reshape(3, 4)
        assert_equal(np.percentile(x, 50, method='lower'), 5.)
        assert_(np.isscalar(np.percentile(x, 50)))
        r0 = np.array([4., 5., 6., 7.])
        c0 = np.percentile(x, 50, method='lower', axis=0)
        assert_equal(c0, r0)
        assert_equal(c0.shape, r0.shape)
        r1 = np.array([1., 5., 9.])
        c1 = np.percentile(x, 50, method='lower', axis=1)
        assert_almost_equal(c1, r1)
        assert_equal(c1.shape, r1.shape)

        out = np.empty((), dtype=x.dtype)
        c = np.percentile(x, 50, method='lower', out=out)
        assert_equal(c, 5)
        assert_equal(out, 5)
        out = np.empty(4, dtype=x.dtype)
        c = np.percentile(x, 50, method='lower', axis=0, out=out)
        assert_equal(c, r0)
        assert_equal(out, r0)
        out = np.empty(3, dtype=x.dtype)
        c = np.percentile(x, 50, method='lower', axis=1, out=out)
        assert_equal(c, r1)
        assert_equal(out, r1)

    def test_exception(self):
        assert_raises(ValueError, np.percentile, [1, 2], 56,
                      method='foobar')
        assert_raises(ValueError, np.percentile, [1], 101)
        assert_raises(ValueError, np.percentile, [1], -1)
        assert_raises(ValueError, np.percentile, [1], list(range(50)) + [101])
        assert_raises(ValueError, np.percentile, [1], list(range(50)) + [-0.1])

    def test_percentile_list(self):
        assert_equal(np.percentile([1, 2, 3], 0), 1)

    @pytest.mark.parametrize(
        "percentile, with_weights",
        [
            (np.percentile, False),
            (partial(np.percentile, method="inverted_cdf"), True),
        ]
    )
    def test_percentile_out(self, percentile, with_weights):
        out_dtype = int if with_weights else float
        x = np.array([1, 2, 3])
        y = np.zeros((3,), dtype=out_dtype)
        p = (1, 2, 3)
        weights = np.ones_like(x) if with_weights else None
        r = percentile(x, p, out=y, weights=weights)
        assert r is y
        assert_equal(percentile(x, p, weights=weights), y)

        x = np.array([[1, 2, 3],
                      [4, 5, 6]])
        y = np.zeros((3, 3), dtype=out_dtype)
        weights = np.ones_like(x) if with_weights else None
        r = percentile(x, p, axis=0, out=y, weights=weights)
        assert r is y
        assert_equal(percentile(x, p, weights=weights, axis=0), y)

        y = np.zeros((3, 2), dtype=out_dtype)
        percentile(x, p, axis=1, out=y, weights=weights)
        assert_equal(percentile(x, p, weights=weights, axis=1), y)

        x = np.arange(12).reshape(3, 4)
        # q.dim > 1, float
        if with_weights:
            r0 = np.array([[0, 1, 2, 3], [4, 5, 6, 7]])
        else:
            r0 = np.array([[2., 3., 4., 5.], [4., 5., 6., 7.]])
        out = np.empty((2, 4), dtype=out_dtype)
        weights = np.ones_like(x) if with_weights else None
        assert_equal(
            percentile(x, (25, 50), axis=0, out=out, weights=weights), r0
        )
        assert_equal(out, r0)
        r1 = np.array([[0.75, 4.75, 8.75], [1.5, 5.5, 9.5]])
        out = np.empty((2, 3))
        assert_equal(np.percentile(x, (25, 50), axis=1, out=out), r1)
        assert_equal(out, r1)

        # q.dim > 1, int
        r0 = np.array([[0, 1, 2, 3], [4, 5, 6, 7]])
        out = np.empty((2, 4), dtype=x.dtype)
        c = np.percentile(x, (25, 50), method='lower', axis=0, out=out)
        assert_equal(c, r0)
        assert_equal(out, r0)
        r1 = np.array([[0, 4, 8], [1, 5, 9]])
        out = np.empty((2, 3), dtype=x.dtype)
        c = np.percentile(x, (25, 50), method='lower', axis=1, out=out)
        assert_equal(c, r1)
        assert_equal(out, r1)

    def test_percentile_empty_dim(self):
        # empty dims are preserved
        d = np.arange(11 * 2).reshape(11, 1, 2, 1)
        assert_array_equal(np.percentile(d, 50, axis=0).shape, (1, 2, 1))
        assert_array_equal(np.percentile(d, 50, axis=1).shape, (11, 2, 1))
        assert_array_equal(np.percentile(d, 50, axis=2).shape, (11, 1, 1))
        assert_array_equal(np.percentile(d, 50, axis=3).shape, (11, 1, 2))
        assert_array_equal(np.percentile(d, 50, axis=-1).shape, (11, 1, 2))
        assert_array_equal(np.percentile(d, 50, axis=-2).shape, (11, 1, 1))
        assert_array_equal(np.percentile(d, 50, axis=-3).shape, (11, 2, 1))
        assert_array_equal(np.percentile(d, 50, axis=-4).shape, (1, 2, 1))

        assert_array_equal(np.percentile(d, 50, axis=2,
                                         method='midpoint').shape,
                           (11, 1, 1))
        assert_array_equal(np.percentile(d, 50, axis=-2,
                                         method='midpoint').shape,
                           (11, 1, 1))

        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=0)).shape,
                           (2, 1, 2, 1))
        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=1)).shape,
                           (2, 11, 2, 1))
        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=2)).shape,
                           (2, 11, 1, 1))
        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=3)).shape,
                           (2, 11, 1, 2))

    def test_percentile_no_overwrite(self):
        a = np.array([2, 3, 4, 1])
        np.percentile(a, [50], overwrite_input=False)
        assert_equal(a, np.array([2, 3, 4, 1]))

        a = np.array([2, 3, 4, 1])
        np.percentile(a, [50])
        assert_equal(a, np.array([2, 3, 4, 1]))

    def test_no_p_overwrite(self):
        p = np.linspace(0., 100., num=5)
        np.percentile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, np.linspace(0., 100., num=5))
        p = np.linspace(0., 100., num=5).tolist()
        np.percentile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, np.linspace(0., 100., num=5).tolist())

    def test_percentile_overwrite(self):
        a = np.array([2, 3, 4, 1])
        b = np.percentile(a, [50], overwrite_input=True)
        assert_equal(b, np.array([2.5]))

        b = np.percentile([2, 3, 4, 1], [50], overwrite_input=True)
        assert_equal(b, np.array([2.5]))

    def test_extended_axis(self):
        o = np.random.normal(size=(71, 23))
        x = np.dstack([o] * 10)
        assert_equal(np.percentile(x, 30, axis=(0, 1)), np.percentile(o, 30))
        x = np.moveaxis(x, -1, 0)
        assert_equal(np.percentile(x, 30, axis=(-2, -1)), np.percentile(o, 30))
        x = x.swapaxes(0, 1).copy()
        assert_equal(np.percentile(x, 30, axis=(0, -1)), np.percentile(o, 30))
        x = x.swapaxes(0, 1).copy()

        assert_equal(np.percentile(x, [25, 60], axis=(0, 1, 2)),
                     np.percentile(x, [25, 60], axis=None))
        assert_equal(np.percentile(x, [25, 60], axis=(0,)),
                     np.percentile(x, [25, 60], axis=0))

        d = np.arange(3 * 5 * 7 * 11).reshape((3, 5, 7, 11))
        np.random.shuffle(d.ravel())
        assert_equal(np.percentile(d, 25, axis=(0, 1, 2))[0],
                     np.percentile(d[:, :, :, 0].flatten(), 25))
        assert_equal(np.percentile(d, [10, 90], axis=(0, 1, 3))[:, 1],
                     np.percentile(d[:, :, 1, :].flatten(), [10, 90]))
        assert_equal(np.percentile(d, 25, axis=(3, 1, -4))[2],
                     np.percentile(d[:, :, 2, :].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(3, 1, 2))[2],
                     np.percentile(d[2, :, :, :].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(3, 2))[2, 1],
                     np.percentile(d[2, 1, :, :].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(1, -2))[2, 1],
                     np.percentile(d[2, :, :, 1].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(1, 3))[2, 2],
                     np.percentile(d[2, :, 2, :].flatten(), 25))

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.percentile, d, axis=-5, q=25)
        assert_raises(AxisError, np.percentile, d, axis=(0, -5), q=25)
        assert_raises(AxisError, np.percentile, d, axis=4, q=25)
        assert_raises(AxisError, np.percentile, d, axis=(0, 4), q=25)
        # each of these refers to the same axis twice
        assert_raises(ValueError, np.percentile, d, axis=(1, 1), q=25)
        assert_raises(ValueError, np.percentile, d, axis=(-1, -1), q=25)
        assert_raises(ValueError, np.percentile, d, axis=(3, -1), q=25)

    def test_keepdims(self):
        d = np.ones((3, 5, 7, 11))
        assert_equal(np.percentile(d, 7, axis=None, keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.percentile(d, 7, axis=(0, 1), keepdims=True).shape,
                     (1, 1, 7, 11))
        assert_equal(np.percentile(d, 7, axis=(0, 3), keepdims=True).shape,
                     (1, 5, 7, 1))
        assert_equal(np.percentile(d, 7, axis=(1,), keepdims=True).shape,
                     (3, 1, 7, 11))
        assert_equal(np.percentile(d, 7, (0, 1, 2, 3), keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.percentile(d, 7, axis=(0, 1, 3), keepdims=True).shape,
                     (1, 1, 7, 1))

        assert_equal(np.percentile(d, [1, 7], axis=(0, 1, 3),
                                   keepdims=True).shape, (2, 1, 1, 7, 1))
        assert_equal(np.percentile(d, [1, 7], axis=(0, 3),
                                   keepdims=True).shape, (2, 1, 5, 7, 1))

    @pytest.mark.parametrize('q', [7, [1, 7]])
    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1,),
            (0, 1),
            (-3, -1),
        ]
    )
    def test_keepdims_out(self, q, axis):
        d = np.ones((3, 5, 7, 11))
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        shape_out = np.shape(q) + shape_out

        out = np.empty(shape_out)
        result = np.percentile(d, q, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    def test_out(self):
        o = np.zeros((4,))
        d = np.ones((3, 4))
        assert_equal(np.percentile(d, 0, 0, out=o), o)
        assert_equal(np.percentile(d, 0, 0, method='nearest', out=o), o)
        o = np.zeros((3,))
        assert_equal(np.percentile(d, 1, 1, out=o), o)
        assert_equal(np.percentile(d, 1, 1, method='nearest', out=o), o)

        o = np.zeros(())
        assert_equal(np.percentile(d, 2, out=o), o)
        assert_equal(np.percentile(d, 2, method='nearest', out=o), o)

    @pytest.mark.parametrize("method, weighted", [
        ("linear", False),
        ("nearest", False),
        ("inverted_cdf", False),
        ("inverted_cdf", True),
    ])
    def test_out_nan(self, method, weighted):
        if weighted:
            kwargs = {"weights": np.ones((3, 4)), "method": method}
        else:
            kwargs = {"method": method}
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', RuntimeWarning)
            o = np.zeros((4,))
            d = np.ones((3, 4))
            d[2, 1] = np.nan
            assert_equal(np.percentile(d, 0, 0, out=o, **kwargs), o)

            o = np.zeros((3,))
            assert_equal(np.percentile(d, 1, 1, out=o, **kwargs), o)

            o = np.zeros(())
            assert_equal(np.percentile(d, 1, out=o, **kwargs), o)

    def test_nan_behavior(self):
        a = np.arange(24, dtype=float)
        a[2] = np.nan
        assert_equal(np.percentile(a, 0.3), np.nan)
        assert_equal(np.percentile(a, 0.3, axis=0), np.nan)
        assert_equal(np.percentile(a, [0.3, 0.6], axis=0),
                     np.array([np.nan] * 2))

        a = np.arange(24, dtype=float).reshape(2, 3, 4)
        a[1, 2, 3] = np.nan
        a[1, 1, 2] = np.nan

        # no axis
        assert_equal(np.percentile(a, 0.3), np.nan)
        assert_equal(np.percentile(a, 0.3).ndim, 0)

        # axis0 zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4), 0.3, 0)
        b[2, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.percentile(a, 0.3, 0), b)

        # axis0 not zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4),
                          [0.3, 0.6], 0)
        b[:, 2, 3] = np.nan
        b[:, 1, 2] = np.nan
        assert_equal(np.percentile(a, [0.3, 0.6], 0), b)

        # axis1 zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4), 0.3, 1)
        b[1, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.percentile(a, 0.3, 1), b)
        # axis1 not zerod
        b = np.percentile(
            np.arange(24, dtype=float).reshape(2, 3, 4), [0.3, 0.6], 1)
        b[:, 1, 3] = np.nan
        b[:, 1, 2] = np.nan
        assert_equal(np.percentile(a, [0.3, 0.6], 1), b)

        # axis02 zerod
        b = np.percentile(
            np.arange(24, dtype=float).reshape(2, 3, 4), 0.3, (0, 2))
        b[1] = np.nan
        b[2] = np.nan
        assert_equal(np.percentile(a, 0.3, (0, 2)), b)
        # axis02 not zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4),
                          [0.3, 0.6], (0, 2))
        b[:, 1] = np.nan
        b[:, 2] = np.nan
        assert_equal(np.percentile(a, [0.3, 0.6], (0, 2)), b)
        # axis02 not zerod with method='nearest'
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4),
                          [0.3, 0.6], (0, 2), method='nearest')
        b[:, 1] = np.nan
        b[:, 2] = np.nan
        assert_equal(np.percentile(
            a, [0.3, 0.6], (0, 2), method='nearest'), b)

    def test_nan_q(self):
        # GH18830
        with pytest.raises(ValueError, match="Percentiles must be in"):
            np.percentile([1, 2, 3, 4.0], np.nan)
        with pytest.raises(ValueError, match="Percentiles must be in"):
            np.percentile([1, 2, 3, 4.0], [np.nan])
        q = np.linspace(1.0, 99.0, 16)
        q[0] = np.nan
        with pytest.raises(ValueError, match="Percentiles must be in"):
            np.percentile([1, 2, 3, 4.0], q)

    @pytest.mark.parametrize("dtype", ["m8[D]", "M8[s]"])
    @pytest.mark.parametrize("pos", [0, 23, 10])
    def test_nat_basic(self, dtype, pos):
        # TODO: Note that times have dubious rounding as of fixing NaTs!
        # NaT and NaN should behave the same, do basic tests for NaT:
        a = np.arange(0, 24, dtype=dtype)
        a[pos] = "NaT"
        res = np.percentile(a, 30)
        assert res.dtype == dtype
        assert np.isnat(res)
        res = np.percentile(a, [30, 60])
        assert res.dtype == dtype
        assert np.isnat(res).all()

        a = np.arange(0, 24 * 3, dtype=dtype).reshape(-1, 3)
        a[pos, 1] = "NaT"
        res = np.percentile(a, 30, axis=0)
        assert_array_equal(np.isnat(res), [False, True, False])


quantile_methods = [
    'inverted_cdf', 'averaged_inverted_cdf', 'closest_observation',
    'interpolated_inverted_cdf', 'hazen', 'weibull', 'linear',
    'median_unbiased', 'normal_unbiased', 'nearest', 'lower', 'higher',
    'midpoint']


methods_supporting_weights = ["inverted_cdf"]


class TestQuantile:
    # most of this is already tested by TestPercentile

    def V(self, x, y, alpha):
        # Identification function used in several tests.
        return (x >= y) - alpha

    def test_max_ulp(self):
        x = [0.0, 0.2, 0.4]
        a = np.quantile(x, 0.45)
        # The default linear method would result in 0 + 0.2 * (0.45/2) = 0.18.
        # 0.18 is not exactly representable and the formula leads to a 1 ULP
        # different result. Ensure it is this exact within 1 ULP, see gh-20331.
        np.testing.assert_array_max_ulp(a, 0.18, maxulp=1)

    def test_basic(self):
        x = np.arange(8) * 0.5
        assert_equal(np.quantile(x, 0), 0.)
        assert_equal(np.quantile(x, 1), 3.5)
        assert_equal(np.quantile(x, 0.5), 1.75)

    def test_correct_quantile_value(self):
        a = np.array([True])
        tf_quant = np.quantile(True, False)
        assert_equal(tf_quant, a[0])
        assert_equal(type(tf_quant), a.dtype)
        a = np.array([False, True, True])
        quant_res = np.quantile(a, a)
        assert_array_equal(quant_res, a)
        assert_equal(quant_res.dtype, a.dtype)

    def test_fraction(self):
        # fractional input, integral quantile
        x = [Fraction(i, 2) for i in range(8)]
        q = np.quantile(x, 0)
        assert_equal(q, 0)
        assert_equal(type(q), Fraction)

        q = np.quantile(x, 1)
        assert_equal(q, Fraction(7, 2))
        assert_equal(type(q), Fraction)

        q = np.quantile(x, .5)
        assert_equal(q, 1.75)
        assert_equal(type(q), np.float64)

        q = np.quantile(x, Fraction(1, 2))
        assert_equal(q, Fraction(7, 4))
        assert_equal(type(q), Fraction)

        q = np.quantile(x, [Fraction(1, 2)])
        assert_equal(q, np.array([Fraction(7, 4)]))
        assert_equal(type(q), np.ndarray)

        q = np.quantile(x, [[Fraction(1, 2)]])
        assert_equal(q, np.array([[Fraction(7, 4)]]))
        assert_equal(type(q), np.ndarray)

        # repeat with integral input but fractional quantile
        x = np.arange(8)
        assert_equal(np.quantile(x, Fraction(1, 2)), Fraction(7, 2))

    def test_complex(self):
        # gh-22652
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.quantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.quantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.quantile, arr_c, 0.5)

    def test_no_p_overwrite(self):
        # this is worth retesting, because quantile does not make a copy
        p0 = np.array([0, 0.75, 0.25, 0.5, 1.0])
        p = p0.copy()
        np.quantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

        p0 = p0.tolist()
        p = p.tolist()
        np.quantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

    @pytest.mark.parametrize("dtype", np.typecodes["AllInteger"])
    def test_quantile_preserve_int_type(self, dtype):
        res = np.quantile(np.array([1, 2], dtype=dtype), [0.5],
                          method="nearest")
        assert res.dtype == dtype

    @pytest.mark.parametrize("method", quantile_methods)
    def test_q_zero_one(self, method):
        # gh-24710
        arr = [10, 11, 12]
        quantile = np.quantile(arr, q=[0, 1], method=method)
        assert_equal(quantile, np.array([10, 12]))

    @pytest.mark.parametrize("method", quantile_methods)
    def test_quantile_monotonic(self, method):
        # GH 14685
        # test that the return value of quantile is monotonic if p0 is ordered
        # Also tests that the boundary values are not mishandled.
        p0 = np.linspace(0, 1, 101)
        quantile = np.quantile(np.array([0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 1, 1, 9, 9, 9,
                                         8, 8, 7]) * 0.1, p0, method=method)
        assert_equal(np.sort(quantile), quantile)

        # Also test one where the number of data points is clearly divisible:
        quantile = np.quantile([0., 1., 2., 3.], p0, method=method)
        assert_equal(np.sort(quantile), quantile)

    @hypothesis.given(
            arr=arrays(dtype=np.float64,
                       shape=st.integers(min_value=3, max_value=1000),
                       elements=st.floats(allow_infinity=False, allow_nan=False,
                                          min_value=-1e300, max_value=1e300)))
    def test_quantile_monotonic_hypo(self, arr):
        p0 = np.arange(0, 1, 0.01)
        quantile = np.quantile(arr, p0)
        assert_equal(np.sort(quantile), quantile)

    def test_quantile_scalar_nan(self):
        a = np.array([[10., 7., 4.], [3., 2., 1.]])
        a[0][1] = np.nan
        actual = np.quantile(a, 0.5)
        assert np.isscalar(actual)
        assert_equal(np.quantile(a, 0.5), np.nan)

    @pytest.mark.parametrize("weights", [False, True])
    @pytest.mark.parametrize("method", quantile_methods)
    @pytest.mark.parametrize("alpha", [0.2, 0.5, 0.9])
    def test_quantile_identification_equation(self, weights, method, alpha):
        # Test that the identification equation holds for the empirical
        # CDF:
        #   E[V(x, Y)] = 0  <=>  x is quantile
        # with Y the random variable for which we have observed values and
        # V(x, y) the canonical identification function for the quantile (at
        # level alpha), see
        # https://doi.org/10.48550/arXiv.0912.0902
        if weights and method not in methods_supporting_weights:
            pytest.skip("Weights not supported by method.")
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we cover 3 cases:
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        w = rng.integers(low=0, high=10, size=n) if weights else None
        x = np.quantile(y, alpha, method=method, weights=w)

        if method in ("higher",):
            # These methods do not fulfill the identification equation.
            assert np.abs(np.mean(self.V(x, y, alpha))) > 0.1 / n
        elif int(n * alpha) == n * alpha and not weights:
            # We can expect exact results, up to machine precision.
            assert_allclose(
                np.average(self.V(x, y, alpha), weights=w), 0, atol=1e-14,
            )
        else:
            # V = (x >= y) - alpha cannot sum to zero exactly but within
            # "sample precision".
            assert_allclose(np.average(self.V(x, y, alpha), weights=w), 0,
                atol=1 / n / np.amin([alpha, 1 - alpha]))

    @pytest.mark.parametrize("weights", [False, True])
    @pytest.mark.parametrize("method", quantile_methods)
    @pytest.mark.parametrize("alpha", [0.2, 0.5, 0.9])
    def test_quantile_add_and_multiply_constant(self, weights, method, alpha):
        # Test that
        #  1. quantile(c + x) = c + quantile(x)
        #  2. quantile(c * x) = c * quantile(x)
        #  3. quantile(-x) = -quantile(x, 1 - alpha)
        #     On empirical quantiles, this equation does not hold exactly.
        # Koenker (2005) "Quantile Regression" Chapter 2.2.3 calls these
        # properties equivariance.
        if weights and method not in methods_supporting_weights:
            pytest.skip("Weights not supported by method.")
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we have cases for
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        w = rng.integers(low=0, high=10, size=n) if weights else None
        q = np.quantile(y, alpha, method=method, weights=w)
        c = 13.5

        # 1
        assert_allclose(np.quantile(c + y, alpha, method=method, weights=w),
                        c + q)
        # 2
        assert_allclose(np.quantile(c * y, alpha, method=method, weights=w),
                        c * q)
        # 3
        if weights:
            # From here on, we would need more methods to support weights.
            return
        q = -np.quantile(-y, 1 - alpha, method=method)
        if method == "inverted_cdf":
            if (
                n * alpha == int(n * alpha)
                or np.round(n * alpha) == int(n * alpha) + 1
            ):
                assert_allclose(q, np.quantile(y, alpha, method="higher"))
            else:
                assert_allclose(q, np.quantile(y, alpha, method="lower"))
        elif method == "closest_observation":
            if n * alpha == int(n * alpha):
                assert_allclose(q, np.quantile(y, alpha, method="higher"))
            elif np.round(n * alpha) == int(n * alpha) + 1:
                assert_allclose(
                    q, np.quantile(y, alpha + 1 / n, method="higher"))
            else:
                assert_allclose(q, np.quantile(y, alpha, method="lower"))
        elif method == "interpolated_inverted_cdf":
            assert_allclose(q, np.quantile(y, alpha + 1 / n, method=method))
        elif method == "nearest":
            if n * alpha == int(n * alpha):
                assert_allclose(q, np.quantile(y, alpha + 1 / n, method=method))
            else:
                assert_allclose(q, np.quantile(y, alpha, method=method))
        elif method == "lower":
            assert_allclose(q, np.quantile(y, alpha, method="higher"))
        elif method == "higher":
            assert_allclose(q, np.quantile(y, alpha, method="lower"))
        else:
            # "averaged_inverted_cdf", "hazen", "weibull", "linear",
            # "median_unbiased", "normal_unbiased", "midpoint"
            assert_allclose(q, np.quantile(y, alpha, method=method))

    @pytest.mark.parametrize("method", methods_supporting_weights)
    @pytest.mark.parametrize("alpha", [0.2, 0.5, 0.9])
    def test_quantile_constant_weights(self, method, alpha):
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we have cases for
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        q = np.quantile(y, alpha, method=method)

        w = np.ones_like(y)
        qw = np.quantile(y, alpha, method=method, weights=w)
        assert_allclose(qw, q)

        w = 8.125 * np.ones_like(y)
        qw = np.quantile(y, alpha, method=method, weights=w)
        assert_allclose(qw, q)

    @pytest.mark.parametrize("method", methods_supporting_weights)
    @pytest.mark.parametrize("alpha", [0, 0.2, 0.5, 0.9, 1])
    def test_quantile_with_integer_weights(self, method, alpha):
        # Integer weights can be interpreted as repeated observations.
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we have cases for
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        w = rng.integers(low=0, high=10, size=n, dtype=np.int32)

        qw = np.quantile(y, alpha, method=method, weights=w)
        q = np.quantile(np.repeat(y, w), alpha, method=method)
        assert_allclose(qw, q)

    @pytest.mark.parametrize("method", methods_supporting_weights)
    def test_quantile_with_weights_and_axis(self, method):
        rng = np.random.default_rng(4321)

        # 1d weight and single alpha
        y = rng.random((2, 10, 3))
        w = np.abs(rng.random(10))
        alpha = 0.5
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = np.zeros(shape=(2, 3))
        for i in range(2):
            for j in range(3):
                q_res[i, j] = np.quantile(
                    y[i, :, j], alpha, method=method, weights=w
                )
        assert_allclose(q, q_res)

        # 1d weight and 1d alpha
        alpha = [0, 0.2, 0.4, 0.6, 0.8, 1]  # shape (6,)
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = np.zeros(shape=(6, 2, 3))
        for i in range(2):
            for j in range(3):
                q_res[:, i, j] = np.quantile(
                    y[i, :, j], alpha, method=method, weights=w
                )
        assert_allclose(q, q_res)

        # 1d weight and 2d alpha
        alpha = [[0, 0.2], [0.4, 0.6], [0.8, 1]]  # shape (3, 2)
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = q_res.reshape((3, 2, 2, 3))
        assert_allclose(q, q_res)

        # shape of weights equals shape of y
        w = np.abs(rng.random((2, 10, 3)))
        alpha = 0.5
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = np.zeros(shape=(2, 3))
        for i in range(2):
            for j in range(3):
                q_res[i, j] = np.quantile(
                    y[i, :, j], alpha, method=method, weights=w[i, :, j]
                )
        assert_allclose(q, q_res)

    @pytest.mark.parametrize("method", methods_supporting_weights)
    def test_quantile_weights_min_max(self, method):
        # Test weighted quantile at 0 and 1 with leading and trailing zero
        # weights.
        w = [0, 0, 1, 2, 3, 0]
        y = np.arange(6)
        y_min = np.quantile(y, 0, weights=w, method="inverted_cdf")
        y_max = np.quantile(y, 1, weights=w, method="inverted_cdf")
        assert y_min == y[2]  # == 2
        assert y_max == y[4]  # == 4

    def test_quantile_weights_raises_negative_weights(self):
        y = [1, 2]
        w = [-0.5, 1]
        with pytest.raises(ValueError, match="Weights must be non-negative"):
            np.quantile(y, 0.5, weights=w, method="inverted_cdf")

    @pytest.mark.parametrize(
            "method",
            sorted(set(quantile_methods) - set(methods_supporting_weights)),
    )
    def test_quantile_weights_raises_unsupported_methods(self, method):
        y = [1, 2]
        w = [0.5, 1]
        msg = "Only method 'inverted_cdf' supports weights"
        with pytest.raises(ValueError, match=msg):
            np.quantile(y, 0.5, weights=w, method=method)

    def test_weibull_fraction(self):
        arr = [Fraction(0, 1), Fraction(1, 10)]
        quantile = np.quantile(arr, [0, ], method='weibull')
        assert_equal(quantile, np.array(Fraction(0, 1)))
        quantile = np.quantile(arr, [Fraction(1, 2)], method='weibull')
        assert_equal(quantile, np.array(Fraction(1, 20)))

    def test_closest_observation(self):
        # Round ties to nearest even order statistic (see #26656)
        m = 'closest_observation'
        q = 0.5
        arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert_equal(2, np.quantile(arr[0:3], q, method=m))
        assert_equal(2, np.quantile(arr[0:4], q, method=m))
        assert_equal(2, np.quantile(arr[0:5], q, method=m))
        assert_equal(3, np.quantile(arr[0:6], q, method=m))
        assert_equal(4, np.quantile(arr[0:7], q, method=m))
        assert_equal(4, np.quantile(arr[0:8], q, method=m))
        assert_equal(4, np.quantile(arr[0:9], q, method=m))
        assert_equal(5, np.quantile(arr, q, method=m))


class TestLerp:
    @hypothesis.given(t0=st.floats(allow_nan=False, allow_infinity=False,
                                   min_value=0, max_value=1),
                      t1=st.floats(allow_nan=False, allow_infinity=False,
                                   min_value=0, max_value=1),
                      a=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300),
                      b=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300))
    def test_linear_interpolation_formula_monotonic(self, t0, t1, a, b):
        l0 = nfb._lerp(a, b, t0)
        l1 = nfb._lerp(a, b, t1)
        if t0 == t1 or a == b:
            assert l0 == l1  # uninteresting
        elif (t0 < t1) == (a < b):
            assert l0 <= l1
        else:
            assert l0 >= l1

    @hypothesis.given(t=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=0, max_value=1),
                      a=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300),
                      b=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300))
    def test_linear_interpolation_formula_bounded(self, t, a, b):
        if a <= b:
            assert a <= nfb._lerp(a, b, t) <= b
        else:
            assert b <= nfb._lerp(a, b, t) <= a

    @hypothesis.given(t=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=0, max_value=1),
                      a=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300),
                      b=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300))
    def test_linear_interpolation_formula_symmetric(self, t, a, b):
        # double subtraction is needed to remove the extra precision of t < 0.5
        left = nfb._lerp(a, b, 1 - (1 - t))
        right = nfb._lerp(b, a, 1 - t)
        assert_allclose(left, right)

    def test_linear_interpolation_formula_0d_inputs(self):
        a = np.array(2)
        b = np.array(5)
        t = np.array(0.2)
        assert nfb._lerp(a, b, t) == 2.6


class TestMedian:

    def test_basic(self):
        a0 = np.array(1)
        a1 = np.arange(2)
        a2 = np.arange(6).reshape(2, 3)
        assert_equal(np.median(a0), 1)
        assert_allclose(np.median(a1), 0.5)
        assert_allclose(np.median(a2), 2.5)
        assert_allclose(np.median(a2, axis=0), [1.5, 2.5, 3.5])
        assert_equal(np.median(a2, axis=1), [1, 4])
        assert_allclose(np.median(a2, axis=None), 2.5)

        a = np.array([0.0444502, 0.0463301, 0.141249, 0.0606775])
        assert_almost_equal((a[1] + a[3]) / 2., np.median(a))
        a = np.array([0.0463301, 0.0444502, 0.141249])
        assert_equal(a[0], np.median(a))
        a = np.array([0.0444502, 0.141249, 0.0463301])
        assert_equal(a[-1], np.median(a))
        # check array scalar result
        assert_equal(np.median(a).ndim, 0)
        a[1] = np.nan
        assert_equal(np.median(a).ndim, 0)

    def test_axis_keyword(self):
        a3 = np.array([[2, 3],
                       [0, 1],
                       [6, 7],
                       [4, 5]])
        for a in [a3, np.random.randint(0, 100, size=(2, 3, 4))]:
            orig = a.copy()
            np.median(a, axis=None)
            for ax in range(a.ndim):
                np.median(a, axis=ax)
            assert_array_equal(a, orig)

        assert_allclose(np.median(a3, axis=0), [3, 4])
        assert_allclose(np.median(a3.T, axis=1), [3, 4])
        assert_allclose(np.median(a3), 3.5)
        assert_allclose(np.median(a3, axis=None), 3.5)
        assert_allclose(np.median(a3.T), 3.5)

    def test_overwrite_keyword(self):
        a3 = np.array([[2, 3],
                       [0, 1],
                       [6, 7],
                       [4, 5]])
        a0 = np.array(1)
        a1 = np.arange(2)
        a2 = np.arange(6).reshape(2, 3)
        assert_allclose(np.median(a0.copy(), overwrite_input=True), 1)
        assert_allclose(np.median(a1.copy(), overwrite_input=True), 0.5)
        assert_allclose(np.median(a2.copy(), overwrite_input=True), 2.5)
        assert_allclose(
            np.median(a2.copy(), overwrite_input=True, axis=0), [1.5, 2.5, 3.5])
        assert_allclose(
            np.median(a2.copy(), overwrite_input=True, axis=1), [1, 4])
        assert_allclose(
            np.median(a2.copy(), overwrite_input=True, axis=None), 2.5)
        assert_allclose(
            np.median(a3.copy(), overwrite_input=True, axis=0), [3, 4])
        assert_allclose(
            np.median(a3.T.copy(), overwrite_input=True, axis=1), [3, 4])

        a4 = np.arange(3 * 4 * 5, dtype=np.float32).reshape((3, 4, 5))
        np.random.shuffle(a4.ravel())
        assert_allclose(np.median(a4, axis=None),
                        np.median(a4.copy(), axis=None, overwrite_input=True))
        assert_allclose(np.median(a4, axis=0),
                        np.median(a4.copy(), axis=0, overwrite_input=True))
        assert_allclose(np.median(a4, axis=1),
                        np.median(a4.copy(), axis=1, overwrite_input=True))
        assert_allclose(np.median(a4, axis=2),
                        np.median(a4.copy(), axis=2, overwrite_input=True))

    def test_array_like(self):
        x = [1, 2, 3]
        assert_almost_equal(np.median(x), 2)
        x2 = [x]
        assert_almost_equal(np.median(x2), 2)
        assert_allclose(np.median(x2, axis=0), x)

    def test_subclass(self):
        # gh-3846
        class MySubClass(np.ndarray):

            def __new__(cls, input_array, info=None):
                obj = np.asarray(input_array).view(cls)
                obj.info = info
                return obj

            def mean(self, axis=None, dtype=None, out=None):
                return -7

        a = MySubClass([1, 2, 3])
        assert_equal(np.median(a), -7)

    @pytest.mark.parametrize('arr',
                             ([1., 2., 3.], [1., np.nan, 3.], np.nan, 0.))
    def test_subclass2(self, arr):
        """Check that we return subclasses, even if a NaN scalar."""
        class MySubclass(np.ndarray):
            pass

        m = np.median(np.array(arr).view(MySubclass))
        assert isinstance(m, MySubclass)

    def test_out(self):
        o = np.zeros((4,))
        d = np.ones((3, 4))
        assert_equal(np.median(d, 0, out=o), o)
        o = np.zeros((3,))
        assert_equal(np.median(d, 1, out=o), o)
        o = np.zeros(())
        assert_equal(np.median(d, out=o), o)

    def test_out_nan(self):
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', RuntimeWarning)
            o = np.zeros((4,))
            d = np.ones((3, 4))
            d[2, 1] = np.nan
            assert_equal(np.median(d, 0, out=o), o)
            o = np.zeros((3,))
            assert_equal(np.median(d, 1, out=o), o)
            o = np.zeros(())
            assert_equal(np.median(d, out=o), o)

    def test_nan_behavior(self):
        a = np.arange(24, dtype=float)
        a[2] = np.nan
        assert_equal(np.median(a), np.nan)
        assert_equal(np.median(a, axis=0), np.nan)

        a = np.arange(24, dtype=float).reshape(2, 3, 4)
        a[1, 2, 3] = np.nan
        a[1, 1, 2] = np.nan

        # no axis
        assert_equal(np.median(a), np.nan)
        assert_equal(np.median(a).ndim, 0)

        # axis0
        b = np.median(np.arange(24, dtype=float).reshape(2, 3, 4), 0)
        b[2, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.median(a, 0), b)

        # axis1
        b = np.median(np.arange(24, dtype=float).reshape(2, 3, 4), 1)
        b[1, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.median(a, 1), b)

        # axis02
        b = np.median(np.arange(24, dtype=float).reshape(2, 3, 4), (0, 2))
        b[1] = np.nan
        b[2] = np.nan
        assert_equal(np.median(a, (0, 2)), b)

    @pytest.mark.skipif(IS_WASM, reason="fp errors don't work correctly")
    def test_empty(self):
        # mean(empty array) emits two warnings: empty slice and divide by 0
        a = np.array([], dtype=float)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', RuntimeWarning)
            assert_equal(np.median(a), np.nan)
            assert_(w[0].category is RuntimeWarning)
            assert_equal(len(w), 2)

        # multiple dimensions
        a = np.array([], dtype=float, ndmin=3)
        # no axis
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', RuntimeWarning)
            assert_equal(np.median(a), np.nan)
            assert_(w[0].category is RuntimeWarning)

        # axis 0 and 1
        b = np.array([], dtype=float, ndmin=2)
        assert_equal(np.median(a, axis=0), b)
        assert_equal(np.median(a, axis=1), b)

        # axis 2
        b = np.array(np.nan, dtype=float, ndmin=2)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', RuntimeWarning)
            assert_equal(np.median(a, axis=2), b)
            assert_(w[0].category is RuntimeWarning)

    def test_object(self):
        o = np.arange(7.)
        assert_(type(np.median(o.astype(object))), float)
        o[2] = np.nan
        assert_(type(np.median(o.astype(object))), float)

    def test_extended_axis(self):
        o = np.random.normal(size=(71, 23))
        x = np.dstack([o] * 10)
        assert_equal(np.median(x, axis=(0, 1)), np.median(o))
        x = np.moveaxis(x, -1, 0)
        assert_equal(np.median(x, axis=(-2, -1)), np.median(o))
        x = x.swapaxes(0, 1).copy()
        assert_equal(np.median(x, axis=(0, -1)), np.median(o))

        assert_equal(np.median(x, axis=(0, 1, 2)), np.median(x, axis=None))
        assert_equal(np.median(x, axis=(0, )), np.median(x, axis=0))
        assert_equal(np.median(x, axis=(-1, )), np.median(x, axis=-1))

        d = np.arange(3 * 5 * 7 * 11).reshape((3, 5, 7, 11))
        np.random.shuffle(d.ravel())
        assert_equal(np.median(d, axis=(0, 1, 2))[0],
                     np.median(d[:, :, :, 0].flatten()))
        assert_equal(np.median(d, axis=(0, 1, 3))[1],
                     np.median(d[:, :, 1, :].flatten()))
        assert_equal(np.median(d, axis=(3, 1, -4))[2],
                     np.median(d[:, :, 2, :].flatten()))
        assert_equal(np.median(d, axis=(3, 1, 2))[2],
                     np.median(d[2, :, :, :].flatten()))
        assert_equal(np.median(d, axis=(3, 2))[2, 1],
                     np.median(d[2, 1, :, :].flatten()))
        assert_equal(np.median(d, axis=(1, -2))[2, 1],
                     np.median(d[2, :, :, 1].flatten()))
        assert_equal(np.median(d, axis=(1, 3))[2, 2],
                     np.median(d[2, :, 2, :].flatten()))

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.median, d, axis=-5)
        assert_raises(AxisError, np.median, d, axis=(0, -5))
        assert_raises(AxisError, np.median, d, axis=4)
        assert_raises(AxisError, np.median, d, axis=(0, 4))
        assert_raises(ValueError, np.median, d, axis=(1, 1))

    def test_keepdims(self):
        d = np.ones((3, 5, 7, 11))
        assert_equal(np.median(d, axis=None, keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.median(d, axis=(0, 1), keepdims=True).shape,
                     (1, 1, 7, 11))
        assert_equal(np.median(d, axis=(0, 3), keepdims=True).shape,
                     (1, 5, 7, 1))
        assert_equal(np.median(d, axis=(1,), keepdims=True).shape,
                     (3, 1, 7, 11))
        assert_equal(np.median(d, axis=(0, 1, 2, 3), keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.median(d, axis=(0, 1, 3), keepdims=True).shape,
                     (1, 1, 7, 1))

    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1, ),
            (0, 1),
            (-3, -1),
        ]
    )
    def test_keepdims_out(self, axis):
        d = np.ones((3, 5, 7, 11))
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        out = np.empty(shape_out)
        result = np.median(d, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    @pytest.mark.parametrize("dtype", ["m8[s]"])
    @pytest.mark.parametrize("pos", [0, 23, 10])
    def test_nat_behavior(self, dtype, pos):
        # TODO: Median does not support Datetime, due to `mean`.
        # NaT and NaN should behave the same, do basic tests for NaT.
        a = np.arange(0, 24, dtype=dtype)
        a[pos] = "NaT"
        res = np.median(a)
        assert res.dtype == dtype
        assert np.isnat(res)
        res = np.percentile(a, [30, 60])
        assert res.dtype == dtype
        assert np.isnat(res).all()

        a = np.arange(0, 24 * 3, dtype=dtype).reshape(-1, 3)
        a[pos, 1] = "NaT"
        res = np.median(a, axis=0)
        assert_array_equal(np.isnat(res), [False, True, False])


class TestSortComplex:

    @pytest.mark.parametrize("type_in, type_out", [
        ('l', 'D'),
        ('h', 'F'),
        ('H', 'F'),
        ('b', 'F'),
        ('B', 'F'),
        ('g', 'G'),
        ])
    def test_sort_real(self, type_in, type_out):
        # sort_complex() type casting for real input types
        a = np.array([5, 3, 6, 2, 1], dtype=type_in)
        actual = np.sort_complex(a)
        expected = np.sort(a).astype(type_out)
        assert_equal(actual, expected)
        assert_equal(actual.dtype, expected.dtype)

    def test_sort_complex(self):
        # sort_complex() handling of complex input
        a = np.array([2 + 3j, 1 - 2j, 1 - 3j, 2 + 1j], dtype='D')
        expected = np.array([1 - 3j, 1 - 2j, 2 + 1j, 2 + 3j], dtype='D')
        actual = np.sort_complex(a)
        assert_equal(actual, expected)
        assert_equal(actual.dtype, expected.dtype)