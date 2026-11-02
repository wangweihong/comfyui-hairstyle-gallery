"""ComfyUI hairstyle selector: offline browsing and original PNG tensor output."""
import asyncio
import logging
import hashlib
import json
import random
import uuid
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from aiohttp import web
from server import PromptServer

from .catalog import ROOT, USER_LIBRARY, records, hairstyle, asset, browser_payload
from .uploads import import_image, UploadError, MAX_BYTES


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
    DESCRIPTION = "本地发型图库：浏览内置参考或单张上传自定义图片，支持中英文名称、筛选、收藏和PNG输出。"

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


class RandomHairstyleGallery(HairstyleGallery):
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"origin": (["all", "builtin", "user"], {"default": "all",
                    "tooltip": "随机范围：全部 / 内置 / 自定义。Random pool: all / built-in / custom."})},
                "optional": {"language": (["zh", "en"], {"default": "zh",
                    "tooltip": "界面与文本输出语言 / UI and text output language"})}}

    FUNCTION = "load_random"
    DESCRIPTION = "每次运行工作流时，自动从可用原图中随机抽取一个发型；输出与原发型图库相同的八项结果。"

    @classmethod
    def _candidates(cls, origin="all", language="zh"):
        if origin not in ("all", "builtin", "user"):
            raise ValueError("Invalid random source" if language == "en" else "无效的随机来源")
        available = []
        for row in records():
            if origin != "all" and row["origin"] != origin:
                continue
            try:
                asset("full", Path(row["full"]).name)
            except FileNotFoundError:
                continue
            available.append(row)
        if not available:
            raise ValueError("No available hairstyle originals in this source. Install the library, upload a reference, or change the source."
                             if language == "en" else "当前来源没有可用发型原图，请安装素材库、上传参考图或切换来源。")
        return available

    @classmethod
    def VALIDATE_INPUTS(cls, origin="all", language="zh"):
        try:
            cls._candidates(origin, language)
        except (ValueError, FileNotFoundError) as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, origin="all", language="zh"):
        # Fresh on every queued prompt, without NaN in saved prompt metadata.
        return uuid.uuid4().hex

    def load_random(self, origin="all", language="zh"):
        selected = random.choice(self._candidates(origin, language))
        result = super().load_hairstyle(selected["id"], language)
        row = hairstyle(selected["id"])
        return {"ui": {"hairstyle_id": [result[3]], "name": [result[4]], "name_zh": [row["name_zh"]], "name_en": [row["name_en"]]}, "result": result}


routes = PromptServer.instance.routes


@routes.get("/hairstyle_gallery/catalog")
async def catalog_route(request):
    try:
        return web.json_response(records())
    except (ValueError, FileNotFoundError) as exc:
        return web.json_response({"error": str(exc)}, status=503)


@routes.post("/hairstyle_gallery/upload")
async def upload_route(request):
    try:
        multipart = await request.multipart()
        fields, data, filename = {}, None, None
        async for part in multipart:
            if part.filename is not None:
                if part.name != "image" or data is not None:
                    raise UploadError("single_image_only")
                chunks, size = [], 0
                while chunk := await part.read_chunk():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise UploadError("file_too_large", 413)
                    chunks.append(chunk)
                data, filename = b"".join(chunks), part.filename
            else:
                if part.name not in {"name", "other_name", "language", "hair"} or part.name in fields:
                    raise UploadError("invalid_metadata")
                chunks, size = [], 0
                while chunk := await part.read_chunk():
                    size += len(chunk)
                    if size > 2048:
                        raise UploadError("invalid_metadata")
                    chunks.append(chunk)
                fields[part.name] = b"".join(chunks).decode("utf-8")
        if data is None:
            raise UploadError("image_required")
        try:
            await asyncio.to_thread(records)
        except (ValueError, OSError) as exc:
            raise UploadError("storage_error", 500) from exc
        row = await asyncio.to_thread(import_image, data, name=fields.get("name", ""),
            other_name=fields.get("other_name", ""), language=fields.get("language", "zh"),
            hair=fields.get("hair", "unknown"), filename=filename, root=USER_LIBRARY)
        # Reuse the existing allow-listed, browser-relative catalog representation.
        payload = browser_payload()
        selected = next(item for item in payload["records"] if item["id"] == row["id"])
        return web.json_response({"record": selected, "catalog": payload}, status=201,
                                 headers={"Cache-Control": "no-store"})
    except UploadError as exc:
        return web.json_response({"error": exc.code}, status=exc.status)
    except (ValueError, UnicodeError, AssertionError):
        return web.json_response({"error": "invalid_request"}, status=400)
    except OSError:
        logging.exception("Unable to save a custom hairstyle")
        return web.json_response({"error": "storage_error"}, status=500)


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


NODE_CLASS_MAPPINGS = {"HairstyleGallery": HairstyleGallery, "RandomHairstyleGallery": RandomHairstyleGallery}
NODE_DISPLAY_NAME_MAPPINGS = {"HairstyleGallery": "Hairstyle Gallery 发型图库", "RandomHairstyleGallery": "Random Hairstyle Gallery 随机发型图库"}
WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
