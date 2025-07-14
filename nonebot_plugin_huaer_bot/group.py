import re
from typing import Dict, List, Optional

from nonebot import logger
from .doc import Documentation
from nonebot.adapters import Message
from .chat import ChatHandler, PersonalityManager
from .config import ConfigManager, ChatConfig, GROUP_WHITELIST_FILE, USER_WHITELIST_FILE, WHITELIST_MODE

class WhitelistManager:
    '''白名单管理类'''
    def __init__(self):
        self.groups: List[str] = ConfigManager.load_json(
            GROUP_WHITELIST_FILE, []
        )
        self.users: List[str] = ConfigManager.load_json(
            USER_WHITELIST_FILE, []
        )

    def _update_group(self, group_id: str, opt: bool):
        '''群聊白名单更新，opt = true 为增加，opt = False 为删除'''
        original_groups = set(self.groups.copy())
        
        if opt:
            if group_id in self.groups:
                raise ValueError(f"群聊 {group_id} 已在白名单中")
            self.groups.append(group_id)
        else:
            if group_id not in self.groups:
                raise ValueError(f"群聊 {group_id} 不在白名单中")
            self.groups.remove(group_id)
        
        # 仅在发生变化时保存
        if set(self.groups) != original_groups:
            ConfigManager.save_json(self.groups, GROUP_WHITELIST_FILE)

    def _update_user(self, user_id: str, opt: bool):
        '''用户白名单更新，opt = true 为增加，opt = False 为删除'''
        original_users = set(self.users.copy())
        
        if opt:
            if user_id in self.users:
                raise ValueError(f"用户 {user_id} 已在白名单中")
            self.users.append(user_id)
        else:
            if user_id not in self.users:
                raise ValueError(f"用户 {user_id} 不在白名单中")
            self.users.remove(user_id)

        # 仅在发生变化时保存
        if set(self.users) != original_users:
            ConfigManager.save_json(self.users, USER_WHITELIST_FILE)

    def _validate_group_id(self, group_id: str) -> bool:
        """验证群号格式"""
        return re.fullmatch(r"\d{6,10}", group_id) is not None

    def _validate_user_id(self, user_id: str) -> bool:
        """验证用户ID格式（兼容5-11位QQ号）"""
        return re.fullmatch(r"\d{5,11}", user_id) is not None
    
    def _parse_args(self, args: Message) -> Optional[tuple]:
        '''白名单参数解析器'''
        arg = args.extract_plain_text().split()

        if len(arg) != 2:
            return None
            
        # 智能识别参数位置
        action = next((a for a in arg if a in ("增加", "删除")), None)
        id = next((g for g in arg if g != action), None)
        
        return (id, action) if id and action else None
    
    def _check_access(self, user: str, group: str, type: bool) -> bool:
        '''鉴权函数，type为true表示群消息事件，false表示私聊事件'''
        # 群聊检查
        if type:
            if WHITELIST_MODE == 0 : 
                return group in self.groups
            elif WHITELIST_MODE == 1:
                return (group in self.groups and user in self.users)

        # 私聊检查
        else:
            if WHITELIST_MODE == 0 : 
                return user in self.users
            elif WHITELIST_MODE == 1:
                return user in self.users
            #为什么私聊鉴权没有用到group还是要导入进来？还有config这么多冗余的设计是怎么回事？当然是为了方便后续拓展 <del>真的不是因为懒得改ﾚ(ﾟ∀ﾟ;)ﾍ=З=З=З</del>

        logger.error("白名单模式错误")
        return False

    # 白名单命令
    # 群聊白名单命令
    async def handle_group_whitelist(self, args: Message) -> str:
        '''群聊白名单控制命令'''
        try:
            parsed = self._parse_args(args)
            if not parsed:
                return "⚠️ 格式错误，正确格式：/群聊白名单 [群号] [增加/删除]"

            group_id, action = parsed
            if not self._validate_group_id(group_id):######
                return "⚠️ 群号无效"
            
            # 执行更新操作
            self._update_group(group_id, True if action == "增加" else False)
            
            return f"✅ 群聊 {group_id} {action}成功"
            
        except ValueError as e:
            logger.warning(f"参数错误：{str(e)}")
            return f"❌ 操作失败：{str(e)}"
        except Exception as e:
            logger.exception("未知错误：")
            return "⚠️ 系统异常，请联系管理员"

    # 用户白名单命令
    async def handle_user_whitelist(self, args: Message) -> str:
        '''用户白名单控制命令'''
        try:
            parsed = self._parse_args(args)
            if not parsed:
                return "⚠️ 格式错误，正确格式：/用户白名单 [QQ号] [增加/删除]"

            user_id, action = parsed
            if not self._validate_group_id(user_id):
                return "⚠️ QQ号无效"
            
            # 执行更新操作
            self._update_user(user_id, True if action == "增加" else False)
            
            # 添加操作反馈增强
            return f"✅ 用户 {user_id} {action}成功"
            
        except ValueError as e:
            logger.warning(f"参数错误：{str(e)}")
            return f"❌ 操作失败：{str(e)}"
        except Exception as e:
            logger.exception("未知错误：")
            return "⚠️ 系统异常，请联系管理员"

class GroupManagement:
    '''组管理器类'''
    def __init__(self, ID):
        self.chat_config = ChatConfig(ID)
        self.chat_config.file.mkdir(exist_ok=True)

        self.chat_handler = ChatHandler(chat_config=self.chat_config)
        self.documentation = Documentation(chat_config=self.chat_config)
        self.personality_manager = PersonalityManager(chat_config=self.chat_config)

        self._initialize(ID)

    def _initialize(self, ID: int):
        save_path = self.chat_config.file / f"{self.chat_config.config_name}.json"
        if save_path.exists() :
            self.chat_config.load_group()
        else :
            self.chat_config.save_group()
            if ID == 0 :
                self.personality_manager._save_personality("华尔", False)
            elif ID == 1 :
                self.chat_config.rd = 0 # 私聊记忆锁，容量默认为0

    async def save_group(self):
        """保存配置"""
        return self.chat_config.save_group()

    async def load_group(self):
        """加载配置"""
        return self.chat_config.load_group()
    
    async def show_dev_doc(self):
        """开发者文档"""
        return self.documentation.show_dev_doc()

    async def show_user_doc(self):
        """用户文档"""
        return self.documentation.show_user_doc()

class GroupManager:
    '''组管理器容器类（单例模式）'''
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.private_group_id = "private"
            self.public_group_id = "public"
            self.groups: Dict[str, GroupManagement] = {}
            self.whitelist_manager = WhitelistManager()
            
            self.add_private_group()
            self.add_public_group()

            for group in self.whitelist_manager.groups :
                self.groups[group] = GroupManagement(int(group))
                logger.info(f"群{group}实例已初始化")
            
            logger.info(f"群组管理器初始化完成，共加载 {len(self.groups)} 个实例")
            self._initialized = True

    def _parse_args(self, args: List[str]) -> Optional[tuple]:
        '''组管理器参数解析器'''
        if len(args) != 2:
            return None
            
        action = next((a for a in args if a in ("增加", "删除")), None)
        id = next((g for g in args if g), None)
        
        return (id, action) if id and action else None

    def add_public_group(self):
        """初始化公共实例"""
        if self.public_group_id not in self.groups:
            self.groups[self.public_group_id] = GroupManagement(0)
            logger.info("公有实例已初始化")

    def add_private_group(self):
        """添加私聊实例"""
        if self.private_group_id not in self.groups:
            self.groups[self.private_group_id] = GroupManagement(1)
            logger.info("私聊实例已初始化")

    def get_group(self, group_id: str) -> GroupManagement:
        """安全获取实例"""
        return self.groups.get(group_id)
    
    async def reset_group(self, group_id: str) -> str:
        """重置群组配置"""
        try :
            self.get_group(group_id).chat_config = self.get_group(self.public_group_id).chat_config
            return "✅ 重置完成"
        except Exception as e:
            logger.exception("未知错误：")
            return f"❌ 重置失败，{str(e)}"

    async def add_group(self, group_id: str):
        """创建群组实例"""
        if group_id in self.groups:
            logger.warning(f"群组 {group_id} 已存在，跳过创建")
            return
            
        # 创建群组实例
        self.groups[group_id] = GroupManagement(int(group_id))
            
        logger.info(f"群组 {group_id} 实例已创建")

    async def remove_group(self, group_id: str):
        """移除群组实例，但不会移除已生成的配置文件"""
        if group_id in self.groups:
            # 执行清理操作
            del self.groups[group_id]
            logger.info(f"群组 {group_id} 实例已移除")
        else:
            logger.warning(f"尝试移除不存在的群组：{group_id}")

