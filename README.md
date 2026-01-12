# Mind Map Generator Plugin

A powerful mind map generation plugin that intelligently converts Markdown text into beautiful PNG mind maps. Supports both center radial and horizontal layouts, with perfect Chinese environment compatibility.【Mind maps generated locally, no API Key required, no external network or services needed】

## Version Information

- **Current Version**: v0.0.6
- **Release Date**: 2026-1-1
- **Compatibility**: Dify Plugin Framework
- **Python Version**: 3.12+

### Version History
- **v0.0.6** (2026-1-1): 
  - Added Watermark support for all layouts (Center, Horizontal, Free)
  - Supports custom watermark text (required), opacity (0-255), and multiple layout options (tile, center, corners, individual corners)
- **v0.0.5** (2025-12-14): Fix bugs in Free Structure Layout.
- **v0.0.4** (2025-12-06): Added Free Structure Layout to Smart Layout that automatically chooses between Center and Horizontal styles based on complexity. Implemented anti-overlap algorithms for both Center and Horizontal layouts to fix element overlapping bugs.
- **v0.0.3** (2025-10-14): Adjust font centering and interface display effects, and fix known bugs
- **v0.0.2** (2025-09-02): Improved text rendering - removed bold effect while maintaining 1.5x font size for better readability
- **v0.0.1** (2025-07-29): Initial release with dual layout support and perfect Chinese compatibility

## Core Features

### Triple Layout Support
<img width="2296" height="949" alt="00" src="https://github.com/user-attachments/assets/30159e4a-cbb6-4b91-9870-7d70b92f755e" />

<img width="7451" height="7451" alt="01" src="https://github.com/user-attachments/assets/56c7254c-fb78-493c-b707-75f356482ee1" />


- **Center Radial Layout**: Classic radial mind maps, perfect for knowledge systems and concept relationships
<img width="8542" height="8542" alt="English_01" src="https://github.com/user-attachments/assets/52095858-f150-494b-a6c6-03a39e8a106d" />


- **Horizontal Layout**: Left-to-right hierarchical expansion, ideal for processes and timelines
<img width="6892" height="4288" alt="English_02" src="https://github.com/user-attachments/assets/8f7232f4-23e9-4e59-b450-9b23d440687f" />


- **Smart Free Structure Layout**: Automatically analyzes content complexity and tree depth to choose the best layout (Center Radial for simple/conceptual maps, Horizontal for deep/complex hierarchies).


### Watermark Support (New in v0.0.6)
Add custom watermarks to your mind maps with extensive customization options:
- **Watermark Text**: Custom text content (Required)
- **Opacity**: Adjustable transparency (0-255)
- **Layout Options**:
  - Full Screen Tile (default)
  - Four Corners
  - Center
  - Individual Corners (TL, TR, BL, BR)
- **Layering**: Watermark is always placed in the background for better readability.
<img width="6416" height="6416" alt="mindmap_center_1768200397" src="https://github.com/user-attachments/assets/dc582830-8898-4129-8090-9557009747c0" />


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
- **License**: Apache License 2.0
- **Source Code**: https://github.com/sawyer-shi/dify-plugins-mind_map
- **Support**: Through Dify platform and GitHub Issues

## License Notice

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for the full license text.

**Note**: This project was previously licensed under MIT License but has been updated to Apache License 2.0 starting from version 0.0.6.

---

**Ready to create beautiful mind maps?**
