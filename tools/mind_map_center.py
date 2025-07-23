#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Center Layout Mind Map Tool
Generates radial mind maps from Markdown text with PIL-based Chinese font support
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


class MindMapCenterTool(Tool):
    
    def _setup_pil_chinese_font(self, temp_dir):
        """
        使用PIL/Pillow进行中文字体处理的解决方案
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("PIL/Pillow not available, using fallback")
            return None
            
        import platform
        
        system = platform.system()
        print(f"System: {system}")
        
        # 查找中文字体文件
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
                    print(f"Found Chinese font: {font_path}")
                    break
        elif system == 'Darwin':  # macOS
            font_paths = [
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/PingFang.ttc',
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    break
        else:  # Linux
            font_paths = [
                '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
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

    def _count_nodes_at_level(self, node: dict, target_level: int, current_level: int = 1) -> int:
        """Count nodes at a specific level in the tree"""
        if current_level == target_level:
            return 1
        if not node.get('children') or current_level >= target_level:
            return 0
        return sum(self._count_nodes_at_level(child, target_level, current_level + 1) 
                  for child in node['children'])

    def _draw_text_with_pil(self, img, draw, x, y, text, depth_level, color, font_file):
        """
        使用PIL绘制中文文本，确保完美显示
        """
        try:
            from PIL import ImageFont, ImageDraw
            
            # 确保文本正确编码
            if isinstance(text, bytes):
                safe_text = text.decode('utf-8', errors='replace')
            else:
                safe_text = str(text).strip()
            
            if not safe_text:
                safe_text = f"Node{depth_level}"
            
            print(f"Drawing text with PIL: '{safe_text}' at ({x:.0f}, {y:.0f})")
            
            # 字体大小
            base_font_size = 14
            font_size = max(base_font_size - (depth_level * 2), 8)
            
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
            
            # 绘制背景框
            padding = max(8 - depth_level, 4)
            if depth_level == 1:
                # 根节点使用更粗的边框
                border_width = 3
            else:
                border_width = 2
            
            # 背景框坐标
            box_x1 = x - text_width // 2 - padding
            box_y1 = y - text_height // 2 - padding
            box_x2 = x + text_width // 2 + padding
            box_y2 = y + text_height // 2 + padding
            
            # 绘制圆角矩形背景
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                 radius=5, fill='white', outline=color, width=border_width)
            
            # 绘制文本
            text_x = x - text_width // 2
            text_y = y - text_height // 2
            draw.text((text_x, text_y), safe_text, font=font, fill=color)
            
            print(f"Successfully drew text: '{safe_text}'")
            
        except Exception as e:
            print(f"PIL text drawing error: {e}")
            # 最简单的回退方案
            try:
                draw.text((x-10, y-5), f"Node{depth_level}", fill=color)
            except:
                pass

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str) -> bool:
        """
        Generate PNG mind map with PIL-based Chinese text rendering
        """
        try:
            print("Starting center mind map generation with PIL...")
            
            # 设置PIL中文字体
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw
            
            # Calculate canvas size
            tree_depth = self._calculate_tree_depth(tree_data)
            max_children = max([len(node.get('children', [])) for node in [tree_data] + self._get_all_nodes(tree_data)] + [1])
            
            base_size = 12
            max_width = 20
            max_height = 16
            
            width = min(base_size + (tree_depth * 2), max_width)
            height = min(base_size + (max_children * 1), max_height)
            
            fig, ax = plt.subplots(1, 1, figsize=(width, height))
            
            # Set axis limits
            max_axis_limit = 10
            axis_limit = min(max_axis_limit, max(8, tree_depth * 2, max_children))
            ax.set_xlim(-axis_limit, axis_limit)
            ax.set_ylim(-axis_limit, axis_limit)
            ax.axis('off')
            
            # Color palette
            branch_colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', 
                '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43', '#EE5A24', '#0984E3'
            ]
            
            # 存储文本信息，稍后用PIL绘制
            text_elements = []
            
            def draw_curved_branch_line(start_x, start_y, end_x, end_y, color='#333333', linewidth=3):
                """Draw smooth curved branch line"""
                if abs(start_x - end_x) < 0.01 and abs(start_y - end_y) < 0.01:
                    return
                
                dx = end_x - start_x
                dy = end_y - start_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < 0.1:
                    ax.plot([start_x, end_x], [start_y, end_y], color=color, linewidth=linewidth, alpha=0.8)
                    return
                
                control_distance = min(distance * 0.4, 2.0)
                
                if abs(dx) > abs(dy):
                    cp1_x = start_x + control_distance * (1 if dx > 0 else -1)
                    cp1_y = start_y
                    cp2_x = end_x - control_distance * (1 if dx > 0 else -1)
                    cp2_y = end_y
                else:
                    cp1_x = start_x
                    cp1_y = start_y + control_distance * (1 if dy > 0 else -1)
                    cp2_x = end_x
                    cp2_y = end_y - control_distance * (1 if dy > 0 else -1)
                
                t = np.linspace(0, 1, 50)
                curve_x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
                curve_y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
                
                ax.plot(curve_x, curve_y, color=color, linewidth=linewidth, alpha=0.8)
            
            def store_text_element(x, y, text, depth_level, color='#333333'):
                """Store text element for later PIL rendering"""
                # 转换坐标系 (matplotlib坐标 -> 像素坐标)
                text_elements.append({
                    'x': x, 'y': y, 'text': text, 
                    'depth_level': depth_level, 'color': color
                })

            def layout_dynamic_center_mindmap(node, center_x=0, center_y=0, depth_level=1, parent_angle=0, angle_range=2*math.pi, inherited_color='#333333'):
                """Dynamic center layout with color consistency"""
                root_content = node.get('content', 'Root')
                children = node.get('children', [])
                
                # Color assignment
                if depth_level == 1:
                    node_color = '#333333'
                else:
                    node_color = inherited_color
                
                # Store text element for PIL rendering
                store_text_element(center_x, center_y, root_content, depth_level, node_color)
                
                if not children:
                    return [(center_x, center_y)]
                
                child_count = len(children)
                
                # Calculate radius
                base_radius = 3.0
                depth_factor = 0.3
                child_factor = 0.05
                radius = base_radius + (depth_level * depth_factor) + (child_count * child_factor)
                radius = min(radius, axis_limit * 0.3)
                
                # Calculate angles
                if child_count == 1:
                    angles = [parent_angle if parent_angle != 0 else 0]
                else:
                    if depth_level == 1:
                        start_angle = 0
                        angle_step = 2 * math.pi / child_count
                    else:
                        start_angle = parent_angle - angle_range / 2
                        angle_step = angle_range / max(child_count - 1, 1) if child_count > 1 else 0
                    
                    angles = [start_angle + i * angle_step for i in range(child_count)]
                
                child_positions = []
                
                for i, (child, angle) in enumerate(zip(children, angles)):
                    # Calculate child position
                    child_x = center_x + radius * math.cos(angle)
                    child_y = center_y + radius * math.sin(angle)
                    
                    # Ensure within bounds
                    child_x = max(-axis_limit + 1, min(axis_limit - 1, child_x))
                    child_y = max(-axis_limit + 1, min(axis_limit - 1, child_y))
                    
                    # Color assignment
                    if depth_level == 1:
                        branch_color = branch_colors[i % len(branch_colors)]
                    else:
                        branch_color = inherited_color
                    
                    # Draw connection line
                    line_thickness = max(3 - depth_level * 0.5, 1)
                    draw_curved_branch_line(center_x, center_y, child_x, child_y, 
                                          color=branch_color, linewidth=line_thickness)
                    
                    # Calculate angle range for child
                    if len(child.get('children', [])) > 0:
                        child_angle_range = min(math.pi / 3, angle_range / max(child_count, 1))
                    else:
                        child_angle_range = 0
                    
                    # Recursive layout
                    child_positions_list = layout_dynamic_center_mindmap(
                        child, child_x, child_y, depth_level + 1, angle, child_angle_range, branch_color
                    )
                    child_positions.extend(child_positions_list)
                
                return [(center_x, center_y)] + child_positions

            # Execute layout (只绘制线条，存储文本)
            print("Starting layout...")
            all_positions = layout_dynamic_center_mindmap(tree_data)
            print(f"Layout complete with {len(all_positions)} nodes")
            
            # 先保存matplotlib图像(只有线条)
            plt.tight_layout()
            temp_base_file = os.path.join(temp_dir, "base_mindmap.png")
            plt.savefig(temp_base_file, dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            # 使用PIL加载matplotlib生成的基础图像
            base_img = Image.open(temp_base_file)
            draw = ImageDraw.Draw(base_img)
            
            # 获取图像尺寸用于坐标转换
            img_width, img_height = base_img.size
            
            print(f"Base image size: {img_width}x{img_height}")
            print(f"Text elements to draw: {len(text_elements)}")
            
            # 坐标转换函数 (matplotlib坐标 -> PIL像素坐标)
            def transform_coords(x, y):
                # matplotlib坐标范围是 [-axis_limit, axis_limit]
                # 转换为PIL图像坐标 [0, img_width/height]
                pixel_x = int((x + axis_limit) / (2 * axis_limit) * img_width)
                pixel_y = int((axis_limit - y) / (2 * axis_limit) * img_height)
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
            
            print(f"Center mind map with PIL text generated: {output_file}")
            return True
            
        except Exception as e:
            print(f"Mind map generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _get_all_nodes(self, node: dict) -> List[dict]:
        """Get all nodes in the tree for analysis"""
        nodes = [node]
        for child in node.get('children', []):
            nodes.extend(self._get_all_nodes(child))
        return nodes

    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        """
        Invoke center layout mind map generation
        """
        try:
            # Get parameters
            markdown_content = tool_parameters.get('markdown_content', '').strip()
            filename = tool_parameters.get('filename', '').strip()
            
            if not markdown_content:
                yield self.create_text_message('Center mind map generation failed: No Markdown content provided.')
                return
            
            # Handle filename
            display_filename = filename if filename else f"mindmap_center_{int(time.time())}"
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
                    yield self.create_text_message(f'Center mind map generation successful! File size: {size_text}')
                else:
                    yield self.create_text_message('Center mind map generation failed: Unable to create image file.')
        
        except Exception as e:
            error_msg = str(e)
            print(f"Tool execution failed: {error_msg}")
            yield self.create_text_message(f'Center mind map generation failed: {error_msg}')


# Export tool class for Dify
def get_tool():
    return MindMapCenterTool 