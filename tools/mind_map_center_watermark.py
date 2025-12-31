#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Center Layout Mind Map Tool with Watermark
Generates radial mind maps from Markdown text with PIL-based Chinese font support and Watermark
Supports unlimited dynamic hierarchical structures
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

from .watermark_utils import add_watermark

class MindMapCenterWatermarkTool(Tool):
    
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
        # Replace escaped newlines with real newlines to handle escaped Markdown content
        markdown_text = markdown_text.replace('\\n', '\n')
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
            
            # Handle headers
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
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = text.replace('《', '').replace('》', '')
        text = re.sub(r'\*\*(.*?)\*\*:\s*', r'\1: ', text)
        return text.strip()

    def _calculate_tree_depth(self, node: dict) -> int:
        if not node.get('children'):
            return 1
        return 1 + max(self._calculate_tree_depth(child) for child in node['children'])

    def _get_all_nodes(self, node: dict) -> List[dict]:
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

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str,
                              watermark_text: str = None, opacity: int = 40,
                              layout: str = 'corners') -> bool:
        """
        Generate PNG mind map with free structure layout (Collision-free Radial)
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
            # Track minimum radius for each depth level to enforce strict hierarchy
            min_radius_by_depth = {}  # {depth_level: min_radius}
            # Track parent radius to ensure children are always further out
            parent_radius_map = {}  # {node_id: parent_radius}

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

            def get_min_radius_for_depth(depth_level, parent_radius=0, parent_size=None, current_size=None):
                """
                Calculate minimum radius for a depth level to ensure strict hierarchy.
                Uses node sizes to calculate compact but safe distances.
                """
                # Reduced base minimum radius for more compact layout
                # Original: 150 + (depth_level - 1) * 200
                # Optimized: 100 + (depth_level - 1) * 120
                base_min_radius = 100 + (depth_level - 1) * 120
                
                # Ensure child radius is always greater than parent radius
                if parent_radius > 0:
                    # Calculate safe distance based on actual node sizes
                    if parent_size and current_size:
                        # parent_size and current_size are (width, height) tuples
                        parent_diagonal = math.sqrt(parent_size[0]**2 + parent_size[1]**2) / 2
                        current_diagonal = math.sqrt(current_size[0]**2 + current_size[1]**2) / 2
                        # Safe distance: half of parent diagonal + half of current diagonal + small gap
                        safe_distance = parent_diagonal + current_diagonal + 30  # Reduced from fixed 120
                    else:
                        # Fallback: use smaller fixed distance
                        safe_distance = 60  # Reduced from 120
                    
                    required_radius = parent_radius + safe_distance
                    base_min_radius = max(base_min_radius, required_radius)
                
                # Update global minimum for this depth level
                if depth_level not in min_radius_by_depth:
                    min_radius_by_depth[depth_level] = base_min_radius
                else:
                    min_radius_by_depth[depth_level] = max(min_radius_by_depth[depth_level], base_min_radius)
                
                return min_radius_by_depth[depth_level]

            def layout_recursive(node, parent_x, parent_y, start_angle, end_angle, depth_level, inherited_color, parent_radius=0, parent_size=None, node_id=None):
                """
                Recursive layout with strict hierarchy enforcement and enhanced collision detection.
                Ensures all elements extend outward only, never inward.
                Optimized for compact layout while maintaining no-overlap guarantee.
                """
                content = node.get('content', 'Node')
                children = node.get('children', [])
                
                # Generate unique node ID for tracking
                if node_id is None:
                    node_id = f"node_{depth_level}_{id(node)}"
                
                # Measure text size
                w, h = self._measure_text_size(content, depth_level, font_file)
                current_size = (w, h)
                
                if depth_level == 1:
                    # Root node
                    x, y = 0, 0
                    node_color = '#333333'
                    current_radius = 0
                else:
                    node_color = inherited_color
                    
                    # Calculate minimum radius for this depth level (strict hierarchy)
                    # Pass node sizes for more accurate distance calculation
                    min_radius = get_min_radius_for_depth(depth_level, parent_radius, parent_size, current_size)
                    
                    # Preliminary polar coordinates calculation
                    mid_angle = (start_angle + end_angle) / 2
                    
                    # Start from minimum radius (never go inward)
                    radius_base = min_radius
                    
                    # Optimized collision resolution with smaller, more precise steps
                    # Use smaller base step for finer positioning
                    base_step = 20 + (depth_level - 1) * 5  # Reduced from 60 + (depth-1)*10
                    max_attempts = 150  # More attempts with smaller steps
                    
                    final_x, final_y = 0, 0
                    placed = False
                    current_radius = 0
                    
                    # Try placing along the radial line, pushing outwards if collision
                    # CRITICAL: Never allow inward movement - always start from min_radius
                    for attempt in range(max_attempts):
                        # Use smaller, more precise steps for compact layout
                        # Only slightly increase step size for later attempts
                        step = base_step * (1 + attempt * 0.05)  # Reduced from 0.1 to 0.05
                        test_r = radius_base + attempt * step
                        
                        # Ensure we never go inward (strict hierarchy enforcement)
                        if test_r < min_radius:
                            test_r = min_radius
                        
                        test_x = test_r * math.cos(mid_angle)
                        test_y = test_r * math.sin(mid_angle)
                        
                        if not check_collision(test_x, test_y, w, h):
                            final_x, final_y = test_x, test_y
                            current_radius = test_r
                            placed = True
                            break
                    
                    if not placed:
                        # Fallback: place at maximum attempted radius
                        final_x = test_r * math.cos(mid_angle)
                        final_y = test_r * math.sin(mid_angle)
                        current_radius = test_r
                    
                    x, y = final_x, final_y
                    
                    # Update minimum radius for this depth level based on actual placement
                    # But don't update too aggressively to avoid pushing everything out
                    if current_radius > min_radius_by_depth.get(depth_level, 0):
                        # Only update if significantly larger (avoid minor updates that push everything out)
                        if current_radius > min_radius_by_depth.get(depth_level, 0) * 1.2:
                            min_radius_by_depth[depth_level] = current_radius
                
                # Store parent radius for children
                parent_radius_map[node_id] = current_radius

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
                        
                        # Pass parent radius and size to ensure child is always further out
                        child_node_id = f"{node_id}_child_{i}"
                        layout_recursive(child, x, y, child_start, child_end, depth_level + 1, child_c, 
                                       parent_radius=current_radius, parent_size=current_size, node_id=child_node_id)
                        
                        current_angle += child_angle_step

            # Start Layout
            layout_recursive(tree_data, 0, 0, 0, 2*math.pi, 1, '#333333', parent_radius=0, parent_size=None, node_id='root')
            
            # Calculate dynamic canvas size with enhanced margin
            if not layout_nodes:
                return False
            
            # Calculate bounding box with node dimensions
            min_x = min(n['x'] - n['width']/2 for n in layout_nodes)
            max_x = max(n['x'] + n['width']/2 for n in layout_nodes)
            min_y = min(n['y'] - n['height']/2 for n in layout_nodes)
            max_y = max(n['y'] + n['height']/2 for n in layout_nodes)
            
            # Calculate maximum radius to ensure adequate space
            max_radius = 0
            for n in layout_nodes:
                node_radius = math.sqrt(n['x']**2 + n['y']**2)
                # Add half of node diagonal to account for node size
                node_diagonal = math.sqrt(n['width']**2 + n['height']**2) / 2
                total_radius = node_radius + node_diagonal
                max_radius = max(max_radius, total_radius)
            
            # Enhanced margin calculation based on maximum radius and depth
            # Deeper structures need more margin
            max_depth = max(n['depth'] for n in layout_nodes) if layout_nodes else 1
            base_margin = 150
            depth_margin = max_depth * 30  # Additional margin per depth level
            margin = base_margin + depth_margin
            
            # Calculate canvas size with enhanced margin
            total_width = max_x - min_x + 2 * margin
            total_height = max_y - min_y + 2 * margin
            
            # Ensure minimum size based on maximum radius
            min_size_from_radius = (max_radius + margin) * 2
            total_width = max(total_width, min_size_from_radius, 1000)
            total_height = max(total_height, min_size_from_radius, 800)
            
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
            ax.set_position([0, 0, 1, 1]) # Occupy full figure
            
            temp_base_file = os.path.join(temp_dir, "base_center_mindmap.png")
            plt.savefig(temp_base_file, dpi=dpi, facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            # Open with PIL to draw text
            base_img = Image.open(temp_base_file)
            
            # Apply Background Watermark
            if watermark_text:
                 base_img = add_watermark(base_img, watermark_text, opacity, layout, font_file)
            
            draw = ImageDraw.Draw(base_img)
            img_w, img_h = base_img.size
            
            # Coordinate transform: Data (min_x..max_x) -> Pixel (0..img_w)
            x_range = (max_x + margin) - (min_x - margin)
            y_range = (max_y + margin) - (min_y - margin)
            
            def data_to_pixel(x, y):
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
        Invoke center layout mind map generation
        """
        try:
            markdown_content = tool_parameters.get('markdown_content', '').strip()
            filename = tool_parameters.get('filename', '').strip()
            
            # Watermark parameters
            watermark_text = tool_parameters.get('watermark_text', '')
            opacity = tool_parameters.get('opacity', 40)
            watermark_layout = tool_parameters.get('watermark_layout', 'tile')

            if not markdown_content:
                yield self.create_text_message('Center mind map generation failed: No Markdown content provided.')
                return
            
            display_filename = filename if filename else f"mindmap_center_{int(time.time())}"
            display_filename = re.sub(r'[^\w\-_\.]', '_', display_filename)
            
            if not display_filename.endswith('.png'):
                display_filename += '.png'
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_output_path = os.path.join(temp_dir, display_filename)
                
                tree_data = self._parse_markdown_to_tree(markdown_content)
                success = self._generate_png_mindmap(tree_data, temp_output_path, temp_dir,
                                                     watermark_text, opacity, watermark_layout)
                
                if success and os.path.exists(temp_output_path):
                    with open(temp_output_path, 'rb') as f:
                        png_data = f.read()
                    
                    file_size = len(png_data)
                    size_mb = file_size / (1024 * 1024)
                    size_text = f"{size_mb:.2f}M"
                    
                    blob_message = self.create_blob_message(
                        blob=png_data,
                        meta={'mime_type': 'image/png', 'filename': display_filename}
                    )
                    
                    json_data = {
                        "layout_type": "center",
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
                    yield self.create_text_message(f'Center mind map generation successful! File size: {size_text}')
                    yield self.create_json_message(json_data)
                else:
                    json_data = {
                        "layout_type": "center",
                        "success": False,
                        "error": "Unable to create image file"
                    }
                    yield self.create_text_message('Center mind map generation failed: Unable to create image file.')
                    yield self.create_json_message(json_data)
        
        except Exception as e:
            error_msg = str(e)
            json_data = {
                "layout_type": "center",
                "success": False,
                "error": error_msg
            }
            yield self.create_text_message(f'Center mind map generation failed: {error_msg}')
            yield self.create_json_message(json_data)


# Export tool class for Dify
def get_tool():
    return MindMapCenterWatermarkTool

