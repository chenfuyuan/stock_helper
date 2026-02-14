from loguru import logger


def convert_akshare_stock_code(raw_code: str) -> str | None:
    """
    将 akshare 返回的原始股票代码转换为系统标准 third_code 格式
    
    Args:
        raw_code: akshare 原始代码（如 "000001"、"601398"）
        
    Returns:
        str | None: 系统标准格式代码（如 "000001.SZ"、"601398.SH"），转换失败返回 None
        
    转换规则：
    - 6 开头 → .SH（上交所）
    - 68 开头 → .SH（科创板）
    - 0 开头 → .SZ（深交所）
    - 3 开头 → .SZ（创业板）
    - 4 或 8 开头 → .BJ（北交所）
    """
    if not raw_code or not raw_code.strip():
        return None
    
    code = raw_code.strip()
    
    # 科创板（688xxx）
    if code.startswith("68"):
        return f"{code}.SH"
    
    # 上交所（6xxxxx）
    if code.startswith("6"):
        return f"{code}.SH"
    
    # 深交所主板/中小板（000xxx、001xxx、002xxx）
    if code.startswith("0"):
        return f"{code}.SZ"
    
    # 创业板（300xxx）
    if code.startswith("3"):
        return f"{code}.SZ"
    
    # 北交所（43xxxx、83xxxx、87xxxx、92xxxx）
    if code.startswith("4") or code.startswith("92") or code.startswith("8"):
        return f"{code}.BJ"
    
    # 无法识别的代码格式
    logger.warning(f"无法识别的股票代码格式：{raw_code}")
    return None
