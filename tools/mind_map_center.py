#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Center Layout Mind Map Tool
Generates radial mind maps from Markdown text with enhanced Chinese font support
Supports unlimited dynamic hierarchical structures
"""

import os
import re
import tempfile
import time
import math
from typing import Any, Dict, Generator, List

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class MindMapCenterTool(Tool):
    
    def _setup_chinese_fonts(self):
        """
        更强力的中文字体设置，使用最直接的系统字体路径
        """
        import matplotlib
        matplotlib.use('Agg')  # 必须在其他导入之前设置
        
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        
        # 最强力的UTF-8环境设置
        import sys
        import locale
        import platform
        
        # 多重环境变量设置
        utf8_vars = {
            'LANG': 'zh_CN.UTF-8',
            'LC_ALL': 'zh_CN.UTF-8', 
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONUTF8': '1',
        }
        
        for key, value in utf8_vars.items():
            os.environ[key] = value
        
        # 强制设置Python内部编码
        if hasattr(sys, 'setdefaultencoding'):
            sys.setdefaultencoding('utf-8')
        
        # 获取系统平台
        system = platform.system()
        
        # 清理所有字体缓存
        try:
            import shutil
            # 清除matplotlib缓存
            cache_dir = matplotlib.get_cachedir()
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir, ignore_errors=True)
            # 重建字体管理器
            matplotlib.font_manager._rebuild()
        except Exception as e:
            print(f"Font cache cleanup: {e}")
        
        # 直接使用系统字体文件路径
        font_found = None
        
        if system == 'Windows':
            # Windows系统字体的绝对路径
            windows_fonts = [
                r'C:\Windows\Fonts\msyh.ttc',      # 微软雅黑
                r'C:\Windows\Fonts\msyhbd.ttc',    # 微软雅黑粗体
                r'C:\Windows\Fonts\simhei.ttf',    # 黑体
                r'C:\Windows\Fonts\simsun.ttc',    # 宋体
                r'C:\Windows\Fonts\simkai.ttf',    # 楷体
                r'C:\Windows\Fonts\simfang.ttf',   # 仿宋
            ]
            
            for font_path in windows_fonts:
                if os.path.exists(font_path):
                    try:
                        # 直接加载字体文件
                        prop = fm.FontProperties(fname=font_path)
                        # 测试字体
                        fig, ax = plt.subplots(figsize=(1, 1))
                        ax.text(0.5, 0.5, '测试中文', fontproperties=prop)
                        plt.close(fig)
                        font_found = prop
                        print(f"✅ 成功加载中文字体: {font_path}")
                        break
                    except Exception as e:
                        print(f"字体加载失败: {font_path}, {e}")
                        continue
                        
        elif system == 'Darwin':  # macOS
            macos_fonts = [
                '/Library/Fonts/Arial Unicode.ttf',
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/PingFang.ttc',
            ]
            for font_path in macos_fonts:
                if os.path.exists(font_path):
                    try:
                        prop = fm.FontProperties(fname=font_path)
                        font_found = prop
                        break
                    except:
                        continue
                        
        else:  # Linux
            linux_fonts = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            ]
            for font_path in linux_fonts:
                if os.path.exists(font_path):
                    try:
                        prop = fm.FontProperties(fname=font_path)
                        font_found = prop
                        break
                    except:
                        continue
        
        # 设置matplotlib全局字体配置
        if font_found:
            plt.rcParams['font.family'] = [font_found.get_name()]
        else:
            # 后备字体名称设置
            if system == 'Windows':
                plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
            elif system == 'Darwin':
                plt.rcParams['font.sans-serif'] = ['STHeiti', 'PingFang SC', 'Arial Unicode MS']
            else:
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'WenQuanYi Micro Hei']
        
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
        
        return font_found
    
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

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, title: str = "Mind Map", layout_type: str = "center") -> bool:
        """
        Generate PNG mind map with perfect Chinese character rendering and consistent colors
        """
        try:
            # 更强力的中文字体设置
            chinese_font_prop = self._setup_chinese_fonts()
            
            import matplotlib
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            from matplotlib.patches import FancyBboxPatch, ConnectionPatch
            import numpy as np
            
            # FIXED: Limit canvas size to prevent performance issues
            tree_depth = self._calculate_tree_depth(tree_data)
            max_children = max([len(node.get('children', [])) for node in [tree_data] + self._get_all_nodes(tree_data)] + [1])
            
            # Calculate optimal but LIMITED canvas size
            base_size = 12  # Reduced from 16
            max_width = 20   # Maximum width limit
            max_height = 16  # Maximum height limit
            
            width = min(base_size + (tree_depth * 2), max_width)   # Reduced multiplier from 4 to 2
            height = min(base_size + (max_children * 1), max_height)  # Reduced multiplier from 2 to 1
            
            fig, ax = plt.subplots(1, 1, figsize=(width, height))
            
            # FIXED: Limit axis ranges for better density
            max_axis_limit = 10  # Reduced from unlimited
            axis_limit = min(max_axis_limit, max(8, tree_depth * 2, max_children))
            ax.set_xlim(-axis_limit, axis_limit)
            ax.set_ylim(-axis_limit, axis_limit)
            ax.axis('off')
            
            # Compact color palette
            branch_colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', 
                '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43', '#EE5A24', '#0984E3'
            ]
            
            def draw_curved_branch_line(start_x, start_y, end_x, end_y, color='#333333', linewidth=3):
                """Draw smooth curved branch line with better control"""
                if abs(start_x - end_x) < 0.01 and abs(start_y - end_y) < 0.01:
                    return  # Skip if points are too close
                
                dx = end_x - start_x
                dy = end_y - start_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < 0.1:  # Too close, draw straight line
                    ax.plot([start_x, end_x], [start_y, end_y], color=color, linewidth=linewidth, alpha=0.8)
                    return
                
                control_distance = min(distance * 0.4, 2.0)  # Limit control distance
                
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
                
                t = np.linspace(0, 1, 50)  # Reduced points for performance
                curve_x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
                curve_y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
                
                ax.plot(curve_x, curve_y, color=color, linewidth=linewidth, alpha=0.8)
            
            def draw_text_label(x, y, text, depth_level, color='#333333'):
                """强化的中文文本渲染，确保UTF-8正确处理"""
                # 字体大小
                base_font_size = 14
                font_size = max(base_font_size - (depth_level * 2), 8)
                
                # 样式
                if depth_level == 1:  # Root
                    bbox_props = dict(boxstyle="round,pad=0.4", facecolor='white', 
                                    edgecolor=color, linewidth=2)
                    weight = 'bold'
                else:  # All other levels
                    padding = max(0.3 - (depth_level * 0.02), 0.15)
                    bbox_props = dict(boxstyle=f"round,pad={padding}", facecolor='white', 
                                    edgecolor=color, linewidth=1.5, alpha=0.9)
                    weight = 'normal'
                
                # 更强力的文本处理
                try:
                    # 确保输入是字符串
                    if isinstance(text, bytes):
                        safe_text = text.decode('utf-8', errors='replace')
                    else:
                        safe_text = str(text)
                    
                    # 清理空白字符
                    safe_text = safe_text.strip()
                    if not safe_text:
                        safe_text = f"Node{depth_level}"
                    
                    # 直接使用找到的字体进行渲染
                    if chinese_font_prop:
                        ax.text(x, y, safe_text, fontsize=font_size, weight=weight,
                               ha='center', va='center', color=color, bbox=bbox_props,
                               fontproperties=chinese_font_prop)
                    else:
                        # 强制使用系统默认中文字体
                        ax.text(x, y, safe_text, fontsize=font_size, weight=weight,
                               ha='center', va='center', color=color, bbox=bbox_props,
                               fontfamily='sans-serif')
                               
                except Exception as e:
                    print(f"文本渲染错误: {e}, 文本: {text}")
                    # 最终回退使用ASCII字符
                    try:
                        fallback_text = f"Text{depth_level}"
                        ax.text(x, y, fallback_text, fontsize=font_size, weight=weight,
                               ha='center', va='center', color=color, bbox=bbox_props)
                    except:
                        # 如果连ASCII都失败，使用最基础的绘制
                        ax.text(x, y, "Node", fontsize=font_size,
                               ha='center', va='center', color=color)

            def layout_dynamic_center_mindmap(node, center_x=0, center_y=0, depth_level=1, parent_angle=0, angle_range=2*math.pi, inherited_color='#333333'):
                """
                FIXED: 完全动态的中心布局，确保颜色一致性
                """
                root_content = node.get('content', 'Root')
                children = node.get('children', [])
                
                # FIXED: 使用继承的颜色或为根节点设置默认颜色
                if depth_level == 1:
                    node_color = '#333333'  # 根节点固定为深灰色
                else:
                    node_color = inherited_color  # 使用从父节点继承的颜色
                
                # 绘制当前节点
                draw_text_label(center_x, center_y, root_content, depth_level, node_color)
                
                if not children:
                    return [(center_x, center_y)]  # Return this node's position
                
                child_count = len(children)
                
                # FIXED: More compact radius calculation
                base_radius = 3.0    # Reduced from 5.0
                depth_factor = 0.3   # Reduced from 0.5
                child_factor = 0.05  # Reduced from 0.1
                radius = base_radius + (depth_level * depth_factor) + (child_count * child_factor)
                radius = min(radius, axis_limit * 0.3)  # Limit radius to prevent overflow
                
                # Calculate child angles
                if child_count == 1:
                    angles = [parent_angle if parent_angle != 0 else 0]
                else:
                    # Even distribution within available angle range
                    if depth_level == 1:  # Root level gets full circle
                        start_angle = 0
                        angle_step = 2 * math.pi / child_count
                    else:  # Child levels get limited range
                        start_angle = parent_angle - angle_range / 2
                        angle_step = angle_range / max(child_count - 1, 1) if child_count > 1 else 0
                    
                    angles = [start_angle + i * angle_step for i in range(child_count)]
                
                child_positions = []
                
                for i, (child, angle) in enumerate(zip(children, angles)):
                    # FIXED: Calculate child position relative to current center
                    child_x = center_x + radius * math.cos(angle)
                    child_y = center_y + radius * math.sin(angle)
                    
                    # Ensure child position is within bounds
                    child_x = max(-axis_limit + 1, min(axis_limit - 1, child_x))
                    child_y = max(-axis_limit + 1, min(axis_limit - 1, child_y))
                    
                    # FIXED: 为第一级子节点选择颜色，后续层级继承父节点颜色
                    if depth_level == 1:
                        # 根节点的直接子节点获得新颜色
                        branch_color = branch_colors[i % len(branch_colors)]
                    else:
                        # 更深层级的节点继承父节点的颜色
                        branch_color = inherited_color
                    
                    # FIXED: Draw connection line with consistent color
                    line_thickness = max(3 - depth_level * 0.5, 1)
                    draw_curved_branch_line(center_x, center_y, child_x, child_y, 
                                          color=branch_color, linewidth=line_thickness)
                    
                    # FIXED: Calculate proper angle range for child subtree
                    if len(child.get('children', [])) > 0:
                        child_angle_range = min(math.pi / 3, angle_range / max(child_count, 1))  # Limited range
                    else:
                        child_angle_range = 0
                    
                    # FIXED: 递归布局时传递颜色
                    child_positions_list = layout_dynamic_center_mindmap(
                        child, child_x, child_y, depth_level + 1, angle, child_angle_range, branch_color
                    )
                    child_positions.extend(child_positions_list)
                
                return [(center_x, center_y)] + child_positions

            # Execute layout
            all_positions = layout_dynamic_center_mindmap(tree_data)
            
            # FIXED: Save with optimized DPI for smaller file size
            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches='tight',  # Reduced DPI from 300 to 150
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            
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
                yield self.create_text_message('❌ Please provide Markdown text content.')
                return
            
            # Handle filename
            display_filename = filename if filename else f"mindmap_center_{int(time.time())}"
            display_filename = re.sub(r'[^\w\-_\.]', '_', display_filename)
            
            if not display_filename.endswith('.png'):
                display_filename += '.png'
            
            yield self.create_text_message('🌟 Generating perfect Chinese center layout mind map with consistent colors...')
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_output_path = os.path.join(temp_dir, display_filename)
                
                # Parse Markdown to tree structure
                tree_data = self._parse_markdown_to_tree(markdown_content)
                
                # Generate PNG mind map
                success = self._generate_png_mindmap(tree_data, temp_output_path, "Perfect Chinese Center Layout Mind Map", "center")
                
                if success and os.path.exists(temp_output_path):
                    # Read generated PNG file
                    with open(temp_output_path, 'rb') as f:
                        png_data = f.read()
                    
                    # Calculate file size in MB (as requested)
                    file_size = len(png_data)
                    size_mb = file_size / (1024 * 1024)  # Convert to MB
                    size_text = f"{size_mb:.2f}M"
                    
                    yield self.create_blob_message(
                        blob=png_data,
                        meta={'mime_type': 'image/png', 'filename': display_filename}
                    )
                    yield self.create_text_message(f'Perfect Chinese center layout mind map with consistent colors generated successfully! File size: {size_text}')
                else:
                    yield self.create_text_message('Mind map generation failed. Please check your Markdown format.')
        
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            print(f"❌ {error_msg}")
            yield self.create_text_message(f'Mind map generation failed: {str(e)}')


# Export tool class for Dify
def get_tool():
    return MindMapCenterTool 