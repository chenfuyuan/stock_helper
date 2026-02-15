import pandas as pd
from loguru import logger

from src.modules.data_engineering.domain.dtos.concept_dtos import (
    ConceptConstituentDTO,
    ConceptInfoDTO,
)
from src.modules.data_engineering.domain.ports.providers.concept_data_provider import (
    IConceptDataProvider,
)
from src.modules.data_engineering.infrastructure.external_apis.akshare.base_client import (
    AkShareBaseClient,
)
from src.modules.data_engineering.infrastructure.external_apis.akshare.converters.stock_code_converter import (
    convert_akshare_stock_code,
)
from src.shared.domain.exceptions import AppException


class AkShareConceptClient(AkShareBaseClient, IConceptDataProvider):
    """
    akshare 概念数据客户端（基础设施层适配器）
    实现 IConceptDataProvider 接口，调用 akshare API 获取东方财富概念板块数据
    """

    async def fetch_concept_list(self) -> list[ConceptInfoDTO]:
        """
        获取所有概念板块列表
        调用 akshare.stock_board_concept_name_em() 接口
        
        Returns:
            list[ConceptInfoDTO]: 概念板块列表
            
        Raises:
            AppException: API 调用失败时抛出
        """
        try:
            import akshare as ak

            logger.info("开始获取概念板块列表")
            df: pd.DataFrame = await self._rate_limited_call(ak.stock_board_concept_name_em)

            if df is None or df.empty:
                logger.warning("akshare 返回空的概念板块列表")
                return []

            # akshare 返回的列名：板块代码、板块名称等
            # 需要转换为 ConceptInfoDTO
            concepts: list[ConceptInfoDTO] = []
            for _, row in df.iterrows():
                # 根据 akshare 实际返回的列名进行映射
                # 常见列名：板块代码、板块名称
                code = str(row.get("板块代码", "")).strip() if "板块代码" in row else ""
                name = str(row.get("板块名称", "")).strip() if "板块名称" in row else ""

                # 过滤空值
                if not code or not name:
                    continue

                concepts.append(ConceptInfoDTO(code=code, name=name))

            logger.info(f"成功获取 {len(concepts)} 个概念板块")
            return concepts

        except ImportError as e:
            logger.error("akshare 库未安装或导入失败")
            raise AppException(
                status_code=500,
                code="AKSHARE_IMPORT_ERROR",
                message="akshare 数据服务不可用",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"获取概念板块列表失败：{str(e)}")
            raise AppException(
                status_code=500,
                code="AKSHARE_API_ERROR",
                message="获取概念板块列表失败",
                details=f"stock_board_concept_name_em API 调用失败: {str(e)}",
            )

    async def fetch_concept_constituents(self, symbol: str) -> list[ConceptConstituentDTO]:
        """
        获取指定概念板块的成份股列表
        调用 akshare.stock_board_concept_cons_em(symbol=<概念名称>) 接口
        
        Args:
            symbol: 概念板块名称（如 "低空经济"）
            
        Returns:
            list[ConceptConstituentDTO]: 成份股列表，股票代码已转换为系统标准格式
            
        Raises:
            AppException: API 调用失败时抛出
        """
        try:
            import akshare as ak

            logger.debug(f"开始获取概念「{symbol}」的成份股")
            df: pd.DataFrame = await self._rate_limited_call(
                ak.stock_board_concept_cons_em, symbol=symbol
            )

            if df is None or df.empty:
                logger.warning(f"概念「{symbol}」无成份股数据")
                return []

            # akshare 返回的列名：代码、名称等
            # 需要转换为 ConceptConstituentDTO
            constituents: list[ConceptConstituentDTO] = []
            for _, row in df.iterrows():
                # 根据 akshare 实际返回的列名进行映射
                raw_code = str(row.get("代码", "")).strip() if "代码" in row else ""
                stock_name = str(row.get("名称", "")).strip() if "名称" in row else ""

                if not raw_code or not stock_name:
                    continue

                # 转换股票代码为系统标准格式
                standard_code = convert_akshare_stock_code(raw_code)
                if not standard_code:
                    logger.warning(f"概念「{symbol}」中股票代码 {raw_code} 转换失败，跳过")
                    continue

                constituents.append(
                    ConceptConstituentDTO(stock_code=standard_code, stock_name=stock_name)
                )

            logger.debug(f"概念「{symbol}」成功获取 {len(constituents)} 个成份股")
            return constituents

        except ImportError as e:
            logger.error("akshare 库未安装或导入失败")
            raise AppException(
                status_code=500,
                code="AKSHARE_IMPORT_ERROR",
                message="akshare 数据服务不可用",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"获取概念「{symbol}」成份股失败：{str(e)}")
            raise AppException(
                status_code=500,
                code="AKSHARE_API_ERROR",
                message=f"获取概念「{symbol}」成份股失败",
                details=f"stock_board_concept_cons_em API 调用失败: {str(e)}",
            )
