# Mind Map Generator Plugin

A powerful mind map generation plugin that intelligently converts Markdown text into beautiful PNG mind maps. Supports both center radial and horizontal layouts, with perfect Chinese environment compatibility.

## Version Information

- **Current Version**: v0.0.4
- **Release Date**: 2025-12-05
- **Compatibility**: Dify Plugin Framework
- **Python Version**: 3.12+

### Version History
- **v0.0.4** (2025-12-05): Added Free Structure Layout to Smart Layout that automatically chooses between Center and Horizontal styles based on complexity. Implemented anti-overlap algorithms for both Center and Horizontal layouts to fix element overlapping bugs.
- **v0.0.3** (2025-10-14): Adjust font centering and interface display effects, and fix known bugs
- **v0.0.2** (2025-09-02): Improved text rendering - removed bold effect while maintaining 1.5x font size for better readability
- **v0.0.1** (2025-07-29): Initial release with dual layout support and perfect Chinese compatibility

## Core Features

### Triple Layout Support
<img width="1932" height="925" alt="mind-map-en-01" src="https://github.com/user-attachments/assets/7ad41fac-eb86-419e-a477-25ce50b1a12e" />

- **Center Radial Layout**: Classic radial mind maps, perfect for knowledge systems and concept relationships
- <img width="2985" height="2385" alt="mind-map-en-03" src="https://github.com/user-attachments/assets/3d3f8d39-b50a-4b27-b0b1-9269a74ef2fa" />

- **Horizontal Layout**: Left-to-right hierarchical expansion, ideal for processes and timelines
- <img width="3585" height="2085" alt="mind-map-en-02" src="https://github.com/user-attachments/assets/e5812438-80f3-4615-9072-48f90f3a7538" />

- **Smart Free Structure Layout**: Automatically analyzes content complexity and tree depth to choose the best layout (Center Radial for simple/conceptual maps, Horizontal for deep/complex hierarchies).


### Perfect Chinese Support
- Built-in 18.79MB Chinese font file ensures perfect rendering in server environments
- Multi-platform font detection and fallback mechanisms
- Display effects optimized specifically for Chinese users

### Intelligent Optimization
- **Dynamic Size Adjustment**: Intelligently adjusts canvas and font size based on content complexity
- **Anti-overlap Algorithm**: Advanced collision detection ensures clear, readable text
- **Memory Optimization**: 100MB memory limit with efficient resource management

### Technical Advantages
- **Local Generation**: Mind maps generated locally, no API Key required, no external network or services needed
- **Secure and Reliable**: No data leakage, completely offline processing, protecting user privacy
- **Pure Python Implementation**: No external dependencies like Node.js required
- **High-Quality Output**: 150 DPI PNG images with Bézier curve smooth connections
- **Multi-platform Compatibility**: Full support for Windows, macOS, and Linux

## Developer Information

- **Author**: [@sawyer-shi](https://github.com/sawyer-shi)
- **Email**: sawyer36@foxmail.com
- **License**: MIT License
- **Source Code**: https://github.com/sawyer-shi/dify-plugins-mind_map
- **Support**: Through Dify platform and GitHub Issues

---

**Ready to create beautiful mind maps?**
