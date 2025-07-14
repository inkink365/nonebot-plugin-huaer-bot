import json
import toml
import shutil
import datetime
from pathlib import Path
from typing import Dict, Any
from nonebot import logger, get_driver, require

require("nonebot_plugin_localstore")

from nonebot_plugin_localstore import get_data_dir

class ConfigManager:
    '''配置管理类'''

    @staticmethod
    def load_toml(file_path: Path) -> Dict[str, Any]:
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return toml.load(f)
            logger.error(f"TOML 不存在: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"加载 {file_path} 失败: {e}")
            return {}
    
    @staticmethod
    def save_toml(data: Dict[str, Any], file_path: Path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                toml.dump(data, f)
        except Exception as e:
            logger.error(f"保存 {file_path} 失败: {e}")

    @staticmethod
    def load_json(file_path: Path, default: dict) -> dict:
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default
        except Exception as e:
            logger.error(f"加载 {file_path} 失败: {e}")
            return default

    @staticmethod
    def save_json(data: dict, file_path: Path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 {file_path} 失败: {e}")

SELF_DIR = Path(__file__).resolve().parent

# 处理配置文件路径
CONFIG_DIR = SELF_DIR / "config.toml"
try:
    # 读取配置文件路径
    TEMP_DIR = Path(get_driver().config.huaer_config_path)

    if TEMP_DIR is not None:
        try:
            # 检查是否存在
            if not TEMP_DIR.exists():
                raise ValueError(f"路径 '{TEMP_DIR}' 不存在")
            
            # 检查是否为文件夹
            if not TEMP_DIR.is_dir():
                raise ValueError(f"路径 '{TEMP_DIR}' 不是文件夹")
            
            # 检查是否为绝对路径
            if not TEMP_DIR.is_absolute():
                raise ValueError(f"路径 '{TEMP_DIR}' 不是绝对路径")

            # 目标配置文件路径
            target_config = TEMP_DIR / "huaer_config.toml"
            default_config = SELF_DIR / "config.toml"

            # 如果配置文件不存在，复制默认配置
            if not target_config.exists():
                if not default_config.exists():
                    raise FileNotFoundError(f"默认配置文件 '{default_config}' 不存在")
                
                shutil.copy2(default_config, target_config)
                logger.info(f"已复制默认配置到: {target_config}")
            
            CONFIG_DIR = target_config

        except Exception as e:
            logger.error(f"配置文件异常: {e}")
except:
    logger.info(f"未设置配置文件路径, 使用默认配置")
    pass

# 数据存储目录
BASE_DIR = get_data_dir("nonebot_plugin_huaer_bot")

# 版本信息
MAJOR_VERSION = 2
MINOR_VERSION = 1
PATCH_VERSION = 9
VERSION_SUFFIX = "stable"

# 导入配置文件
cfg = ConfigManager.load_toml(CONFIG_DIR)

# 加载数据文件夹路径
paths_config = cfg["paths"]
        
data_dir = BASE_DIR / paths_config["data_dir"]
groups_dir = BASE_DIR / paths_config["groups_dir"]
public_dir = BASE_DIR / paths_config["public_dir"]
private_dir = BASE_DIR / paths_config["private_dir"]
whitelist_dir = BASE_DIR / paths_config["whitelist_dir"]
        
# 创建目录，确保所有必要的目录存在
data_dir.mkdir(exist_ok=True, parents=True)
groups_dir.mkdir(exist_ok=True, parents=True)
public_dir.mkdir(exist_ok=True, parents=True)
private_dir.mkdir(exist_ok=True, parents=True)
whitelist_dir.mkdir(exist_ok=True, parents=True)

# 解析数据文件夹路径
DATA_DIR = data_dir
GROUPS_DIR = groups_dir
PUBLIC_DIR = public_dir
PRIVATE_DIR = private_dir
WHITELIST = whitelist_dir

# 加载API配置
api_config = cfg["api"]

# 解析API配置
API_URL = api_config.get("url", "")
MODELS = api_config.get("models", [])
HEADERS = api_config.get("headers", {})
PRE_MOD = set(api_config.get("pre_mod", []))  # 转换为集合

# 加载文件路径配置
paths_config = cfg["files"]

# 解析文件路径
BASIC_FILE = BASE_DIR / paths_config.get("base_file", "")
USER_WHITELIST_FILE = BASE_DIR / paths_config.get("user_whitelist_file", "")
GROUP_WHITELIST_FILE = BASE_DIR / paths_config.get("group_whitelist_file", "")

# 加载白名单配置
whitelist_config = cfg["whitelist_config"]

# 解析白名单路径
WHITELIST_MODE  = whitelist_config.get("whitelist_mode", 0)

# 加载对话配置
basic_config = cfg["basic_config"]

class ChatConfig:
    '''变量容器类，配置的动态载体'''
    def __init__(self, ID: int):

        self.group = ID # ID : 此配置归属的组的ID
        self.file : Path = self._path_generation(ID) # 数据存储位置
        self.config_name : str = self._file_generation(ID)  # 配置文件名称

        self.rd : int = basic_config.get("rd", 6)
        self.mod : int = basic_config.get("mod", 3)
        self.prt : str= basic_config.get("prt", True)
        self.tkc : str = basic_config.get("tkc", False)
        self.mess : list = basic_config.get("memory", []) 
        self.cooldown : float = basic_config.get("cooldown", 300.0)
        self.max_token : int = basic_config.get("max_token", 1024)
        self.max_recall : int = min(self.rd , basic_config.get("max_recall", 2))
        self.current_personality : str= basic_config.get("default_personality", "你是名叫华尔的猫娘。") 

    def _path_generation(self, ID) -> Path:
        """生成数据存储位置的名称"""
        if ID == 0 :
            return PUBLIC_DIR
        elif ID == 1 :
            return PRIVATE_DIR
        else:
            return GROUPS_DIR / str(ID)

    def _file_generation(self, ID) -> str:
        """生成配置文件的名称"""
        if ID == 0 :
            return 'base'
        elif ID == 1 :
            return 'private_config'
        else:
            return 'group_config'

    def save_group(self) -> str:
        """一键保存群组配置"""
        save_path = self.file / f"{self.config_name}.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "rd" : self.rd,
            "prt" : self.prt,
            "mod" : self.mod,
            "tkc" : self.tkc,
            "memory" : self.mess,
            "cooldown" : self.cooldown,
            "max_token" : self.max_token,
            "max_recall" : self.max_recall,
            "default_personality" : self.current_personality,
        }
        
        try :
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return "✅ 保存成功"
        except Exception as e:
            logger.exception(f"未知保存错误：{e}")
            return "⚠️ 系统异常，请联系管理员"

    def load_group(self) -> str:
        """加载此群组的配置"""
        load_path = self.file / f"{self.config_name}.json"
        if not load_path.exists():
            logger.warning(f"群组 {self.group} 的配置文件不存在，已自动生成")
            self.save_group()
            return
        
        try :
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rd = data["rd"]
                self.prt = data["prt"]
                self.mod = data["mod"]
                self.tkc = data["tkc"]
                self.mess = data["memory"]
                self.cooldown = data["cooldown"]
                self.max_token = data["max_token"]
                self.max_recall = data["max_recall"]
                self.current_personality = data["default_personality"]
            return "✅ 加载成功"
        except Exception as e:
            logger.exception(f"未知保存错误{e}")
            return "⚠️ 系统异常，请联系管理员"

class Information:
    """信息类，维护一些项目信息"""
    @property
    def full_version(self) -> str:
        """生成完整版本号"""
        return f"{MAJOR_VERSION}.{MINOR_VERSION}.{PATCH_VERSION}-{VERSION_SUFFIX}"

    @property
    def build_date(self) -> str:
        """获取构建日期"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")