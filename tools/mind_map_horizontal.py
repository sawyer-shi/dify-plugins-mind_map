#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Horizontal Layout Mind Map Tool
Generates optimized left-to-right mind maps from Markdown text.
Features:
- Overlap prevention using Subtree-Aware Layout Algorithm (Vertical)
- Text-Width-Aware Horizontal Spacing (Horizontal Overlap Prevention)
- Dynamic canvas expansion for complex trees
- PIL-based Chinese font support
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

from tools.themes import draw_canvas_grid, get_theme
from tools.mind_map_style import RENDER_GATE, SEND_GATE, budget_dpi, estimate_width_units, load_font, new_figure, node_height_units, render_scale, run_heavy, wrap_text


class MindMapHorizontalTool(Tool):
    
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
        Estimate node width in coordinate units (wrap-aware).
        """
        return estimate_width_units(text, depth_level)
    def _calculate_subtree_layout_data(self, node: dict, depth_level: int = 1) -> float:
        """
        Pass 1: Calculate vertical height AND estimate horizontal width for each node.
        """
        children = node.get('children', [])
        content = node.get('content', 'Node')
        
        # Calculate and store self width
        node['_width'] = self._estimate_text_width(content, depth_level)
        
        # Basic height unit
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
            
        # Calculate X position for children based on parent's actual width
        # We need: Parent Half Width + Connector Length + Child Half Width (variable)
        # Simplified: Parent Right Edge + Gap
        
        parent_width = node['_width']
        connector_length = 2.0 # Fixed minimum length for the curved line
        
        max_child_width = 0
        for child in children:
            max_child_width = max(max_child_width, child['_width'])
            
        dist_to_children = (parent_width / 2) + connector_length + (max_child_width / 2)
        
        child_x = x + dist_to_children
        
        # Calc Y positions
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
        # Line starts from right edge of parent text box
        parent_width = node['_width']
        
        # Visual edge (where the box ends visually)
        visual_start_x = start_x + (parent_width / 2)
        
        # Actual line start (retracted into the box to ensure connection)
        # Retract by 40% of half-width to be safe against width estimation errors
        line_start_x = start_x + (parent_width / 2) * 0.6
        
        for child in children:
            end_x, end_y = child['x'], child['y']
            child_width = child['_width']
            
            # Visual edge
            visual_end_x = end_x - (child_width / 2)
            
            # Actual line end (retracted)
            line_end_x = end_x - (child_width / 2) * 0.6
            
            color = child['color']
            linewidth = max(3 - child['depth'] * 0.3, 1)
            
            # Draw bezier using both visual and actual points
            self._draw_bezier_curve(ax, line_start_x, start_y, line_end_x, end_y, 
                                  visual_start_x, visual_end_x,
                                  color, linewidth)
            
            # Recurse
            self._draw_lines_recursive(ax, child)

    def _draw_bezier_curve(self, ax, start_x, start_y, end_x, end_y, 
                          visual_start_x, visual_end_x, color, linewidth):
        import numpy as np
        
        # Calculate control points based on VISUAL boundaries for correct curvature shape
        # If we used retracted points, the curve might bend inside the box
        
        dist = math.sqrt((visual_end_x - visual_start_x)**2 + (end_y - start_y)**2)
        h_dist = abs(visual_end_x - visual_start_x)
        
        # Control points extending from visual edges
        cp_dist = min(h_dist * 0.6, 4.0)
        
        cp1_x = visual_start_x + cp_dist
        cp1_y = start_y
        
        cp2_x = visual_end_x - cp_dist
        cp2_y = end_y
        
        # Generate curve points
        t = np.linspace(0, 1, 50)
        
        # Bezier formula
        x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
        y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
        
        ax.plot(x, y, color=color, linewidth=linewidth, alpha=0.7)

    def _draw_text_with_pil(self, img, draw, x, y, text, depth_level, color, font_file, node_fill='white'):
        """
        Draw node text with PIL (wrap-aware, render-scale aware)
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

            padding = max(int(round((18 - depth_level * 2) * px)), int(round(10 * px)))
            border_width = 4 if depth_level == 1 else 3
            border_width = max(1, int(round(border_width * px)))

            box_width = text_width + 2 * padding
            box_height = text_height + 2 * padding

            box_x1 = x - box_width / 2
            box_y1 = y - box_height / 2
            box_x2 = x + box_width / 2
            box_y2 = y + box_height / 2

            radius = max(1, int(round(5 * px)))
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2],
                                   radius=min(radius, int(box_width / 2), int(box_height / 2)),
                                   fill=node_fill, outline=color, width=border_width)

            try:
                draw.multiline_text((x, y), display, font=font, fill=color,
                                    anchor="mm", align="center", spacing=spacing)
            except TypeError:
                draw.multiline_text((x - text_width / 2, y - text_height / 2), display,
                                    font=font, fill=color, align="center", spacing=spacing)

        except Exception:
            pass
    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str, theme=None) -> bool:
        """
        Generate PNG mind map using optimized layout engine
        """
        try:
            # Setup fonts
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            from tools.mpl_compat import import_matplotlib_agg
            import_matplotlib_agg()
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw
            
            # 1. Calc heights AND widths
            self._calculate_subtree_layout_data(tree_data)
            
            # 2. Assign Coordinates (Store in tree nodes)
            theme = get_theme(theme)
            branch_colors = theme['branch_colors']
            self._assign_coordinates_to_tree(tree_data, 0, 0, branch_colors, theme['root_color'], 1, theme['root_color'])
            
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
                # Height is roughly fixed/estimated as 1.0 unit for calculation
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
            
            render_dpi = budget_dpi(fig_width, fig_height)
            fig, ax = new_figure(fig_width, fig_height, render_dpi)
            ax.set_xlim(min_x - margin_x, max_x + margin_x)
            ax.set_ylim(min_y - margin_y, max_y + margin_y)
            ax.axis('off')
            
            # 4. Draw Lines
            self._draw_lines_recursive(ax, tree_data)
            
            # 5. Save Base Image
            ax.set_position([0, 0, 1, 1])
            
            temp_base_file = os.path.join(temp_dir, "base_horizontal.png")
            fig.savefig(temp_base_file, dpi=render_dpi, facecolor=theme['background'], edgecolor='none')
            
            # 6. Draw Text with PIL
            base_img = Image.open(temp_base_file)
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
            download_md = tool_parameters.get('download_md', False)
            theme_name = tool_parameters.get('theme', 'industrial')
            
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
                
                with RENDER_GATE:
                    success = run_heavy(self._generate_png_mindmap, tree_data, temp_output_path, temp_dir, theme_name)
                
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
                    
                    with SEND_GATE:
                        yield blob_message
                    yield self.create_text_message(f'Horizontal mind map generated successfully! Image File Size: {size_text}')
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
                    yield self.create_text_message('Generation failed: Unable to create image file.')
        
        except Exception as e:
            yield self.create_text_message(f'Generation failed: {str(e)}')

def get_tool():
    return MindMapHorizontalTool
