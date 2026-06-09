from pydantic import BaseModel, Field
from typing import Optional

class AlphaStock(BaseModel):
    """
    AlphaTide 实盘标准股票数据结构 (Pydantic 强制校验)
    任何流转于各模块间的标的数据都必须遵循此契约，防止弱类型导致的静默失败。
    """
    symbol: str = Field(..., description="股票代码，必须包含 sh 或 sz 前缀，例如 sh600519")
    name: str = Field(default="未知", description="股票名称")
    ai_reason: str = Field(default="", description="AI 挖掘其作为龙头的核心业务理由")
    
    current_price: Optional[float] = Field(default=None, description="当前最新价")
    momentum_20d: Optional[float] = Field(default=None, description="近 20 日动量(%)")
    vcp_status: str = Field(default="Unknown", description="VCP 波动率收缩状态描述")
    
    # 状态灯，用于生成实盘战报
    status_light: str = Field(default="🟡", description="当前监控状态灯(🟢🟡🔴⚪)")

    class Config:
        validate_assignment = True
        
    def get_clean_symbol(self) -> str:
        """获取去除前缀的纯数字代码，用于 Akshare 部分接口"""
        return self.symbol.replace('sh', '').replace('sz', '')
