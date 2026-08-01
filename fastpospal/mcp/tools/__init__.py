"""导入各业务域工具模块，触发 @mcp.tool 注册，并应用暴露 profile。"""

from fastpospal.mcp.instance import mcp
from fastpospal.mcp.profile import apply_tool_profile
from fastpospal.mcp.tools import (  # noqa: F401
    categories,
    customers,
    products,
    reports,
    semantic,
    session,
    stock,
    waimai,
)

apply_tool_profile(mcp)
