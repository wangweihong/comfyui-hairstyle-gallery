# comfyui-hairstyle-gallery

[简体中文](README.md) · **English**

An offline mannequin hairstyle gallery for ComfyUI. It follows Portrait Gallery's warm, responsive layout with filters, search, favorites, and large previews, so hairstyle references can be used separately from character identity.

The collection contains **893 generated hairstyles**, extracted from the face-reference section of `comfyui-portrait-gallery`: 433 short, 229 medium, 154 medium-long, and 77 long. The source styling-photo section was not used. There are 2,679 image assets (full-size PNG, preview WebP, and thumbnail WebP), totaling about 1.87 GiB. Integrity checks passed; see `library/data/audit-report.json`.

There are 54 distinct name labels: 744 images retain detailed source style names; 149 use the source hair-length category because no detailed name was supplied. Names describe source labels rather than a new visual classification.

![Original portraits and extracted mannequin hairstyles](docs/extraction-examples.jpg)

## Installation and browsing

Clone this repository inside `ComfyUI/custom_nodes/`. It includes all 893 full-size PNGs, previews, thumbnails and names (about 1.87 GiB); no separate ZIP is needed. Install dependencies with ComfyUI's Python, restart ComfyUI, and refresh the browser.

```bash
git clone https://github.com/wangweihong/comfyui-hairstyle-gallery.git
python -m pip install -r comfyui-hairstyle-gallery/requirements.txt
```

 Add **image → Hairstyle Gallery → Hairstyle Gallery**, then click **Browse hairstyles**.

Filter by length and style, or search English, Chinese, and Japanese names, hairstyle IDs, and source portrait IDs. Open a large preview and click **Use hairstyle → ComfyUI** to update the current node. Selection updates the preview without running the workflow.

The default library is the node's `library/` directory. This machine stores its data at `/media/wwhvw/备份/comfyui/发型/`; the installed node and container-visible mirror share image files through hard links. The repository includes a ready-to-use `library/`. To use a different copy, set `COMFYUI_HAIRSTYLE_GALLERY_LIBRARY` to a complete library path visible inside the ComfyUI environment/container.

## Automatic random selection: a separate node

Add **image → Hairstyle Gallery → Random Hairstyle Gallery**. Connect its `image` output to your workflow or Preview Image, then run. It draws automatically on every execution while unlocked. Set `origin` to `all`, `builtin`, or `user`; `language` supports Chinese and English. Gallery filters do not affect this pool.

Its eight outputs match the original selector and all describe the same actual image. The current name, ID and preview appear after a dice click or workflow run.

The original **Hairstyle Gallery** retains its inputs, fixed-selection behavior, outputs and workflow compatibility. The random node can lock its current selection directly. Missing originals are skipped; an empty usable source raises a clear error. Random draws may repeat by chance. The node does not start or enqueue tasks itself.

Click **🎲 Random** to draw and preview a hairstyle using the node's source filter, without running the workflow. The dice skips the current image when alternatives exist. Enable **🔒 Lock random selection** to disable the dice and keep the current `hairstyle_id` and all its outputs for subsequent runs. The workflow saves the lock and selected ID. Draw once before locking. Changing filters while locked keeps the selection; missing or cleaned originals raise an error rather than drawing a replacement.

Unlock to restore automatic random draws on workflow runs, which may repeat by chance. An unlocked manual preview does not fix the next workflow draw. Missing or cleaned originals are excluded; an empty usable source raises an error. The node does not enqueue or start workflow tasks itself.

Import [`example_workflows/random_hairstyle_preview.json`](example_workflows/random_hairstyle_preview.json) and run repeatedly to inspect results. A matching API graph is included.

![Separate random node and execution result](docs/random-node-en.png)

## Upload one custom hairstyle

1. Click **Upload hairstyle** in either the standalone gallery or the gallery opened from a node.
2. Choose a finished hairstyle reference image and inspect its preview. Enter a name in the current interface language; the other-language name is optional. Hair length defaults to **Unspecified**.
3. Click **Save to gallery**. On success, the gallery switches to Custom, clears filters, and opens the new image viewer.
4. Click **Use hairstyle → ComfyUI** to update the current node. Neither uploading nor selecting queues a workflow.

Static PNG, JPEG, and WebP are supported, one image at a time, up to 20 MiB and 32 megapixels. The server validates actual image content, normalizes the full image to PNG while preserving dimensions and transparency, and creates white-background previews and thumbnails. **Import does not extract hair or remove faces.** Custom uploads do not yet support batch import, editing, deletion, or automatic extraction. Built-in assets can be deleted or replaced using Edit.

Custom assets default to **`ComfyUI/user/hairstyle_gallery/`**, separate from node code and bundled assets:

```text
user/hairstyle_gallery/
  data/custom.json   Names, original filename, length, dimensions, and upload time
  img/full/          Full-resolution PNG
  img/preview/       WebP within 800×1000
  img/thumb/         WebP within 400×500
```

Node upgrades do not overwrite this directory; back it up separately. Clients of this local ComfyUI service share the library; there is no browser- or account-level isolation. Set `COMFYUI_HAIRSTYLE_GALLERY_USER_LIBRARY` to override the storage location with a persistent, writable path visible inside the container/environment.

The gallery adds **All sources / Built-in / Custom** filters and separate counts. Custom assets work even when the built-in index is absent. Custom IDs use `u-` plus a UUID, and their `source_id` output is an empty string. User-entered names take priority; if the other language is omitted, the provided name is reused without automatic translation.

API: `POST /hairstyle_gallery/upload` with multipart fields `image`, `name`, optional `other_name`, `language` (zh/en), and `hair` (unknown/short/medium/medium-long/long). Success returns HTTP201 with `record` and the refreshed `catalog`. Failures return JSON error codes without committing incomplete assets. The existing catalog endpoint keeps its array response and adds `origin=builtin/user`; asset reads remain restricted to registered IDs.

![Upload preview and bilingual name form](docs/custom-upload-form.png)

![Selecting a custom hairstyle inside the node gallery](docs/custom-upload-selected.png)

## Chinese / English switching

- Use the **English / 中文** button next to the node's Browse button, or the language selector at the top of the gallery. The current node and its embedded gallery stay in sync.
- The optional `language` input accepts `zh` (Chinese, default) or `en` (English). It is saved with the workflow. Existing workflows and API graphs that omit it keep Chinese outputs.
- `name`, `description`, and `hair_length` follow this language setting. Image pixels, IDs, socket identifiers, and existing connections are unchanged.
- Cards, style menus, image details, help, search controls, favorites messages, and node controls are translated. All 54 English name labels translate existing source names; mixed-language search is supported.
- Switching languages keeps filters, favorites, the current selection, and the open image viewer. It does not queue a workflow. The browser remembers the last preference; a workflow's explicit language takes priority.
- `locales/en` and `locales/zh` also supply native ComfyUI node-definition translations. Custom node titles are retained.

![English gallery and hairstyle details](docs/i18n-english.png)

## Outputs

| Output | Content |
| --- | --- |
| image | Full-resolution RGB hairstyle reference; transparent areas use a white background |
| width / height | Image dimensions |
| hairstyle_id | Built-in: `h-` plus source ID; custom: `u-` plus UUID |
| name | Chinese or English hairstyle name |
| description | Localized reference type, length, and style description |
| hair_length | Short, Medium, Medium-long, Long, or Unspecified in the selected language |
| source_id | Original face-reference ID for built-ins; empty string for custom assets |

Import `example_workflows/hairstyle_gallery_preview.json` to preview and save a selected hairstyle. `example_workflows/flux-klein-hairstyle.json` reproduces extraction and requires Portrait Gallery, LayerStyle, and the original models. Matching `.api.json` graphs are included.

`example_workflows/qwen21_hairstyle_replace.json` uses Qwen Image 2.1 to replace a character's hair with the selected reference. Install its models and choose a local character image in Load Image.

## Extraction settings

The collection uses the user's existing FLUX Klein hairstyle-extraction workflow: FLUX.2 Klein 9B, `Klein-consistency` LoRA at 0.8, Qwen3 8B FP8 text encoder, Flux2 VAE, Euler, 4 steps, CFG 1, fixed seed 295046273850143, and a 1080-pixel shortest-side resize. Current full-size outputs are 1072×1344.

The batch prompt adds a white mannequin description because the original prompt retained skin color and facial traces. Lowering or disabling the consistency LoRA changed bangs and hair length in tests, so production kept 0.8. Heads may retain faint facial contours. This is generative reference editing, not transparent-background hair extraction, exact segmentation, or guaranteed pixel-accurate hairstyle reproduction.

Machine-specific generation records (`workflows/`, `jobs/`, and `experiments/`) remain in the local source backup and are not published. Reproduction examples are provided in `example_workflows/`.

## Dataset layout

```text
library/
  img/full/       Full-resolution PNGs
  img/preview/    WebP previews within 800×1000
  img/thumb/      WebP thumbnails within 400×500
  data/hairstyle-zh.json     Source names, metadata, and image index
  data/hairstyles.csv       UTF-8 BOM source-name table
  data/source-faces.json    Original face-reference metadata
  data/generation-state.json  Completed/failed/submitted jobs
  SOURCE.json     Provenance
```

Chinese and Japanese names are retained from the source. English translations live in `translations/names.en.json`; the API and gallery add `name_en`, `style_en`, `hair_en`, and `section_en` without overwriting source metadata. Entries lacking detailed names keep a length-based fallback (`name_source=source_length_fallback`); bangs, perm, or color labels are not invented. Images and derivatives share stable IDs; metadata records checksums, source IDs, and seeds.

The resumable batch script processes incomplete entries and submits one job at a time:

```bash
python3 scripts/batch_extract.py --samples
python3 scripts/batch_extract.py
```

Defaults match this local installation. Use `--library`, `--source`, `--output`, and `--api` to override paths and the ComfyUI endpoint.

## Verification

```bash
python3 -m unittest discover -s tests -v
node tests/test_core.cjs
node tests/test_i18n.cjs
node --check web/app.mjs
node --check web/hairstyle_gallery.js
node --test tests/test_random_frontend.cjs
```

Source portraits: [AI Model Face Database](https://ai-portrait-gallery.pages.dev/) by [Agi](https://x.com/agi_aibusi). This is an independent generation and organization tool, not an official release or endorsement. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the preserved source notice. Independent program code is MIT-licensed; this does not change third-party material or model terms.

Hairstyles continue to use the existing `name` output; no duplicate socket is added. Both fixed and random nodes localize `name`, `description`, and `hair_length` using `language=zh/en`. Random preview names switch immediately as well. The gallery GitHub link points to this repository.

## Delete and replace built-in assets

- Click **Edit**, select cards and choose **Delete selected assets**. Existing filters and select-all apply to the current results. Assets are independent; matching names or source IDs are never grouped. Custom uploads are excluded.
- **Delete** and **Replace** appear below **Open in new window** in the viewer. Deletion removes the asset files and frees storage. Replacement accepts static PNG/JPEG/WebP, up to 20 MiB and 32 megapixels, preserves the ID and metadata, and updates all image derivatives.
- **Manage built-in assets** is only for handling earlier changes after a plugin update. Choose independently whether to repeat deletions and use replacement images, then **Apply**. No image selection is needed. Reports include deleted, replaced, kept and failed assets. Keeping built-ins stops the matching earlier action; missing restored files produce an error and retain the record for retry.

Startup, browsing and updates never automatically delete or replace files. Records live in `ComfyUI/user/hairstyle_gallery/data/builtin_changes.json`; replacement sources live in `ComfyUI/user/hairstyle_gallery/replacements/<id>/<revision>/`. Back up both. Clients of the same service share these files. Replacement sources and older revisions are retained. Working-tree deletion does not remove Git history objects.

Deleted IDs produce clear errors in fixed workflows and are excluded from random sampling. Replacements keep IDs and update node images. Operations are restricted to registered built-in paths and reject symlinks and path traversal. Restart ComfyUI after deployment and refresh the page. New controls remain hidden until their backend is available.

API: `GET /hairstyle_gallery/manage/summary`; `POST /hairstyle_gallery/manage/plan` with `{ids, mode}` or `{choices: {deleted: "delete" / "keep", replaced: "replace" / "keep"}}`; `POST /hairstyle_gallery/manage/apply` with `{request, token}`; multipart `POST /hairstyle_gallery/manage/replacement` with `id` and `image`.
