# 思维导图生成插件

一个功能强大的思维导图生成插件，能够将Markdown文本智能转换为精美的PNG思维导图，也支持通过用户选择的LLM模型，把普通文本自动总结成脑图Markdown结构后再生成脑图。支持中心结构、左右结构、自由结构三种布局，完美适配中文环境。

英文文档: [README.md](README.md)

## 版本信息

- **当前版本**: v0.0.8
- **发布日期**: 2026-06-14
- **兼容性**: Dify Plugin Framework
- **Python版本**: 3.12+

### 版本历史
- **v0.0.8** (2026-06-14):
  - 新增 `AI脑图` 工具，支持像文档审核插件一样在工具参数中选择 Dify LLM 模型
  - 支持输入普通文本，由LLM自动总结生成脑图Markdown结构
  - 支持选择输出脑图模式：中心结构、左右结构、自由结构
  - 支持可选下载AI生成的脑图Markdown文件
- **v0.0.7** (2026-3-3):
  - 为所有布局（中心结构、左右结构、自由结构）添加MD文件下载选项
  - 新增 `download_md` 参数（默认为false），启用后同时输出PNG脑图和原始Markdown文件
- **v0.0.6** (2026-1-1):
  - 为所有布局（中心结构、左右结构、自由结构）添加水印功能支持
  - 支持自定义水印文字（必填）、透明度(0-255)、多种布局选项（全屏平铺/居中/四角/单个角落）
- **v0.0.5** (2025-12-14): 修复自由结构布局中的bug。
- **v0.0.4** (2025-12-06): 新增自由结构布局为智能布局，根据内容复杂度自动选择中心或水平样式；左右结构和中心结构脑图均实现了防遮盖算法，彻底解决元素遮盖问题。
- **v0.0.3** (2025-10-14): 调整字体居中和界面显示效果，并修复已知bug
- **v0.0.2** (2025-09-02): 改进文本渲染效果 - 移除加粗效果，保持1.5倍字体大小，提升可读性
- **v0.0.1** (2025-07-29): 初始版本，支持双布局和完美中文兼容性

## 快速开始

### 方式一：已有Markdown内容，直接生成脑图

1. 在 Dify 中安装本插件。
2. 选择以下任意一个本地脑图工具：
   - `mind_map_center`: 中心结构
   - `mind_map_horizontal`: 左右结构
   - `mind_map_free`: 自由结构
3. 在 `markdown_content` 中输入脑图Markdown内容。
4. 运行工具后获得 PNG 脑图；如果开启 `download_md`，会同时获得Markdown文件。

### 方式二：只有普通文本，用AI自动生成脑图

1. 在 Dify 中安装并配置好可用的 LLM 模型。
2. 选择 `ai_mind_map` / `AI脑图` 工具。
3. 在 `LLM模型` 中选择要使用的模型。
4. 在 `文本内容` 中粘贴会议纪要、文章、需求说明、学习资料等普通文本。
5. 在 `脑图模式` 中选择：
   - `中心结构`: 适合知识体系、概念关系
   - `左右结构`: 适合流程、步骤、时间线
   - `自由结构`: 自动判断复杂度并选择更合适的布局
6. 运行后插件会先让 LLM 总结出脑图Markdown，再在本地渲染成 PNG 脑图。

## 核心特性

### 三种布局支持
<img width="2296" height="949" alt="00" src="https://github.com/user-attachments/assets/34cca4be-60bc-4c45-b344-95a8ed8a93b3" />
<img width="7451" height="7451" alt="01" src="https://github.com/user-attachments/assets/9d49c861-f1bb-4eb5-a94b-1f0509fa7f2c" />



- **中心辐射布局**: 经典的放射状思维导图，适合知识体系和概念关系展示
<img width="4876" height="4876" alt="Chinese_01" src="https://github.com/user-attachments/assets/d4908dee-65a9-458a-9537-608cc7bc1bd4" />


- **水平展开布局**: 从左到右的层次展开，适合流程和时间线展示
<img width="3207" height="3392" alt="Chinese_02" src="https://github.com/user-attachments/assets/f7419c7f-be68-48e0-b4d4-9c346e3507a7" />


- **智能自由结构布局**: 自动分析内容复杂度和层级深度，选择最佳布局（简单/概念类使用中心辐射，深度/复杂层级使用水平展开）。

### AI脑图功能 (v0.0.8新增)

`AI脑图` 适合用户“有一大段文字，但还没有整理成Markdown”的场景。你只需要输入文本并选择模型，插件会自动完成：

- **选择LLM模型**: 使用 Dify 的 `model-selector` 参数，可以选择工作区中已配置的 LLM。
- **自动总结结构**: LLM 会把普通文本整理成适合脑图的Markdown层级。
- **选择脑图模式**: 支持中心结构、左右结构、自由结构。
- **本地生成图片**: LLM 只负责生成Markdown结构，PNG脑图仍由插件本地渲染。
- **下载Markdown**: 开启 `download_md` 后，可以同时下载AI生成的脑图Markdown文件，方便二次编辑。


### 水印功能支持 (v0.0.6新增)
支持为生成的思维导图添加自定义水印，提供丰富的配置选项：
- **水印文字**: 自定义文本内容 (必填)
- **透明度**: 可调节透明度 (0-255)
- **布局选项**:
  - 全屏平铺 (默认)
  - 四角分布
  - 居中
  - 单个角落 (左上/右上/左下/右下)
- **层级**: 默认将水印置于背景层，保证内容清晰可读。
<img width="6416" height="6416" alt="mindmap_center_1768200397" src="https://github.com/user-attachments/assets/dc582830-8898-4129-8090-9557009747c0" />

### 完美中文支持
- 内置18.79MB中文字体文件，确保服务器环境完美渲染
- 支持多平台字体检测和回退机制
- 专为中文用户优化的显示效果

### 智能优化
- **动态大小调整**: 根据内容复杂度智能调整画布和字体大小
- **防重叠算法**: 先进的碰撞检测，确保文本清晰可读
- **内存优化**: 100MB内存限制，高效资源管理

### 技术优势
- **本地渲染**: Markdown转PNG在本地完成，无需外部脑图生成服务
- **AI能力可选**: 只有使用 `AI脑图` 时，`文本内容` 才会发送给你在 Dify 中选择的 LLM 模型
- **纯Python实现**: 无需Node.js等外部依赖
- **高质量输出**: 150 DPI PNG图像，支持贝塞尔曲线平滑连线
- **多平台兼容**: Windows、macOS、Linux全平台支持

## 核心功能

### 1) AI脑图（`ai_mind_map`）

把普通文本自动总结为脑图Markdown，并生成 PNG 脑图。

- **必填**: `model_config`、`text_content`
- **可选**: `layout_mode`、`filename`、`download_md`
- **适用场景**: 会议纪要转脑图、文章总结、产品需求梳理、学习笔记整理、长文本结构化
- **注意**: 使用该工具时，文本会发送给用户选择的 Dify LLM 模型进行总结

### 2) 中心结构脑图（`mind_map_center`）

把已有Markdown转换为中心放射状脑图。

- **必填**: `markdown_content`
- **可选**: `filename`、`download_md`
- **适用场景**: 知识体系、概念关系、主题发散

### 3) 左右结构脑图（`mind_map_horizontal`）

把已有Markdown转换为从左到右展开的层级脑图。

- **必填**: `markdown_content`
- **可选**: `filename`、`download_md`
- **适用场景**: 流程步骤、时间线、层级较深的内容

### 4) 自由结构脑图（`mind_map_free`）

根据Markdown结构复杂度自动选择中心结构或左右结构。

- **必填**: `markdown_content`
- **可选**: `filename`、`download_md`
- **适用场景**: 不确定应该选择哪种布局时，优先使用该工具

### 5) 水印脑图

以下工具支持水印：

- `mind_map_center_watermark`
- `mind_map_horizontal_watermark`
- `mind_map_free_watermark`

可设置 `watermark_text`、`opacity`、`watermark_layout` 等参数。

## Tool 参数

### `ai_mind_map`

| 参数 | 必填 | Form | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| `model_config` | 是 | form | Dify中选择的LLM | 用于总结文本并生成Markdown结构 |
| `text_content` | 是 | llm | `请把以下会议纪要整理成脑图...` | 普通文本输入 |
| `layout_mode` | 否 | form | `free` | 输出布局，支持 `center`、`horizontal`、`free` |
| `filename` | 否 | llm | `meeting_mind_map` | 输出PNG文件名，不需要写扩展名 |
| `download_md` | 否 | form | `true` | 是否同时输出AI生成的Markdown文件 |

### Markdown脑图工具通用参数

| 参数 | 必填 | Form | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| `markdown_content` | 是 | llm | `# 项目计划` | 已整理好的脑图Markdown |
| `filename` | 否 | llm | `project_plan` | 输出PNG文件名，不需要写扩展名 |
| `download_md` | 否 | form | `false` | 是否同时输出Markdown文件 |

## 使用示例

### AI脑图

```text
model_config: 选择一个可用的 Dify LLM 模型
text_content: 请把下面这段产品需求整理成脑图：我们的产品要支持用户登录、文件上传、权限管理和数据分析...
layout_mode: free
filename: product_requirements
download_md: true
```

输出结果：

- PNG脑图图片
- 如果 `download_md=true`，同时输出AI生成的Markdown文件
- JSON摘要信息，包含布局模式和生成的Markdown内容

### 普通Markdown脑图

```markdown
# 产品需求
## 用户登录
- 手机号登录
- 邮箱登录
## 文件上传
- 图片上传
- 文档上传
## 数据分析
- 使用统计
- 趋势分析
```

选择 `mind_map_free` 后即可生成脑图。

## 安全与隐私说明

- 普通Markdown脑图工具只在本地渲染图片，不需要调用外部模型。
- `AI脑图` 会把 `text_content` 发送给用户在 Dify 中选择的 LLM 模型，用于生成脑图Markdown。
- 插件不会主动保存用户输入内容；生成过程中的临时文件会在工具执行结束后清理。
- 如文本包含合同、隐私信息、商业机密，请确认所选 LLM 模型和 Dify 部署环境符合你的数据安全要求。

## 开发者信息

- **作者**: [@sawyer-shi](https://github.com/sawyer-shi)
- **邮箱**: sawyer36@foxmail.com 【正在寻找新的工作机会】
- **许可证**: Apache License 2.0
- **源码地址**: https://github.com/sawyer-shi/dify-plugins-mind_map
- **支持**: 通过Dify平台和GitHub Issues


## 许可证声明

本项目采用Apache License 2.0许可证。完整的许可证文本请参见[LICENSE](LICENSE)文件。

**注意**: 本项目之前使用MIT许可证，但从版本0.0.6开始已更新为Apache License 2.0。

---

**准备好创建精美的思维导图了吗？**
