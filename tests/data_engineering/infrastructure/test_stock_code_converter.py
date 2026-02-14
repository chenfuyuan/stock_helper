"""
单元测试：股票代码格式转换工具
覆盖深交所/上交所/创业板/科创板/北交所各场景
"""

import pytest

from src.modules.data_engineering.infrastructure.external_apis.akshare.converters.stock_code_converter import (
    convert_akshare_stock_code,
)


class TestStockCodeConverter:
    """测试股票代码格式转换工具"""

    def test_convert_shanghai_main_board(self):
        """测试上交所主板代码转换（6开头）"""
        assert convert_akshare_stock_code("601398") == "601398.SH"
        assert convert_akshare_stock_code("600000") == "600000.SH"
        assert convert_akshare_stock_code("603999") == "603999.SH"

    def test_convert_kcb_board(self):
        """测试科创板代码转换（688开头）"""
        assert convert_akshare_stock_code("688001") == "688001.SH"
        assert convert_akshare_stock_code("688888") == "688888.SH"

    def test_convert_shenzhen_main_board(self):
        """测试深交所主板/中小板代码转换（0开头）"""
        assert convert_akshare_stock_code("000001") == "000001.SZ"
        assert convert_akshare_stock_code("000002") == "000002.SZ"
        assert convert_akshare_stock_code("002001") == "002001.SZ"

    def test_convert_chinext_board(self):
        """测试创业板代码转换（3开头）"""
        assert convert_akshare_stock_code("300001") == "300001.SZ"
        assert convert_akshare_stock_code("300999") == "300999.SZ"

    def test_convert_beijing_board_4(self):
        """测试北交所代码转换（4开头）"""
        assert convert_akshare_stock_code("430001") == "430001.BJ"
        assert convert_akshare_stock_code("400001") == "400001.BJ"

    def test_convert_beijing_board_8(self):
        """测试北交所代码转换（8开头）"""
        assert convert_akshare_stock_code("830001") == "830001.BJ"
        assert convert_akshare_stock_code("870001") == "870001.BJ"

    def test_convert_empty_code(self):
        """测试空代码"""
        assert convert_akshare_stock_code("") is None
        assert convert_akshare_stock_code("   ") is None
        assert convert_akshare_stock_code(None) is None

    def test_convert_invalid_code(self):
        """测试无法识别的代码格式"""
        # 1、2、5、7、9 开头的代码无法识别
        assert convert_akshare_stock_code("100001") is None
        assert convert_akshare_stock_code("200001") is None
        assert convert_akshare_stock_code("500001") is None
        assert convert_akshare_stock_code("700001") is None
        assert convert_akshare_stock_code("900001") is None

    def test_convert_with_whitespace(self):
        """测试带空白字符的代码"""
        assert convert_akshare_stock_code("  000001  ") == "000001.SZ"
        assert convert_akshare_stock_code("\t601398\n") == "601398.SH"
