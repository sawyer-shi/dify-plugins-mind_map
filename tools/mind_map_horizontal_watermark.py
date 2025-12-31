#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Horizontal Layout Mind Map Tool with Watermark
Generates optimized left-to-right mind maps from Markdown text with Watermark
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

from .watermark_utils import add_watermark

class MindMapHorizontalWatermarkTool(Tool):
    
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
        Universal Markdown parser
        """
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
                
            elif re.match(r'^\s*\d+\.\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                level = leading_spaces // 2 + 2
                content = re.sub(r'^\s*\d+\.\s*', '', line)
                content = self._clean_markdown_text(content)
                
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

    def _get_all_nodes(self, node: dict) -> list:
        nodes = [node]
        for child in node.get('children', []):
            nodes.extend(self._get_all_nodes(child))
        return nodes
    
    def _estimate_text_width(self, text: str, depth_level: int) -> float:
        """
        Estimate text width in coordinate units.
        """
        width_score = 0
        for char in text:
            if ord(char) > 127:
                width_score += 1.0
            else:
                width_score += 0.6
        
        scale = max(1.0 - (depth_level - 1) * 0.1, 0.6)
        estimated_width = width_score * scale * 0.4 
        estimated_width += 0.8
        
        return estimated_width

    def _calculate_subtree_layout_data(self, node: dict, depth_level: int = 1) -> float:
        """
        Pass 1: Calculate vertical height AND estimate horizontal width for each node.
        """
        children = node.get('children', [])
        content = node.get('content', 'Node')
        
        node['_width'] = self._estimate_text_width(content, depth_level)
        base_node_height = 1.0
        
        if not children:
            node['_subtree_height'] = base_node_height
            return base_node_height
            
        children_total_height = 0
        for child in children:
            children_total_height += self._calculate_subtree_layout_data(child, depth_level + 1)
            
        gap = 0.6 
        if len(children) > 1:
            children_total_height += (len(children) - 1) * gap
            
        node['_subtree_height'] = max(base_node_height, children_total_height)
        return node['_subtree_height']

    def _assign_coordinates_to_tree(self, node, x, y_center, branch_colors, inherited_color, depth_level):
        """
        Pass 2: Assign coordinates using variable width for precise spacing.
        """
        children = node.get('children', [])
        
        if depth_level == 1:
            color = '#333333'
        else:
            color = inherited_color
            
        node['x'] = x
        node['y'] = y_center
        node['depth'] = depth_level
        node['color'] = color
        
        if not children:
            return
            
        parent_width = node['_width']
        connector_length = 2.0 
        
        max_child_width = 0
        for child in children:
            max_child_width = max(max_child_width, child['_width'])
            
        dist_to_children = (parent_width / 2) + connector_length + (max_child_width / 2)
        child_x = x + dist_to_children
        
        total_children_height = sum(c['_subtree_height'] for c in children)
        gap = 0.6
        if len(children) > 1:
            total_children_height += (len(children) - 1) * gap
            
        current_y = y_center + total_children_height / 2
        
        for i, child in enumerate(children):
            child_height = child['_subtree_height']
            child_y_center = current_y - child_height / 2
            
            if depth_level == 1:
                child_color = branch_colors[i % len(branch_colors)]
            else:
                child_color = color
                
            self._assign_coordinates_to_tree(child, child_x, child_y_center, 
                                           branch_colors, child_color, depth_level + 1)
            
            current_y -= (child_height + gap)

    def _get_all_nodes_with_coords(self, node):
        """Flatten tree to list, ensuring coords exist"""
        if 'x' not in node:
            return []
        nodes = [node]
        for child in node.get('children', []):
            nodes.extend(self._get_all_nodes_with_coords(child))
        return nodes

    def _draw_lines_recursive(self, ax, node):
        children = node.get('children', [])
        if not children:
            return
            
        start_x, start_y = node['x'], node['y']
        parent_width = node['_width']
        visual_start_x = start_x + (parent_width / 2)
        line_start_x = start_x + (parent_width / 2) * 0.6
        
        for child in children:
            end_x, end_y = child['x'], child['y']
            child_width = child['_width']
            visual_end_x = end_x - (child_width / 2)
            line_end_x = end_x - (child_width / 2) * 0.6
            
            color = child['color']
            linewidth = max(3 - child['depth'] * 0.3, 1)
            
            self._draw_bezier_curve(ax, line_start_x, start_y, line_end_x, end_y, 
                                  visual_start_x, visual_end_x,
                                  color, linewidth)
            
            self._draw_lines_recursive(ax, child)

    def _draw_bezier_curve(self, ax, start_x, start_y, end_x, end_y, 
                          visual_start_x, visual_end_x, color, linewidth):
        import numpy as np
        
        dist = math.sqrt((visual_end_x - visual_start_x)**2 + (end_y - start_y)**2)
        h_dist = abs(visual_end_x - visual_start_x)
        
        cp_dist = min(h_dist * 0.6, 4.0)
        
        cp1_x = visual_start_x + cp_dist
        cp1_y = start_y
        cp2_x = visual_end_x - cp_dist
        cp2_y = end_y
        
        t = np.linspace(0, 1, 50)
        x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
        y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
        
        ax.plot(x, y, color=color, linewidth=linewidth, alpha=0.7)

    def _draw_text_with_pil(self, img, draw, x, y, text, depth_level, color, font_file):
        """
        Draw text using PIL with high quality rendering
        """
        try:
            from PIL import ImageFont
            
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Node"
            
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
                    return
            
            bbox = draw.textbbox((0, 0), safe_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            padding = max(18 - depth_level * 2, 10)
            border_width = 4 if depth_level == 1 else 3
            
            box_width = text_width + 2 * padding
            box_height = text_height + 2 * padding
            
            box_x1 = x - box_width // 2
            box_y1 = y - box_height // 2
            box_x2 = x + box_width // 2
            box_y2 = y + box_height // 2
            
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                 radius=6, fill='white', outline=color, width=border_width)
            
            try:
                draw.text((x, y), safe_text, font=font, fill=color, anchor='mm')
            except TypeError:
                text_x = x - text_width / 2
                text_y = y - (bbox[1] + text_height / 2)
                draw.text((text_x, text_y), safe_text, font=font, fill=color)
                
        except Exception:
            pass

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str,
                              watermark_text: str = None, opacity: int = 40,
                              layout: str = 'corners') -> bool:
        """
        Generate PNG mind map using optimized layout engine with Watermark
        """
        try:
            # Setup fonts
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw
            
            # 1. Calc heights AND widths
            self._calculate_subtree_layout_data(tree_data)
            
            # 2. Assign Coordinates (Store in tree nodes)
            branch_colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', 
                '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43', '#EE5A24', '#0984E3'
            ]
            self._assign_coordinates_to_tree(tree_data, 0, 0, branch_colors, '#333333', 1)
            
            # 3. Collect nodes for determining canvas size
            all_nodes = self._get_all_nodes_with_coords(tree_data)
            if not all_nodes:
                return False
            
            # Calculate exact bounding box including text widths
            min_x = float('inf')
            max_x = float('-inf')
            min_y = float('inf')
            max_y = float('-inf')
            
            for n in all_nodes:
                half_w = n['_width'] / 2
                half_h = 0.5 
                
                min_x = min(min_x, n['x'] - half_w)
                max_x = max(max_x, n['x'] + half_w)
                min_y = min(min_y, n['y'] - half_h)
                max_y = max(max_y, n['y'] + half_h)
            
            # Add margins
            margin_x = 2.0
            margin_y = 1.5
            content_width = max_x - min_x + 2 * margin_x
            content_height = max_y - min_y + 2 * margin_y
            
            content_width = max(content_width, 12)
            content_height = max(content_height, 8)
            
            # Use a reasonable scale
            fig_width = content_width * 0.8
            fig_height = content_height * 0.8
            
            # Limit max size for safety
            if fig_width > 200: fig_width = 200
            if fig_height > 200: fig_height = 200
            
            plt.close('all')
            fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=100)
            ax.set_xlim(min_x - margin_x, max_x + margin_x)
            ax.set_ylim(min_y - margin_y, max_y + margin_y)
            ax.axis('off')
            
            # 4. Draw Lines
            self._draw_lines_recursive(ax, tree_data)
            
            # 5. Save Base Image
            plt.tight_layout(pad=0)
            ax.set_position([0, 0, 1, 1])
            
            temp_base_file = os.path.join(temp_dir, "base_horizontal.png")
            plt.savefig(temp_base_file, dpi=100, facecolor='white', edgecolor='none')
            plt.close()
            
            # 6. Draw Text with PIL
            base_img = Image.open(temp_base_file)
            
            # Apply Background Watermark
            if watermark_text:
                 base_img = add_watermark(base_img, watermark_text, opacity, layout, font_file)
            
            draw = ImageDraw.Draw(base_img)
            img_w, img_h = base_img.size
            
            x_range = (max_x + margin_x) - (min_x - margin_x)
            y_range = (max_y + margin_y) - (min_y - margin_y)
            
            def to_px(x, y):
                px = (x - (min_x - margin_x)) / x_range * img_w
                py = img_h - (y - (min_y - margin_y)) / y_range * img_h
                return px, py
                
            for node in all_nodes:
                px, py = to_px(node['x'], node['y'])
                self._draw_text_with_pil(base_img, draw, px, py, 
                                       node['content'], node['depth'], 
                                       node['color'], font_file)
            
            base_img.save(output_file, 'PNG')
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        """
        Invoke horizontal layout mind map generation
        """
        try:
            markdown_content = tool_parameters.get('markdown_content', '').strip()
            filename = tool_parameters.get('filename', '').strip()
            
            # Watermark params
            watermark_text = tool_parameters.get('watermark_text', '')
            opacity = tool_parameters.get('opacity', 40)
            watermark_layout = tool_parameters.get('watermark_layout', 'corners')

            if not markdown_content:
                yield self.create_text_message('Generation failed: No Markdown content.')
                return
            
            display_filename = filename if filename else f"mindmap_horizontal_{int(time.time())}"
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
                        "layout_type": "horizontal_optimized",
                        "file_size_mb": round(size_mb, 2),
                        "tree_depth": self._calculate_tree_depth(tree_data),
                        "total_nodes": len(self._get_all_nodes(tree_data)),
                        "filename": display_filename,
                        "success": True
                    }
                    
                    yield blob_message
                    yield self.create_text_message(f'Horizontal mind map generated successfully! Size: {size_text}')
                    yield self.create_json_message(json_data)
                else:
                    yield self.create_text_message('Generation failed: Unable to create image file.')
        
        except Exception as e:
            yield self.create_text_message(f'Generation failed: {str(e)}')

def get_tool():
    return MindMapHorizontalWatermarkTool

