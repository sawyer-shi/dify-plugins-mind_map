#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Free Structure Mind Map Tool
Generates optimized radial mind maps from Markdown text with PIL-based Chinese font support.
Uses weighted angular distribution to prevent overlaps and ensure clarity based on content complexity.
"""

import os
import re
import tempfile
import time
import math
import shutil
from typing import Any, Dict, Generator, List, Tuple

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class MindMapFreeTool(Tool):
    
    def _setup_pil_chinese_font(self, temp_dir):
        """
        使用PIL/Pillow进行中文字体处理的解决方案 - 优先使用嵌入字体
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return None
            
        import platform
        
        system = platform.system()
        
        # 优先使用嵌入的字体文件
        embedded_font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'chinese_font.ttc')
        embedded_font_path = os.path.abspath(embedded_font_path)
        
        if os.path.exists(embedded_font_path):
            return embedded_font_path
        
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
                    break
        
        return font_file
    
    def _parse_markdown_to_tree(self, markdown_text: str) -> dict:
        """
        Universal Markdown parser - supports unlimited dynamic hierarchical structures
        """
        lines = markdown_text.strip().split('\n')
        nodes = []
        node_stack = []
        last_header_level = 0
        
        for line in lines:
            line = line.rstrip()
            if not line or line.startswith('```'):
                continue
                
            level = 0
            content = ""
            is_header = False
            
            # Handle headers (# ## ###)
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
                last_header_level = level
                
            # Handle numbered lists
            elif re.match(r'^\s*\d+\.\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                level = leading_spaces // 2 + 2
                content = re.sub(r'^\s*\d+\.\s*', '', line)
                content = self._clean_markdown_text(content)
                
            # Handle bullet lists
            elif re.match(r'^\s*[-\*\+]\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                
                if leading_spaces == 0 and last_header_level > 0:
                    level = last_header_level + 1
                else:
                    level = leading_spaces // 2 + 2
                    
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
            
            if not is_header and not re.match(r'^\s*[-\*\+]\s+', line):
                last_header_level = 0
            
            while node_stack and node_stack[-1]['level'] >= level:
                node_stack.pop()
            
            if node_stack:
                node_stack[-1]['children'].append(node)
            else:
                nodes.append(node)
            
            node_stack.append(node)
        
        if not nodes:
            return {'content': 'Mind Map', 'level': 1, 'children': []}
            
        if len(nodes) == 1:
            return nodes[0]
        
        return {
            'content': 'Mind Map',
            'level': 1, 
            'children': nodes
        }

    def _clean_markdown_text(self, text: str) -> str:
        """Clean markdown formatting from text"""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = text.replace('《', '').replace('》', '')
        text = re.sub(r'\*\*(.*?)\*\*:\s*', r'\1: ', text)
        return text.strip()

    def _calculate_tree_depth(self, node: dict) -> int:
        """Calculate the maximum depth of the tree structure"""
        if not node.get('children'):
            return 1
        return 1 + max((self._calculate_tree_depth(child) for child in node['children']), default=0)

    def _get_all_nodes(self, node: dict) -> List[dict]:
        """Get all nodes in the tree for analysis"""
        nodes = [node]
        for child in node.get('children', []):
            nodes.extend(self._get_all_nodes(child))
        return nodes

    def _calculate_subtree_weight(self, node: dict) -> int:
        """
        Calculate weight of subtree based on number of leaves.
        This ensures complex branches get more angular space.
        """
        if not node.get('children'):
            node['weight'] = 1
            return 1
        
        weight = sum(self._calculate_subtree_weight(child) for child in node['children'])
        node['weight'] = weight
        return weight

    def _measure_text_size(self, text: str, depth_level: int, font_file: str = None) -> Tuple[int, int]:
        """
        Estimate text dimensions using PIL font
        """
        try:
            from PIL import ImageFont, ImageDraw, Image
            
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Node{depth_level}"
            
            # 字体大小
            base_font_size = 42
            font_size = max(base_font_size - (depth_level * 6), 24)
            
            font = None
            if font_file and os.path.exists(font_file):
                try:
                    font = ImageFont.truetype(font_file, font_size)
                except Exception:
                    pass
            
            if font is None:
                try:
                    font = ImageFont.load_default()
                except:
                    # Fallback estimation
                    return len(safe_text) * font_size * 0.6 + 20, font_size + 20
            
            # Create a dummy image to get a draw object
            dummy_img = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            
            bbox = draw.textbbox((0, 0), safe_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Add padding
            padding = max(18 - depth_level * 2, 10)
            return text_width + 2 * padding, text_height + 2 * padding
            
        except Exception:
            return len(str(text)) * 15 + 20, 40 # Rough fallback

    def _draw_text_with_pil(self, img, draw, x, y, text, depth_level, color, font_file):
        """
        使用PIL绘制中文文本
        """
        try:
            from PIL import ImageFont, ImageDraw
            
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Node{depth_level}"
            
            # 字体大小
            base_font_size = 42
            font_size = max(base_font_size - (depth_level * 6), 24)
            
            # 加载字体
            font = None
            if font_file and os.path.exists(font_file):
                try:
                    font = ImageFont.truetype(font_file, font_size)
                except Exception:
                    pass
            
            if font is None:
                try:
                    font = ImageFont.load_default()
                except:
                    return
            
            # 计算文本大小
            bbox = draw.textbbox((0, 0), safe_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 背景框
            padding = max(18 - depth_level * 2, 10)
            if depth_level == 1:
                border_width = 4
            else:
                border_width = 3
            
            box_width = text_width + 2 * padding
            box_height = text_height + 2 * padding
            
            box_x1 = x - box_width // 2
            box_y1 = y - box_height // 2
            box_x2 = x + box_width // 2
            box_y2 = y + box_height // 2
            
            # 绘制圆角矩形
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                 radius=5, fill='white', outline=color, width=border_width)
            
            # 文本居中
            try:
                draw.text((x, y), safe_text, font=font, fill=color, anchor='mm')
            except TypeError:
                text_x = x - text_width / 2
                text_baseline_offset = bbox[1]
                text_visual_height = bbox[3] - bbox[1]
                text_y = y - (text_baseline_offset + text_visual_height / 2)
                draw.text((text_x, text_y), safe_text, font=font, fill=color)
            
        except Exception:
            pass

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str) -> bool:
        """
        Generate PNG mind map with free structure layout
        """
        try:
            # 设置PIL中文字体
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw
            
            # 预计算权重
            self._calculate_subtree_weight(tree_data)
            
            # 颜色
            branch_colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', 
                '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43', '#EE5A24', '#0984E3'
            ]
            
            # Store layout results: {'x', 'y', 'w', 'h', 'text', 'depth', 'color', 'children': []}
            layout_nodes = []
            # To check for collisions: list of (x, y, w, h)
            placed_boxes = []

            def check_collision(x, y, w, h, margin=20):
                """Check if the box collides with any existing boxes"""
                # Simple AABB collision
                l1, r1 = x - w/2 - margin, x + w/2 + margin
                t1, b1 = y - h/2 - margin, y + h/2 + margin
                
                for bx, by, bw, bh in placed_boxes:
                    l2, r2 = bx - bw/2, bx + bw/2
                    t2, b2 = by - bh/2, by + bh/2
                    
                    if not (l1 > r2 or r1 < l2 or t1 > b2 or b1 < t2):
                        return True
                return False

            def layout_recursive(node, parent_x, parent_y, start_angle, end_angle, depth_level, inherited_color):
                """
                Recursive layout with collision detection and staggered radius
                """
                content = node.get('content', 'Node')
                children = node.get('children', [])
                
                # Measure text size
                w, h = self._measure_text_size(content, depth_level, font_file)
                
                # Calculate position for current node
                # Note: For root, parent_x/y is 0, radius is 0
                
                if depth_level == 1:
                    # Root node
                    x, y = 0, 0
                    node_color = '#333333'
                else:
                    node_color = inherited_color
                    
                    # Preliminary polar coordinates calculation
                    # Angle is midpoint of assigned sector
                    mid_angle = (start_angle + end_angle) / 2
                    
                    # Dynamic Radius Base
                    # Increasing radius for deeper levels
                    # Start with a larger base to separate from root
                    radius_base = 200 * depth_level if depth_level > 1 else 0 
                    
                    # Staggered Radius Logic:
                    # If this node is a child, we can offset its radius based on its index among siblings
                    # But here we are processing recursively.
                    # We need a "proposed" radius.
                    
                    # Let's use an iterative approach to find a non-colliding radius
                    # Start from ideal radius
                    current_r = radius_base
                    
                    # Collision resolution loop
                    # Max attempts to push outward
                    max_attempts = 20
                    step = 60 # Push out by 60 pixels per step
                    
                    final_x, final_y = 0, 0
                    placed = False
                    
                    for attempt in range(max_attempts):
                        # Calculate cartesian
                        # Adjust r based on attempt (push out)
                        # Also apply small angle jitter if needed? No, stick to radial push for now.
                        
                        # Basic staggered logic: 
                        # If we knew the sibling index, we could add offset.
                        # Since we are in recursive call, we can pass it or handle it.
                        # But simple collision push might be enough.
                        
                        test_r = current_r + attempt * step
                        test_x = parent_x + (test_r - (200 * (depth_level-1))) * math.cos(mid_angle) # Relative to parent?
                        # Actually, "Free Layout" usually means relative to Parent.
                        # But ensuring global non-overlap is easier with absolute coordinates from Center?
                        # Let's stick to Global Radial logic:
                        # x = r * cos(theta), y = r * sin(theta)
                        # This ensures consistency.
                        
                        test_x = test_r * math.cos(mid_angle)
                        test_y = test_r * math.sin(mid_angle)
                        
                        if not check_collision(test_x, test_y, w, h):
                            final_x, final_y = test_x, test_y
                            placed = True
                            break
                    
                    if not placed:
                        # If still colliding, just place it at last tested position
                        final_x, final_y = test_x, test_y
                        
                    x, y = final_x, final_y

                # Register placed box
                placed_boxes.append((x, y, w, h))
                
                # Store node info for drawing
                node_info = {
                    'x': x, 'y': y, 
                    'parent_x': parent_x, 'parent_y': parent_y,
                    'text': content, 'depth': depth_level, 
                    'color': node_color, 'width': w, 'height': h
                }
                layout_nodes.append(node_info)
                
                # Process children
                if children:
                    total_weight = sum(child.get('weight', 1) for child in children)
                    angle_range = end_angle - start_angle
                    
                    current_angle = start_angle
                    
                    # Staggered Radius Optimization for Siblings
                    # Pre-calculate sibling order to apply zig-zag radius offsets if needed
                    # But collision detection above handles overlapping.
                    # To improve "visual" spacing (prevent crowding), we can add initial offsets.
                    
                    for i, child in enumerate(children):
                        child_weight = child.get('weight', 1)
                        child_angle_step = (child_weight / total_weight) * angle_range
                        
                        child_start = current_angle
                        child_end = current_angle + child_angle_step
                        
                        # Determine color
                        if depth_level == 1:
                            child_c = branch_colors[i % len(branch_colors)]
                        else:
                            child_c = inherited_color
                            
                        layout_recursive(child, x, y, child_start, child_end, depth_level + 1, child_c)
                        
                        current_angle += child_angle_step

            # Start Layout
            # Initial call with root
            layout_recursive(tree_data, 0, 0, 0, 2*math.pi, 1, '#333333')
            
            # Calculate dynamic canvas size
            if not layout_nodes:
                return False
                
            min_x = min(n['x'] - n['width']/2 for n in layout_nodes)
            max_x = max(n['x'] + n['width']/2 for n in layout_nodes)
            min_y = min(n['y'] - n['height']/2 for n in layout_nodes)
            max_y = max(n['y'] + n['height']/2 for n in layout_nodes)
            
            # Add padding
            margin = 100
            total_width = max_x - min_x + 2 * margin
            total_height = max_y - min_y + 2 * margin
            
            # Sanity check
            total_width = max(total_width, 800)
            total_height = max(total_height, 600)
            
            # Matplotlib figsize is in inches. Assume dpi=100
            dpi = 100
            fig_width = total_width / dpi
            fig_height = total_height / dpi
            
            # Re-create figure with calculated size
            plt.close() # Close initial dummy figure
            fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=dpi)
            
            # Set limits to match our coordinate system
            ax.set_xlim(min_x - margin, max_x + margin)
            ax.set_ylim(min_y - margin, max_y + margin)
            ax.axis('off')
            
            # Helper for drawing lines
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
                
                # 贝塞尔控制点计算
                mid_x = (start_x + end_x) / 2
                mid_y = (start_y + end_y) / 2
                
                t = np.linspace(0, 1, 50)
                
                start_dist = math.sqrt(start_x**2 + start_y**2)
                if start_dist > 0.001:
                    norm_start_x, norm_start_y = start_x / start_dist, start_y / start_dist
                else:
                    norm_start_x, norm_start_y = dx / distance, dy / distance

                cp1_dist = distance * 0.4
                cp1_x = start_x + norm_start_x * cp1_dist
                cp1_y = start_y + norm_start_y * cp1_dist
                
                cp2_x = end_x - (end_x - start_x) * 0.4 
                cp2_y = end_y - (end_y - start_y) * 0.4
                
                curve_x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
                curve_y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
                
                ax.plot(curve_x, curve_y, color=color, linewidth=linewidth, alpha=0.8)

            # Draw lines first
            for node in layout_nodes:
                if node['depth'] > 1:
                    # Draw line from parent
                    line_width = max(3 - node['depth'] * 0.5, 1)
                    draw_curved_branch_line(node['parent_x'], node['parent_y'], 
                                          node['x'], node['y'], 
                                          color=node['color'], linewidth=line_width)
            
            # Save base image (lines only)
            plt.tight_layout(pad=0)
            # We need to set the extent exactly to control pixel mapping
            # But tight_layout might mess it up.
            # Better:
            ax.set_position([0, 0, 1, 1]) # Occupy full figure
            
            temp_base_file = os.path.join(temp_dir, "base_free_mindmap.png")
            plt.savefig(temp_base_file, dpi=dpi, facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            # Open with PIL to draw text
            base_img = Image.open(temp_base_file)
            draw = ImageDraw.Draw(base_img)
            img_w, img_h = base_img.size
            
            # Coordinate transform: Data (min_x..max_x) -> Pixel (0..img_w)
            # X_pixel = (X_data - min_limit) / (max_limit - min_limit) * img_w
            x_range = (max_x + margin) - (min_x - margin)
            y_range = (max_y + margin) - (min_y - margin)
            
            def data_to_pixel(x, y):
                # Note: Matplotlib Y is increasing upwards. PIL Y is increasing downwards.
                # We need to flip Y.
                px = (x - (min_x - margin)) / x_range * img_w
                py = img_h - (y - (min_y - margin)) / y_range * img_h # Flip Y
                return px, py
            
            # Draw text
            for node in layout_nodes:
                px, py = data_to_pixel(node['x'], node['y'])
                self._draw_text_with_pil(
                    base_img, draw, px, py,
                    node['text'], node['depth'], 
                    node['color'], font_file
                )
            
            base_img.save(output_file, 'PNG')
            return True
            
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        """
        Invoke free structure mind map generation
        """
        try:
            # Get parameters
            markdown_content = tool_parameters.get('markdown_content', '').strip()
            filename = tool_parameters.get('filename', '').strip()
            
            if not markdown_content:
                yield self.create_text_message('Free mind map generation failed: No Markdown content provided.')
                return
            
            # Handle filename
            display_filename = filename if filename else f"mindmap_free_{int(time.time())}"
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
                    
                    # Create blob message and get the file info
                    blob_message = self.create_blob_message(
                        blob=png_data,
                        meta={'mime_type': 'image/png', 'filename': display_filename}
                    )
                    
                    # 准备JSON数据，包含文件URL信息
                    json_data = {
                        "layout_type": "free_structure",
                        "file_size_mb": round(size_mb, 2),
                        "tree_depth": self._calculate_tree_depth(tree_data),
                        "total_nodes": len(self._get_all_nodes(tree_data)),
                        "filename": display_filename,
                        "generation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "success": True,
                        "file_info": {
                            "type": "image",
                            "mime_type": "image/png",
                            "size": file_size,
                            "filename": display_filename
                        }
                    }
                    
                    yield blob_message
                    yield self.create_text_message(f'Free mind map generation successful! File size: {size_text}')
                    yield self.create_json_message(json_data)
                else:
                    json_data = {
                        "layout_type": "free_structure",
                        "success": False,
                        "error": "Unable to create image file"
                    }
                    yield self.create_text_message('Free mind map generation failed: Unable to create image file.')
                    yield self.create_json_message(json_data)
        
        except Exception as e:
            error_msg = str(e)
            json_data = {
                "layout_type": "free_structure",
                "success": False,
                "error": error_msg
            }
            yield self.create_text_message(f'Free mind map generation failed: {error_msg}')
            yield self.create_json_message(json_data)

def get_tool():
    return MindMapFreeTool
