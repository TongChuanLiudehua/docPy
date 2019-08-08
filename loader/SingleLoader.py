"""
    dependencies
"""
import os
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SingleFileLoader - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SingleFileLoader:

    def __init__(self):
        self._file_path = ""
        self._file_format = ""  # .cpp, .hpp, .h, .py, .java, ...
        self._file_name = ""
        self.chunk = ""
        self.limitation = 1024*1024  # 1MB
        self.pages = []  # 对于超过限制大小的单个文件进行分页处理

    """
        setter方法
        void set_attr(v1,v2,v3)
        :param path : 文件路径
        :param name : 文件名
        :param format : 文件格式
        :return : void
    """
    def set_attr(self, path, name, format):
        assert format in ["cpp", "hpp", "h", "py", "java"]

        self._file_format = format
        self._file_name = name
        self._file_path = path

    """
        将文件加载进入内存，如果文件大小超过限制，则进行分页
        分页结果存入self.pages列表
        void load(void)
        :param:void
        :return :void
    """
    def load(self):
        assert self._file_path
        assert self._file_name

        try:
            file_size = os.path.getsize(self._file_path)
            logging.info("open file with size={}, aka={}MB".format(file_size, file_size / self.limitation))
            if file_size > self.limitation:  # if source code file's size bigger than 1MB
                read_size = 0
                with open(self._file_path, "r", encoding="utf8") as target:
                    while read_size*2 < file_size:  # TODO
                        self.chunk = target.read(self.limitation)
                        self.pages.append(self.chunk)
                        read_size += len(self.chunk)
                logging.info("pages = {}, read characters = {} ".format(len(self.pages), read_size))
            else:
                with open(self._file_path, "r") as target:
                    self.pages.append(target.read())

        except FileNotFoundError as e1:
            logging.error(msg="file: {} not exists".format(self._file_path))