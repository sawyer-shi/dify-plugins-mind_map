#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Free Structure Mind Map Tool (Smart Layout) with Watermark
Generates optimized mind maps from Markdown text with Watermark.
Automatically selects between Center (Radial) and Horizontal (Left-Right) layouts 
based on content complexity and structure depth.
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

from tools.themes import draw_canvas_grid, get_theme
from tools.mind_map_style import (RENDER_GATE, SEND_GATE, budget_dpi, contrast_text_color, estimate_width_units,
                                    inner_corner_radius, line_linewidth_for, load_font, new_figure, node_border_width,
                                    node_corner_radius, node_height_units, render_scale, run_heavy, wrap_text)
from .watermark_utils import add_watermark

class MindMapFreeWatermarkTool(Tool):
    
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
        embedded_font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NotoSansSC-Regular.otf')
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
    
    def _analyze_structure_complexity(self, tree_data: dict) -> str:
        """
        Analyze tree complexity to decide layout.
        Returns: 'center' or 'horizontal'
        """
        depth = self._calculate_tree_depth(tree_data)
        nodes = self._get_all_nodes(tree_data)
        total_nodes = len(nodes)
        
        # Use center layout for moderate complexity (depth <= 4 and nodes <= 100)
        if depth <= 4 and total_nodes <= 100:
            return 'center'
        
        # Use horizontal layout for deep or large structures
        return 'horizontal'

    def _draw_text_with_pil(self, img, draw, x, y, text, depth_level, color, font_file, node_fill='white'):
        """
        Draw double-layer node: colored outer ring, theme inner fill, contrast text
        """
        try:
            px = render_scale()
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Node{depth_level}"

            font_size = max(int(round((42 - depth_level * 6) * px)), int(round(24 * px)))
            font = load_font(font_file, font_size)
            if font is None:
                return

            spacing = max(int(font_size * 0.28), max(3, int(round(6 * px))))
            display = "\n".join(wrap_text(safe_text))
            bbox = draw.multiline_textbbox((0, 0), display, font=font, spacing=spacing, align="center")
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            pad_x = max(int(round((18 - depth_level * 2) * px)), int(round(10 * px)))
            pad_y = max(int(round((14 - depth_level) * px)), int(round(9 * px)))
            border = max(1, int(round(node_border_width(depth_level) * px)))

            inner_w = text_width + 2 * pad_x
            inner_h = text_height + 2 * pad_y
            outer_w = inner_w + 2 * border
            outer_h = inner_h + 2 * border

            outer_r = max(1, int(round(node_corner_radius(depth_level) * px)))
            inner_r = max(1, int(round(inner_corner_radius(depth_level) * px)))

            draw.rounded_rectangle(
                [x - outer_w / 2.0, y - outer_h / 2.0, x + outer_w / 2.0, y + outer_h / 2.0],
                radius=min(outer_r, int(outer_w / 2), int(outer_h / 2)),
                fill=color,
            )
            draw.rounded_rectangle(
                [x - inner_w / 2.0, y - inner_h / 2.0, x + inner_w / 2.0, y + inner_h / 2.0],
                radius=min(inner_r, int(inner_w / 2), int(inner_h / 2)),
                fill=node_fill,
            )

            fill_color = contrast_text_color(color, node_fill)
            try:
                draw.multiline_text((x, y), display, font=font, fill=fill_color,
                                    anchor="mm", align="center", spacing=spacing)
            except TypeError:
                draw.multiline_text((x - text_width / 2, y - text_height / 2), display,
                                    font=font, fill=fill_color, align="center", spacing=spacing)

        except Exception:
            pass
    def _calculate_subtree_weight(self, node: dict) -> int:
        """Calculate weight of subtree for radial distribution"""
        if not node.get('children'):
            node['weight'] = 1
            return 1
        
        weight = sum(self._calculate_subtree_weight(child) for child in node['children'])
        node['weight'] = weight
        return weight

    def _measure_text_size(self, text: str, depth_level: int, font_file: str = None) -> Tuple[int, int]:
        """
        Estimate node dimensions (wrap-aware, border-aware)
        """
        try:
            from PIL import Image, ImageDraw

            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Node{depth_level}"

            font_size = max(42 - depth_level * 6, 24)
            font = load_font(font_file, font_size)
            if font is None:
                return len(safe_text) * font_size * 0.6 + 20, font_size + 20

            spacing = max(int(font_size * 0.28), 6)
            display = "\n".join(wrap_text(safe_text))
            draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            bbox = draw.multiline_textbbox((0, 0), display, font=font, spacing=spacing, align="center")
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            pad_x = max(18 - depth_level * 2, 10)
            pad_y = max(14 - depth_level, 9)
            border = node_border_width(depth_level)
            return text_width + 2 * pad_x + 2 * border, text_height + 2 * pad_y + 2 * border

        except Exception:
            return len(str(text)) * 15 + 20, 40
    def _generate_center_layout(self, tree_data: dict, output_file: str, temp_dir: str,
                              watermark_text: str = None, opacity: int = 40,
                              layout: str = 'corners', theme=None) -> bool:
        """
        Generate Center/Radial Mind Map with optimized compact layout and Watermark
        """
        try:
            theme = get_theme(theme)
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            from tools.mpl_compat import import_matplotlib_agg
            import_matplotlib_agg()
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw

            self._calculate_subtree_weight(tree_data)
            
            branch_colors = theme['branch_colors']
            
            layout_nodes = []
            placed_boxes = []
            min_radius_by_depth = {} 
            parent_radius_map = {} 

            def check_collision(x, y, w, h, margin=20):
                l1, r1 = x - w/2 - margin, x + w/2 + margin
                t1, b1 = y - h/2 - margin, y + h/2 + margin
                
                for bx, by, bw, bh in placed_boxes:
                    l2, r2 = bx - bw/2, bx + bw/2
                    t2, b2 = by - bh/2, by + bh/2
                    
                    if not (l1 > r2 or r1 < l2 or t1 > b2 or b1 < t2):
                        return True
                return False

            def get_min_radius_for_depth(depth_level, parent_radius=0, parent_size=None, current_size=None):
                base_min_radius = 100 + (depth_level - 1) * 120
                if parent_radius > 0:
                    if parent_size and current_size:
                        parent_diagonal = math.sqrt(parent_size[0]**2 + parent_size[1]**2) / 2
                        current_diagonal = math.sqrt(current_size[0]**2 + current_size[1]**2) / 2
                        safe_distance = parent_diagonal + current_diagonal + 30 
                    else:
                        safe_distance = 60 
                    
                    required_radius = parent_radius + safe_distance
                    base_min_radius = max(base_min_radius, required_radius)
                
                if depth_level not in min_radius_by_depth:
                    min_radius_by_depth[depth_level] = base_min_radius
                else:
                    min_radius_by_depth[depth_level] = max(min_radius_by_depth[depth_level], base_min_radius)
                
                return min_radius_by_depth[depth_level]

            def layout_recursive(node, parent_x, parent_y, start_angle, end_angle, depth_level, inherited_color, parent_radius=0, parent_size=None, node_id=None):
                content = node.get('content', 'Node')
                children = node.get('children', [])
                
                if node_id is None:
                    node_id = f"node_{depth_level}_{id(node)}"
                
                w, h = self._measure_text_size(content, depth_level, font_file)
                current_size = (w, h)
                
                if depth_level == 1:
                    x, y = 0, 0
                    node_color = theme['root_color']
                    current_radius = 0
                else:
                    node_color = inherited_color
                    min_radius = get_min_radius_for_depth(depth_level, parent_radius, parent_size, current_size)
                    
                    mid_angle = (start_angle + end_angle) / 2
                    radius_base = min_radius
                    
                    base_step = 20 + (depth_level - 1) * 5 
                    max_attempts = 150 
                    
                    final_x, final_y = 0, 0
                    placed = False
                    current_radius = 0
                    
                    for attempt in range(max_attempts):
                        step = base_step * (1 + attempt * 0.05) 
                        test_r = radius_base + attempt * step
                        
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
                        final_x = test_r * math.cos(mid_angle)
                        final_y = test_r * math.sin(mid_angle)
                        current_radius = test_r
                    
                    x, y = final_x, final_y
                    
                    if current_radius > min_radius_by_depth.get(depth_level, 0):
                        if current_radius > min_radius_by_depth.get(depth_level, 0) * 1.2:
                            min_radius_by_depth[depth_level] = current_radius
                
                parent_radius_map[node_id] = current_radius
                placed_boxes.append((x, y, w, h))
                
                node_info = {
                    'x': x, 'y': y, 
                    'parent_x': parent_x, 'parent_y': parent_y,
                    'text': content, 'depth': depth_level, 
                    'color': node_color, 'width': w, 'height': h
                }
                layout_nodes.append(node_info)
                
                if children:
                    total_weight = sum(child.get('weight', 1) for child in children)
                    angle_range = end_angle - start_angle
                    
                    current_angle = start_angle
                    
                    for i, child in enumerate(children):
                        child_weight = child.get('weight', 1)
                        child_angle_step = (child_weight / total_weight) * angle_range
                        
                        child_start = current_angle
                        child_end = current_angle + child_angle_step
                        
                        if depth_level == 1:
                            child_c = branch_colors[i % len(branch_colors)]
                        else:
                            child_c = inherited_color
                        
                        child_node_id = f"{node_id}_child_{i}"
                        layout_recursive(child, x, y, child_start, child_end, depth_level + 1, child_c, 
                                       parent_radius=current_radius, parent_size=current_size, node_id=child_node_id)
                        
                        current_angle += child_angle_step

            layout_recursive(tree_data, 0, 0, 0, 2*math.pi, 1, theme['root_color'], parent_radius=0, parent_size=None, node_id='root')
            
            if not layout_nodes:
                return False
            
            min_x = min(n['x'] - n['width']/2 for n in layout_nodes)
            max_x = max(n['x'] + n['width']/2 for n in layout_nodes)
            min_y = min(n['y'] - n['height']/2 for n in layout_nodes)
            max_y = max(n['y'] + n['height']/2 for n in layout_nodes)
            
            max_radius = 0
            for n in layout_nodes:
                node_radius = math.sqrt(n['x']**2 + n['y']**2)
                node_diagonal = math.sqrt(n['width']**2 + n['height']**2) / 2
                total_radius = node_radius + node_diagonal
                max_radius = max(max_radius, total_radius)
            
            max_depth = max(n['depth'] for n in layout_nodes) if layout_nodes else 1
            base_margin = 150
            depth_margin = max_depth * 30 
            margin = base_margin + depth_margin
            
            total_width = max_x - min_x + 2 * margin
            total_height = max_y - min_y + 2 * margin
            
            min_size_from_radius = (max_radius + margin) * 2
            total_width = max(total_width, min_size_from_radius, 1000)
            total_height = max(total_height, min_size_from_radius, 800)
            
            dpi = 100
            fig_width = total_width / dpi
            fig_height = total_height / dpi

            dpi = budget_dpi(fig_width, fig_height)
            fig, ax = new_figure(fig_width, fig_height, dpi)
            
            ax.set_xlim(min_x - margin, max_x + margin)
            ax.set_ylim(min_y - margin, max_y + margin)
            ax.axis('off')
            
            def draw_curved_branch_line(start_x, start_y, end_x, end_y, color='#333333', linewidth=3):
                if abs(start_x - end_x) < 0.01 and abs(start_y - end_y) < 0.01:
                    return
                
                dx = end_x - start_x
                dy = end_y - start_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < 0.1:
                    ax.plot([start_x, end_x], [start_y, end_y], color=color, linewidth=linewidth, alpha=0.8)
                    return
                
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

            for node in layout_nodes:
                if node['depth'] > 1:
                    line_width = line_linewidth_for(node['depth'])
                    draw_curved_branch_line(node['parent_x'], node['parent_y'], 
                                          node['x'], node['y'], 
                                          color=node['color'], linewidth=line_width)
            
            ax.set_position([0, 0, 1, 1]) 
            
            temp_base_file = os.path.join(temp_dir, "base_center_mindmap.png")
            fig.savefig(temp_base_file, dpi=dpi, facecolor=theme['background'], edgecolor='none', format='png')
            
            base_img = Image.open(temp_base_file)

            # Apply Background Watermark
            if watermark_text:
                 base_img = add_watermark(base_img, watermark_text, opacity, layout, font_file)

            draw = ImageDraw.Draw(base_img)
            img_w, img_h = base_img.size
            draw_canvas_grid(base_img, draw, theme)
            
            x_range = (max_x + margin) - (min_x - margin)
            y_range = (max_y + margin) - (min_y - margin)
            
            def data_to_pixel(x, y):
                px = (x - (min_x - margin)) / x_range * img_w
                py = img_h - (y - (min_y - margin)) / y_range * img_h 
                return px, py
            
            for node in layout_nodes:
                px, py = data_to_pixel(node['x'], node['y'])
                self._draw_text_with_pil(
                    base_img, draw, px, py,
                    node['text'], node['depth'], 
                    node['color'], font_file, theme['node_fill']
                )
            
            base_img.save(output_file, 'PNG')
            return True
            
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    # ==========================================
    # Horizontal Layout Specific Methods
    # ==========================================

    def _estimate_text_width(self, text: str, depth_level: int) -> float:
        """
        Estimate node width in coordinate units (wrap-aware).
        """
        return estimate_width_units(text, depth_level)
    def _calculate_subtree_layout_data(self, node: dict, depth_level: int = 1) -> float:
        """
        Pass 1: Calculate vertical height AND estimate horizontal width for each node.
        """
        children = node.get('children', [])
        content = node.get('content', 'Node')
        
        node['_width'] = self._estimate_text_width(content, depth_level)
        base_node_height = node_height_units(content, depth_level)
        
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

    def _assign_coordinates_to_tree(self, node, x, y_center, branch_colors, inherited_color, depth_level, root_color='#333333'):
        """
        Pass 2: Assign coordinates using variable width for precise spacing.
        """
        children = node.get('children', [])
        
        if depth_level == 1:
            color = root_color
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

    def _draw_horizontal_lines(self, ax, node):
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
            linewidth = line_linewidth_for(child['depth'])
            
            self._draw_bezier_curve(ax, line_start_x, start_y, line_end_x, end_y, 
                                  visual_start_x, visual_end_x,
                                  color, linewidth)
            
            self._draw_horizontal_lines(ax, child)

    def _generate_horizontal_layout(self, tree_data: dict, output_file: str, temp_dir: str,
                              watermark_text: str = None, opacity: int = 40,
                              layout: str = 'corners', theme=None) -> bool:
        """
        Generate Horizontal Mind Map with Watermark
        """
        try:
            theme = get_theme(theme)
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            from tools.mpl_compat import import_matplotlib_agg
            import_matplotlib_agg()
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw

            self._calculate_subtree_layout_data(tree_data)
            
            branch_colors = theme['branch_colors']
            self._assign_coordinates_to_tree(tree_data, 0, 0, branch_colors, theme['root_color'], 1, theme['root_color'])
            
            all_nodes = self._get_all_nodes_with_coords(tree_data)
            if not all_nodes:
                return False
            
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
            
            margin_x = 2.0
            margin_y = 1.5
            content_width = max_x - min_x + 2 * margin_x
            content_height = max_y - min_y + 2 * margin_y
            
            content_width = max(content_width, 12)
            content_height = max(content_height, 8)
            
            fig_width = content_width * 0.8
            fig_height = content_height * 0.8
            
            if fig_width > 200: fig_width = 200
            if fig_height > 200: fig_height = 200
            
            render_dpi = budget_dpi(fig_width, fig_height)
            fig, ax = new_figure(fig_width, fig_height, render_dpi)
            ax.set_xlim(min_x - margin_x, max_x + margin_x)
            ax.set_ylim(min_y - margin_y, max_y + margin_y)
            ax.axis('off')
            
            self._draw_horizontal_lines(ax, tree_data)
            
            ax.set_position([0, 0, 1, 1])
            
            temp_base_file = os.path.join(temp_dir, "base_horizontal.png")
            fig.savefig(temp_base_file, dpi=render_dpi, facecolor=theme['background'], edgecolor='none', format='png')
            
            base_img = Image.open(temp_base_file)

            # Apply Background Watermark
            if watermark_text:
                 base_img = add_watermark(base_img, watermark_text, opacity, layout, font_file)

            draw = ImageDraw.Draw(base_img)
            img_w, img_h = base_img.size
            draw_canvas_grid(base_img, draw, theme)
            
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
                                       node['color'], font_file, theme['node_fill'])
            
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
            markdown_content = tool_parameters.get('markdown_content', '').strip()
            filename = tool_parameters.get('filename', '').strip()
            download_md = tool_parameters.get('download_md', False)
            
            # Watermark Params
            watermark_text = tool_parameters.get('watermark_text', '')
            opacity = tool_parameters.get('opacity', 40)
            watermark_layout = tool_parameters.get('watermark_layout', 'tile')
            theme_name = tool_parameters.get('theme', 'industrial')

            if not markdown_content:
                yield self.create_text_message('Free mind map generation failed: No Markdown content provided.')
                return
            
            display_filename = filename if filename else f"mindmap_free_{int(time.time())}"
            display_filename = re.sub(r'[^\w\-_\.]', '_', display_filename)
            
            if not display_filename.endswith('.png'):
                display_filename += '.png'
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_output_path = os.path.join(temp_dir, display_filename)
                
                tree_data = self._parse_markdown_to_tree(markdown_content)
                layout_mode = self._analyze_structure_complexity(tree_data)
                
                if layout_mode == 'horizontal':
                    _generate = self._generate_horizontal_layout
                else:
                    _generate = self._generate_center_layout
                with RENDER_GATE:
                    success = run_heavy(_generate, tree_data, temp_output_path, temp_dir,
                                        watermark_text, opacity, watermark_layout, theme_name)
                
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
                        "layout_type": "smart_free_structure",
                        "selected_mode": layout_mode,
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
                    
                    with SEND_GATE:
                        yield blob_message
                    yield self.create_text_message(f'Free mind map generation successful (Mode: {layout_mode})! Image File size: {size_text}')
                    yield self.create_json_message(json_data)
                    
                    if download_md:
                        md_filename = display_filename.replace('.png', '.md')
                        md_data = markdown_content.encode('utf-8')
                        md_blob_message = self.create_blob_message(
                            blob=md_data,
                            meta={'mime_type': 'text/markdown', 'filename': md_filename}
                        )
                        yield md_blob_message
                        yield self.create_text_message(f', Markdown file downloaded: {md_filename}')
                else:
                    json_data = {
                        "layout_type": "smart_free_structure",
                        "selected_mode": layout_mode,
                        "success": False,
                        "error": "Unable to create image file"
                    }
                    yield self.create_text_message('Free mind map generation failed: Unable to create image file.')
                    yield self.create_json_message(json_data)
        
        except Exception as e:
            error_msg = str(e)
            json_data = {
                "layout_type": "smart_free_structure",
                "success": False,
                "error": error_msg
            }
            yield self.create_text_message(f'Free mind map generation failed: {error_msg}')
            yield self.create_json_message(json_data)

def get_tool():
    return MindMapFreeWatermarkTool

