from typing import Any, List
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from tools.mind_map_center import MindMapCenterTool
from tools.mind_map_horizontal import MindMapHorizontalTool


class MindMapProvider(ToolProvider):
    """Mind map generator tool provider"""
    
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        验证凭据（此工具不需要特殊凭据）
        """
        pass
    
    def _get_tools(self) -> List[Any]:
        """
        返回可用的工具列表
        """
        return [MindMapCenterTool, MindMapHorizontalTool]


# 创建provider实例
mind_map_provider = MindMapProvider()
