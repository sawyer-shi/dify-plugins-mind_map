# 思维导图生成插件

一个功能强大的思维导图生成插件，能够将Markdown文本智能转换为精美的PNG思维导图。支持中心辐射和水平展开两种经典布局，完美适配中文环境。

## 版本信息

- **当前版本**: v0.0.4
- **发布日期**: 2025-12-06
- **兼容性**: Dify Plugin Framework
- **Python版本**: 3.12+

### 版本历史
- **v0.0.4** (2025-12-06): 新增自由结构布局为智能布局，根据内容复杂度自动选择中心或水平样式；左右结构和中心结构脑图均实现了防遮盖算法，彻底解决元素遮盖问题。
- **v0.0.3** (2025-10-14): 调整字体居中和界面显示效果，并修复已知bug
- **v0.0.2** (2025-09-02): 改进文本渲染效果 - 移除加粗效果，保持1.5倍字体大小，提升可读性
- **v0.0.1** (2025-07-29): 初始版本，支持双布局和完美中文兼容性

## 核心特性

### 三种布局支持
<img width="2296" height="949" alt="00" src="https://github.com/user-attachments/assets/34cca4be-60bc-4c45-b344-95a8ed8a93b3" />
<img width="7451" height="7451" alt="01" src="https://github.com/user-attachments/assets/9d49c861-f1bb-4eb5-a94b-1f0509fa7f2c" />



- **中心辐射布局**: 经典的放射状思维导图，适合知识体系和概念关系展示
<img width="4876" height="4876" alt="Chinese_01" src="https://github.com/user-attachments/assets/d4908dee-65a9-458a-9537-608cc7bc1bd4" />


- **水平展开布局**: 从左到右的层次展开，适合流程和时间线展示
<img width="3207" height="3392" alt="Chinese_02" src="https://github.com/user-attachments/assets/f7419c7f-be68-48e0-b4d4-9c346e3507a7" />


- **智能自由结构布局**: 自动分析内容复杂度和层级深度，选择最佳布局（简单/概念类使用中心辐射，深度/复杂层级使用水平展开）。


### 完美中文支持
- 内置18.79MB中文字体文件，确保服务器环境完美渲染
- 支持多平台字体检测和回退机制
- 专为中文用户优化的显示效果

### 智能优化
- **动态大小调整**: 根据内容复杂度智能调整画布和字体大小
- **防重叠算法**: 先进的碰撞检测，确保文本清晰可读
- **内存优化**: 100MB内存限制，高效资源管理

### 技术优势
- **本地生成**: 脑图在本地生成，无需API Key，无需链接外部网络或服务
- **安全可靠**: 数据不外泄，完全离线处理，保护用户隐私
- **纯Python实现**: 无需Node.js等外部依赖
- **高质量输出**: 150 DPI PNG图像，支持贝塞尔曲线平滑连线
- **多平台兼容**: Windows、macOS、Linux全平台支持

## 开发者信息

- **作者**: [@sawyer-shi](https://github.com/sawyer-shi)
- **邮箱**: sawyer36@foxmail.com
- **许可证**: MIT License
- **源码地址**: https://github.com/sawyer-shi/dify-plugins-mind_map
- **支持**: 通过Dify平台和GitHub Issues

---

**准备好创建精美的思维导图了吗？**
