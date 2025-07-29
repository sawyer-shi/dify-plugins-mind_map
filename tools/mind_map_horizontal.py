#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Horizontal Layout Mind Map Tool
Generates left-to-right mind maps from Markdown text with PIL-based Chinese font support
Supports unlimited dynamic hierarchical structures
"""

import os
import re
import tempfile
import time
import math
import shutil
from typing import Any, Dict, Generator, List

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class MindMapHorizontalTool(Tool):
    
    def _setup_pil_chinese_font(self, temp_dir):
        """
        使用PIL/Pillow进行中文字体处理的解决方案 - 优先使用嵌入字体
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("PIL/Pillow not available, using fallback")
            return None
            
        import platform
        
        system = platform.system()
        print(f"System: {system}")
        
        # 优先使用嵌入的字体文件
        embedded_font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'chinese_font.ttc')
        embedded_font_path = os.path.abspath(embedded_font_path)
        
        if os.path.exists(embedded_font_path):
            print(f"Found embedded Chinese font: {embedded_font_path}")
            return embedded_font_path
        
        print("Embedded font not found, trying system fonts...")
        
        # 查找系统中文字体文件（作为备用）
        font_file = None
        
        if system == 'Windows':
            font_paths = [
                r'C:\Windows\Fonts\msyh.ttc',      # 微软雅黑
                r'C:\Windows\Fonts\simhei.ttf',    # 黑体
                r'C:\Windows\Fonts\simsun.ttc',    # 宋体
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    print(f"Found system Chinese font: {font_path}")
                    break
        elif system == 'Darwin':  # macOS
            font_paths = [
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/Hiragino Sans GB.ttc',
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    print(f"Found system Chinese font: {font_path}")
                    break
        else:  # Linux
            font_paths = [
                '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    print(f"Found system Chinese font: {font_path}")
                    break
        
        return font_file
    
    def _parse_markdown_to_tree(self, markdown_text: str) -> dict:
        """
        Universal Markdown parser - supports unlimited dynamic hierarchical structures:
        - Any number of header levels (# ## ### #### ##### ######)
        - Any number of list nesting levels with proper indentation
        - Mixed content types and structures
        - Completely dynamic and flexible
        """
        lines = markdown_text.strip().split('\n')
        nodes = []
        node_stack = []
        last_header_level = 0  # Track the last header level for proper list nesting
        
        for line in lines:
            line = line.rstrip()
            if not line or line.startswith('```'):
                continue
                
            level = 0
            content = ""
            is_header = False
            
            # Handle headers (# ## ### #### ##### ######) - unlimited levels
            if line.startswith('#'):
                header_count = 0
                for char in line:
                    if char == '#':
                        header_count += 1
                    else:
                        break
                level = header_count
                content = line[header_count:].strip()
                is_header = True
                last_header_level = level  # Remember this header level
                
            # Handle numbered lists (1. 2. 3. etc) with unlimited indentation
            elif re.match(r'^\s*\d+\.\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                level = leading_spaces // 2 + 2  # Convert indentation to level
                # Extract content after number, remove markdown formatting
                content = re.sub(r'^\s*\d+\.\s*', '', line)
                content = self._clean_markdown_text(content)
                
            # Handle bullet lists (- * +) with unlimited indentation  
            elif re.match(r'^\s*[-\*\+]\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                
                # Special handling: if no indentation and we just had a header, 
                # make list items children of that header
                if leading_spaces == 0 and last_header_level > 0:
                    level = last_header_level + 1  # One level deeper than the last header
                else:
                    level = leading_spaces // 2 + 2  # Convert indentation to level
                    
                # Extract content after bullet, handle **Bold**: pattern
                content = re.sub(r'^\s*[-\*\+]\s*', '', line)
                content = self._clean_markdown_text(content)
                
            else:
                continue
                
            if not content:
                continue
                
            # Create node
            node = {
                'content': content,
                'level': level,
                'children': []
            }
            
            # Reset last_header_level if this is not a list following a header
            if not is_header and not re.match(r'^\s*[-\*\+]\s+', line):
                last_header_level = 0
            
            # Adjust stack - remove nodes with level >= current level
            while node_stack and node_stack[-1]['level'] >= level:
                node_stack.pop()
            
            # Add to correct parent
            if node_stack:
                node_stack[-1]['children'].append(node)
            else:
                nodes.append(node)
            
            # Push current node to stack
            node_stack.append(node)
        
        # Handle results
        if not nodes:
            return {'content': 'Mind Map', 'level': 1, 'children': []}
            
        if len(nodes) == 1:
            return nodes[0]
        
        # Multiple root nodes - create wrapper
        return {
            'content': 'Mind Map',
            'level': 1, 
            'children': nodes
        }

    def _clean_markdown_text(self, text: str) -> str:
        """Clean markdown formatting from text"""
        # Remove **bold** formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # Remove *italic* formatting  
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        # Remove 《》 brackets
        text = text.replace('《', '').replace('》', '')
        # Handle **Bold**: pattern - keep the colon
        text = re.sub(r'\*\*(.*?)\*\*:\s*', r'\1: ', text)
        return text.strip()

    def _calculate_tree_depth(self, node: dict) -> int:
        """Calculate the maximum depth of the tree structure"""
        if not node.get('children'):
            return 1
        return 1 + max(self._calculate_tree_depth(child) for child in node['children'])

    def _count_total_nodes(self, node: dict) -> int:
        """Count total nodes in the tree"""
        count = 1
        for child in node.get('children', []):
            count += self._count_total_nodes(child)
        return count

    def _draw_text_with_pil(self, img, draw, x, y, text, depth_level, color, font_file):
        """
        使用PIL绘制中文文本，确保完美显示 (水平布局)
        """
        try:
            from PIL import ImageFont, ImageDraw
            
            # 简化文本处理
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Node{depth_level}"
            
            print(f"Drawing horizontal text with PIL: '{safe_text}' at ({x:.0f}, {y:.0f})")
            
            # 字体大小 (水平布局略小) - 扩大一倍
            base_font_size = 26
            font_size = max(base_font_size - (depth_level * 3), 16)
            
            # 加载字体
            font = None
            if font_file and os.path.exists(font_file):
                try:
                    font = ImageFont.truetype(font_file, font_size)
                    print(f"Loaded font from: {font_file}")
                except Exception as e:
                    print(f"Failed to load font: {e}")
            
            # 如果字体加载失败，使用默认字体
            if font is None:
                try:
                    font = ImageFont.load_default()
                    print("Using default font")
                except:
                    print("Failed to load default font")
                    return
            
            # 计算文本大小
            bbox = draw.textbbox((0, 0), safe_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 绘制背景框 (水平布局样式) - 扩大一倍
            padding = max(12 - depth_level * 2, 6)  # 稍微紧凑一些
            if depth_level == 1:
                border_width = 6
            else:
                border_width = 4
            
            # 背景框坐标
            box_x1 = x - text_width // 2 - padding
            box_y1 = y - text_height // 2 - padding
            box_x2 = x + text_width // 2 + padding
            box_y2 = y + text_height // 2 + padding
            
            # 绘制圆角矩形背景
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                 radius=4, fill='white', outline=color, width=border_width)
            
            # 绘制文本
            text_x = x - text_width // 2
            text_y = y - text_height // 2
            draw.text((text_x, text_y), safe_text, font=font, fill=color)
            
            print(f"Successfully drew horizontal text: '{safe_text}'")
            
        except Exception as e:
            print(f"PIL horizontal text drawing error: {e}")
            # 最简单的回退方案
            try:
                draw.text((x-10, y-5), f"Node{depth_level}", fill=color)
            except:
                pass

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str) -> bool:
        """
        Generate PNG mind map with PIL-based Chinese text rendering (Horizontal)
        """
        try:
            print("Starting horizontal mind map generation with PIL...")
            
            # 设置PIL中文字体
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw
            
            # 配置matplotlib中文字体
            import matplotlib.font_manager as fm
            if font_file and os.path.exists(font_file):
                try:
                    # 添加字体到matplotlib
                    fm.fontManager.addfont(font_file)
                    font_prop = fm.FontProperties(fname=font_file)
                    plt.rcParams['font.family'] = font_prop.get_name()
                    print(f"Matplotlib configured with font: {font_file}")
                except Exception as e:
                    print(f"Failed to configure matplotlib font: {e}")
                    # 使用系统默认中文字体配置
                    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans', 'Arial Unicode MS']
                    plt.rcParams['axes.unicode_minus'] = False
            else:
                # 使用系统默认中文字体配置
                plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans', 'Arial Unicode MS']
                plt.rcParams['axes.unicode_minus'] = False
                print("Using system default Chinese font configuration")
            
            # Calculate canvas size for horizontal layout
            tree_depth = self._calculate_tree_depth(tree_data)
            total_nodes = self._count_total_nodes(tree_data)
            
            base_width = 16
            base_height = 10
            max_width = 24
            max_height = 14
            
            width = min(base_width + (tree_depth * 3), max_width)
            height = min(base_height + (total_nodes * 0.3), max_height)
            
            fig, ax = plt.subplots(1, 1, figsize=(width, height))
            
            # Set axis limits for horizontal layout
            max_x_limit = 12
            max_y_limit = 8
            x_limit = min(max_x_limit, max(10, tree_depth * 3))
            y_limit = min(max_y_limit, max(6, total_nodes // 4))
            
            ax.set_xlim(-3, x_limit)
            ax.set_ylim(-y_limit, y_limit)
            ax.axis('off')
            
            # Color palette
            branch_colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', 
                '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43', '#EE5A24', '#0984E3'
            ]
            
            # 存储文本信息，稍后用PIL绘制
            text_elements = []
            
            def draw_curved_branch_line(start_x, start_y, end_x, end_y, color='#333333', linewidth=3):
                """Draw smooth curved branch line optimized for horizontal layout"""
                if abs(start_x - end_x) < 0.01 and abs(start_y - end_y) < 0.01:
                    return
                
                dx = end_x - start_x
                dy = end_y - start_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < 0.1:
                    ax.plot([start_x, end_x], [start_y, end_y], color=color, linewidth=linewidth, alpha=0.8)
                    return
                
                control_distance = min(distance * 0.3, 1.5)
                
                # For horizontal layout, prioritize smooth horizontal curves
                cp1_x = start_x + control_distance
                cp1_y = start_y + dy * 0.3
                cp2_x = end_x - control_distance * 0.5
                cp2_y = end_y - dy * 0.3
                
                t = np.linspace(0, 1, 40)
                curve_x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
                curve_y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
                
                ax.plot(curve_x, curve_y, color=color, linewidth=linewidth, alpha=0.8)
            
            def store_text_element(x, y, text, depth_level, color='#333333'):
                """Store text element for later PIL rendering"""
                text_elements.append({
                    'x': x, 'y': y, 'text': text, 
                    'depth_level': depth_level, 'color': color
                })

            def layout_dynamic_horizontal_mindmap(node, start_x=-2, start_y=0, depth_level=1, 
                                                available_height=None, inherited_color='#333333'):
                """Dynamic horizontal layout with color consistency"""
                root_content = node.get('content', 'Root')
                children = node.get('children', [])
                
                # Calculate available height for this subtree if not provided
                if available_height is None:
                    available_height = y_limit * 2
                
                # Color assignment
                if depth_level == 1:
                    node_color = '#333333'
                else:
                    node_color = inherited_color
                
                # Store text element for PIL rendering
                store_text_element(start_x, start_y, root_content, depth_level, node_color)
                
                if not children:
                    return start_y
                
                child_count = len(children)
                
                # More compact horizontal spacing
                base_x_spacing = 3.0
                x_spacing = base_x_spacing + (depth_level * 0.5)
                next_x = start_x + x_spacing
                
                # Ensure next_x doesn't exceed bounds
                if next_x > x_limit - 1:
                    next_x = x_limit - 1
                
                # More compact vertical spacing
                if child_count == 1:
                    child_positions = [start_y]
                else:
                    max_vertical_spacing = min(available_height / max(child_count, 1), 4.0)
                    vertical_spacing = min(max_vertical_spacing, 3.0)
                    
                    # Calculate starting Y position to center the children
                    total_height = (child_count - 1) * vertical_spacing
                    start_child_y = start_y + total_height / 2
                    
                    child_positions = [start_child_y - i * vertical_spacing for i in range(child_count)]
                    
                    # Ensure all positions are within bounds
                    child_positions = [max(-y_limit + 0.5, min(y_limit - 0.5, pos)) for pos in child_positions]
                
                # Track the actual Y range used by children
                min_child_y = float('inf')
                max_child_y = float('-inf')
                
                for i, (child, child_y) in enumerate(zip(children, child_positions)):
                    # Color assignment
                    if depth_level == 1:
                        branch_color = branch_colors[i % len(branch_colors)]
                    else:
                        branch_color = inherited_color
                    
                    # Draw connection line with bounds checking - 线条缩小一倍
                    line_thickness = max(2.5 - (depth_level * 0.2), 1)
                    
                    # Validate coordinates before drawing
                    if (abs(start_x - next_x) > 0.01 or abs(start_y - child_y) > 0.01) and \
                       (-3 <= start_x <= x_limit) and (-3 <= next_x <= x_limit) and \
                       (-y_limit <= start_y <= y_limit) and (-y_limit <= child_y <= y_limit):
                        draw_curved_branch_line(start_x, start_y, next_x, child_y,
                                              color=branch_color, linewidth=line_thickness)
                    
                    # Calculate available height for child subtree
                    child_height = max(vertical_spacing * 0.8, 1.0) if child_count > 1 else available_height * 0.6
                    
                    # Recursive layout
                    if next_x < x_limit - 0.5:
                        actual_child_y = layout_dynamic_horizontal_mindmap(
                            child, next_x, child_y, depth_level + 1, child_height, branch_color
                        )
                        
                        # Track Y range
                        min_child_y = min(min_child_y, actual_child_y)
                        max_child_y = max(max_child_y, actual_child_y)
                    else:
                        # No space for recursion, store the child text element for PIL rendering
                        store_text_element(next_x, child_y, child.get('content', 'Node'), depth_level + 1, branch_color)
                        min_child_y = min(min_child_y, child_y)
                        max_child_y = max(max_child_y, child_y)
                
                # Return the center Y position of all children
                if min_child_y != float('inf') and max_child_y != float('-inf'):
                    return (min_child_y + max_child_y) / 2
                else:
                    return start_y

            # Execute dynamic horizontal layout (只绘制线条，存储文本)
            print("Starting layout...")
            layout_dynamic_horizontal_mindmap(tree_data)
            print("Layout complete")
            
            # 先保存matplotlib图像(只有线条)
            plt.tight_layout()
            temp_base_file = os.path.join(temp_dir, "base_horizontal_mindmap.png")
            plt.savefig(temp_base_file, dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            # 使用PIL加载matplotlib生成的基础图像
            base_img = Image.open(temp_base_file)
            draw = ImageDraw.Draw(base_img)
            
            # 获取图像尺寸用于坐标转换
            img_width, img_height = base_img.size
            
            print(f"Base horizontal image size: {img_width}x{img_height}")
            print(f"Text elements to draw: {len(text_elements)}")
            
            # 坐标转换函数 (matplotlib坐标 -> PIL像素坐标)
            def transform_coords(x, y):
                # x: [-3, x_limit] -> [0, img_width]
                # y: [-y_limit, y_limit] -> [0, img_height] (注意Y轴翻转)
                pixel_x = int((x + 3) / (x_limit + 3) * img_width)
                pixel_y = int((y_limit - y) / (2 * y_limit) * img_height)
                return pixel_x, pixel_y
            
            # 使用PIL绘制所有文本元素
            for element in text_elements:
                pixel_x, pixel_y = transform_coords(element['x'], element['y'])
                self._draw_text_with_pil(
                    base_img, draw, pixel_x, pixel_y,
                    element['text'], element['depth_level'], 
                    element['color'], font_file
                )
            
            # 保存最终图像
            base_img.save(output_file, 'PNG')
            
            print(f"Horizontal mind map with PIL text generated: {output_file}")
            return True
            
        except Exception as e:
            print(f"Mind map generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        """
        Invoke horizontal layout mind map generation
        """
        try:
            # Get parameters
            markdown_content = tool_parameters.get('markdown_content', '').strip()
            filename = tool_parameters.get('filename', '').strip()
            
            if not markdown_content:
                yield self.create_text_message('Horizontal mind map generation failed: No Markdown content provided.')
                return
            
            # Handle filename
            display_filename = filename if filename else f"mindmap_horizontal_{int(time.time())}"
            display_filename = re.sub(r'[^\w\-_\.]', '_', display_filename)
            
            if not display_filename.endswith('.png'):
                display_filename += '.png'
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_output_path = os.path.join(temp_dir, display_filename)
                
                # Parse Markdown to tree structure
                tree_data = self._parse_markdown_to_tree(markdown_content)
                
                # Generate PNG mind map with PIL
                success = self._generate_png_mindmap(tree_data, temp_output_path, temp_dir)
                
                if success and os.path.exists(temp_output_path):
                    # Read generated PNG file
                    with open(temp_output_path, 'rb') as f:
                        png_data = f.read()
                    
                    # Calculate file size in MB
                    file_size = len(png_data)
                    size_mb = file_size / (1024 * 1024)
                    size_text = f"{size_mb:.2f}M"
                    
                    yield self.create_blob_message(
                        blob=png_data,
                        meta={'mime_type': 'image/png', 'filename': display_filename}
                    )
                    yield self.create_text_message(f'Horizontal mind map generation successful! File size: {size_text}')
                else:
                    yield self.create_text_message('Horizontal mind map generation failed: Unable to create image file.')
        
        except Exception as e:
            error_msg = str(e)
            print(f"Tool execution failed: {error_msg}")
            yield self.create_text_message(f'Horizontal mind map generation failed: {error_msg}')


# Export tool class for Dify
def get_tool():
    return MindMapHorizontalTool 