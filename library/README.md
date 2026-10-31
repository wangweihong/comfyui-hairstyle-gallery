# comfyui-hairstyle-gallery

ComfyUI 本地假人发型图库。沿用 Portrait Gallery 的暖色响应式布局、分类筛选、搜索、收藏和大图选择方式，将人物身份与发型参考分开使用。

素材从 `comfyui-portrait-gallery` 的 **893 张正脸参考**生成：短发433张、中发229张、中长发154张、长发77张。造型图不参与本次提取。页面仅展示已生成且已建立索引的结果，生成期间可刷新查看新增素材。

![原始人物与假人发型提取对比](docs/extraction-examples.jpg)

893张均已完成，原图、预览图与缩略图共2,679个资源，约1.87GiB。名称表包含54类名称；其中744张沿用原始细分名称，149张以原始发长类别命名。完整性审计通过，见素材库 `data/audit-report.json`。

![在ComfyUI内浏览并选择发型](docs/gallery-selection.png)

## 安装与浏览

将节点目录放入 `ComfyUI/custom_nodes/comfyui-hairstyle-gallery/`，重启 ComfyUI 并刷新浏览器。添加 **image → Hairstyle Gallery → Hairstyle Gallery 发型图库**，点击“浏览发型图库”。

按长度或发型风格筛选，也可以搜索中文名称、原始日文名称、发型ID或来源人像ID。打开大图并点击 **使用此发型 → ComfyUI**，选择会写回当前节点并更新预览，不会自动运行。

默认读取节点目录的 `library/`。本机数据实际位于 `/media/wwhvw/备份/comfyui/发型/`，本机安装与容器可访问的图片使用硬链接共享，不复制整套图库。其他机器可将该目录作为 `library/`，或通过环境变量 `COMFYUI_HAIRSTYLE_GALLERY_LIBRARY` 指向容器内可见的完整素材库路径。

## 输出

| 输出 | 内容 |
| --- | --- |
| image | 完整 RGB PNG 假人发型图，原始生成尺寸 |
| width / height | 图像宽高 |
| hairstyle_id | 本库ID，`h-`加来源人像ID |
| name | 中文发型名称 |
| description | 假人发型、长度与原始中文风格描述 |
| hair_length | 短发、中发、中长发或长发 |
| source_id | 原始正脸素材ID |

`example_workflows/hairstyle_gallery_preview.json` 可直接导入，预览并保存选中的发型图。生成流程为 `example_workflows/flux-klein-hairstyle.json`，附同名API图；复现生成需要安装Portrait Gallery、LayerStyle及原工作流模型。

## 提取配置

基础为用户已有的 `flux-klein-提取发型.json`：FLUX.2 Klein 9B、`Klein-consistency` LoRA 0.8、Qwen3 8B FP8文本编码器、Flux2 VAE、Euler、4步、CFG1、固定种子295046273850143、最短边1080缩放。当前素材输出1072×1344。

原始提示词会留下肤色和五官痕迹，因此批量提示词增加白色假人头模描述。测试中关闭/降低一致性LoRA会改变发长和刘海，正式生成保留0.8权重。白色假人仍可能有浅五官起伏；这是生成式参考图处理，并非透明背景抠发、逐像素分割或严格发型复刻。

原工作流、实际提示词和运行配置保存在素材库 `workflows/`；每张图的API图、运行历史保存在 `jobs/`。测试版本保存在 `experiments/`，不混入正式图库。

## 素材文件

```text
发型/
  img/full/       完整 PNG
  img/preview/    800×1000 内 WebP 预览
  img/thumb/      400×500 内 WebP 缩略图
  data/hairstyle-zh.json    中文、日文名称与来源索引
  data/hairstyles.csv      UTF-8 BOM CSV 名称表
  data/source-faces.json   来源正脸元数据
  data/generation-state.json  已完成/失败/进行中状态
  workflows/      原始工作流、实际API、提示词
  jobs/           每图工作流与执行历史
  SOURCE.json     来源说明
```

中文名称与日文名称沿用来源记录。没有细分名称时仅以原始发长类别命名，`name_source=source_length_fallback`，不推测不存在的刘海、烫发或发色标签。PNG、预览、缩略图按唯一ID对应，清单记录校验值、来源和种子。

批量脚本支持中断续跑，只处理未完成素材，单次仅提交一项任务，避免堆满ComfyUI队列：

```bash
python3 scripts/batch_extract.py --samples
python3 scripts/batch_extract.py
```

脚本默认匹配本机目录；其他机器可使用 `--library`、`--source`、`--output` 和 `--api` 指定路径与服务地址。

## 检查

```bash
python3 -m unittest discover -s tests -v
node tests/test_core.cjs
node --check web/app.mjs
node --check web/hairstyle_gallery.js
```

来源人物素材为 [AI モデル顔データベース](https://ai-portrait-gallery.pages.dev/)，原作者 [あぎ](https://x.com/agi_aibusi)。本项目为独立生成与整理工具，来源和适用范围见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。独立程序代码适用MIT许可。
