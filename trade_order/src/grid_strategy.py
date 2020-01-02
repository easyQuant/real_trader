# -*- coding: utf-8 -*-
import abc
import io
import tempfile
from typing import TYPE_CHECKING, Dict, List

import pandas as pd
import pywinauto.clipboard
import time

class IGridStrategy(abc.ABC):

    def __init__(self):
        pass

    @abc.abstractmethod
    def get(self, control_id: int) -> List[Dict]:
        """
        获取 gird 数据并格式化返回

        :param control_id: grid 的 control id
        :return: grid 数据
        """
        
        pass

class BaseStrategy(IGridStrategy):
    def __init__(self, trader) -> None:
        self._trader = trader

    @abc.abstractmethod
    def get(self, control_id: int) -> List[Dict]:
        """
        :param control_id: grid 的 control id
        :return: grid 数据
        """
        pass

    def _get_grid(self, control_id: int):
        grid = self._trader.main.child_window(
            control_id=control_id, class_name="CVirtualGridCtrl"
        )
        return grid

class Copy(BaseStrategy):
    """
    通过复制 grid 内容到剪切板z再读取来获取 grid 内容
    """

    def get(self, control_id: int) -> List[Dict]:
        # print('通过复制 grid 内容到剪切板z再读取来获取 grid 内容')

        time.sleep(0.3)

        grid = self._get_grid(control_id)
        grid.type_keys("^A^C")

    def _format_grid_data(self, data: str) -> List[Dict]:
        df = pd.read_csv(
            io.StringIO(data),
            delimiter="\t",
            dtype=self._trader.config.GRID_DTYPE,
            na_filter=False,
        )
        return df.to_dict("records")

    def _get_clipboard_data(self) -> str:
        while True:
            try:
                return pywinauto.clipboard.GetData()
            # pylint: disable=broad-except
            except Exception as e:
                pass
                # log.warning("%s, retry ......", e)