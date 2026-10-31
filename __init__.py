"""ComfyUI hairstyle selector: offline browsing and original PNG tensor output."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from aiohttp import web
from server import PromptServer

from .catalog import ROOT, records, hairstyle, asset, browser_payload


class HairstyleGallery:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"hairstyle_id": ("STRING", {"default": "h-f71f980dde3", "multiline": False,
                "tooltip": "点击浏览发型图库，选择假人头模发型参考；只写回当前节点，不会自动运行。"})},
                "optional": {"language": (["zh", "en"], {"default": "zh", "tooltip": "界面与文本输出语言 / UI and text output language"})}}

    RETURN_TYPES = ("IMAGE", "INT", "INT", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image", "width", "height", "hairstyle_id", "name", "description", "hair_length", "source_id")
    FUNCTION = "load_hairstyle"
    CATEGORY = "image/Hairstyle Gallery"
    DESCRIPTION = "本地假人发型图库：长度、名称、风格筛选与收藏，输出发型PNG及名称；从893张正脸参考提取。"

    @classmethod
    def VALIDATE_INPUTS(cls, hairstyle_id, language="zh"):
        try:
            row = hairstyle(hairstyle_id)
            asset("full", Path(row["full"]).name)
        except (ValueError, FileNotFoundError) as exc:
            return ("Cannot load hairstyle. Check the ID and the complete hairstyle library." if language == "en" else str(exc))
        return True

    @classmethod
    def IS_CHANGED(cls, hairstyle_id, language="zh"):
        row = hairstyle(hairstyle_id)
        return hashlib.sha256(asset("full", Path(row["full"]).name).read_bytes()).hexdigest() + ":" + language

    def load_hairstyle(self, hairstyle_id, language="zh"):
        row = hairstyle(hairstyle_id)
        with Image.open(asset("full", Path(row["full"]).name)) as source:
            image = ImageOps.exif_transpose(source).convert("RGBA")
            image = Image.alpha_composite(Image.new("RGBA", image.size, "white"), image).convert("RGB")
            width, height = image.size
            tensor = torch.from_numpy(np.asarray(image).astype(np.float32) / 255.0).unsqueeze(0)
        lang = "en" if language == "en" else "zh"
        description = " / ".join(value for value in (row["section_" + lang], row["hair_" + lang], row["style_" + lang]) if value)
        return tensor, width, height, hairstyle_id, row["name_" + lang], description, row["hair_" + lang], row["source_id"]


routes = PromptServer.instance.routes


@routes.get("/hairstyle_gallery/catalog")
async def catalog_route(request):
    try:
        return web.json_response(records())
    except (ValueError, FileNotFoundError) as exc:
        return web.json_response({"error": str(exc)}, status=503)


@routes.get("/hairstyle_gallery/data.js")
async def data_route(request):
    try:
        payload = json.dumps(browser_payload(), ensure_ascii=False, separators=(",", ":"))
        return web.Response(text="window.HAIRSTYLE_DATA = " + payload + ";\n", content_type="application/javascript",
                            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"})
    except (ValueError, FileNotFoundError) as exc:
        return web.Response(text="console.error(" + json.dumps(str(exc)) + ");", status=503,
                            content_type="application/javascript")


@routes.get("/hairstyle_gallery/assets/{kind}/{filename}")
async def asset_route(request):
    try:
        return web.FileResponse(asset(request.match_info["kind"], request.match_info["filename"]),
                                headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})
    except (ValueError, FileNotFoundError):
        raise web.HTTPNotFound()


@routes.get("/hairstyle_gallery/ui/{filename}")
async def ui_route(request):
    name = request.match_info["filename"]
    if name not in ("style.css", "core.mjs", "app.mjs", "i18n.mjs", "icon.svg"):
        raise web.HTTPNotFound()
    return web.FileResponse(ROOT / "web" / name, headers={"Cache-Control": "no-cache"})


@routes.get("/hairstyle_gallery/gallery")
async def gallery_route(request):
    return web.FileResponse(ROOT / "web/gallery.html", headers={"Cache-Control": "no-cache"})


NODE_CLASS_MAPPINGS = {"HairstyleGallery": HairstyleGallery}
NODE_DISPLAY_NAME_MAPPINGS = {"HairstyleGallery": "Hairstyle Gallery 发型图库"}
WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
