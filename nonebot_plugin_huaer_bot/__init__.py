# coding: utf-8
# Copyright (c) 2025 HuaEr DevGroup. Licensed under MIT.
import re
from pathlib import Path
from asyncio import to_thread, gather

from nonebot import get_driver
from nonebot.params import CommandArg
from .config import Information, Tools
from nonebot.permission import SUPERUSER
from nonebot.adapters import Message, Event
from .group import GroupManagement, GroupManager
from nonebot import on_command, get_driver, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="HuaEr聊天bot",
    description="基于SiliconFlow API的Nonebot2的多组群聊天插件，支持人格设定、markdown显示、联网搜索、检索增强生成（RAG）等功能",
    usage="多组群聊天插件，支持markdown显示、联网搜索、检索增强生成（RAG）等等功能",
    type="application",
    homepage="https://github.com/inkink365/nonebot-plugin-huaer-bot",
    supported_adapters={ "~onebot.v11" }
)

# 注册事件响应器
# 对话事件响应器
txt = on_command("对话")
markdown_cmd = on_command("MD")
recall_memory = on_command("撤回")
switch_rag_cmd = on_command("RAGS", permission=SUPERUSER)
switch_ssin_cmd = on_command("SSIN", permission=SUPERUSER)
switch_allin_cmd = on_command("ALLIN", permission=SUPERUSER)
switch_thinking_cmd = on_command("思考", permission=SUPERUSER)
model_prompt_cmd = on_command("模型列表", permission=SUPERUSER)
model_setting_cmd = on_command("模型设置", permission=SUPERUSER)
switch_search_cmd = on_command("联网搜索", permission=SUPERUSER)
add_memory = on_command("记忆添加", permission=SUPERUSER)
print_memory = on_command("记忆输出", permission=SUPERUSER)
clean_memory = on_command("记忆清除", permission=SUPERUSER)
insert_rag = on_command("RAG添加", permission=SUPERUSER)
delete_rag = on_command("RAG删除", permission=SUPERUSER)
clear_rag = on_command("RAG清空", permission=SUPERUSER)
save_rag = on_command("RAG保存", permission=SUPERUSER)

# 人格管理事件响应器
set_persona = on_command("人格设置", permission=SUPERUSER)
save_persona = on_command("人格储存", permission=SUPERUSER)
list_persona = on_command("人格列表", permission=SUPERUSER)
load_persona = on_command("人格读取", permission=SUPERUSER)

# 白名单管理事件响应器
group_whitelist = on_command("群聊白名单", permission=SUPERUSER)
user_whitelist = on_command("用户白名单", permission=SUPERUSER)

# 组管理器事件响应器
save_cmd = on_command("保存配置", permission=SUPERUSER)
load_cmd = on_command("加载配置", permission=SUPERUSER)
reset_cmd = on_command("重置配置", permission=SUPERUSER)

# 文档命令响应器
user_doc_cmd = on_command("readme")
dev_doc_cmd = on_command("功能列表", permission=SUPERUSER)

# 初始化类总控函数响应器
open_group = on_command("选择群聊", permission=SUPERUSER)
close_group = on_command("退出群聊", permission=SUPERUSER)
# 用于操作 (class)initialize -> (variable)ID_symbol ，详见ID_symbol

class initialize:
    """初始化类，整合所有命令并绑定于相应的响应器（单例模式）"""
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # 初始化组管理器
            self.groupmanager = GroupManager()

            # 初始化信息类
            self.information = Information()

            # 管理员控制功能核心机制：ID_symbol，当其不为None时，所有管理员的指令将全部作用于其值所对应的组管理器。
            self.ID_symbol = None

            # 绑定处理器
            txt.handle()(self.handle_chat)
            markdown_cmd.handle()(self.handle_markdown)
            switch_rag_cmd.handle()(self.handle_switch_rag)
            switch_ssin_cmd.handle()(self.handle_switch_ssin)
            switch_allin_cmd.handle()(self.handle_switch_allin)
            model_prompt_cmd.handle()(self.handle_model_prompt)
            switch_search_cmd.handle()(self.handle_switch_search)
            switch_thinking_cmd.handle()(self.handle_switch_thinking)
            model_setting_cmd.handle()(self.handle_model_setting)
            recall_memory.handle()(self.handle_recall_memory)
            print_memory.handle()(self.handle_print_memory)
            clean_memory.handle()(self.handle_clean_memory)
            add_memory.handle()(self.handle_add_memory)
            insert_rag.handle()(self.handle_insert_rag)
            delete_rag.handle()(self.handle_delete_rag)
            clear_rag.handle()(self.handle_clear_rag)
            save_rag.handle()(self.handle_save_rag)
            
            save_persona.handle()(self.handle_save_persona)
            list_persona.handle()(self.handle_list_persona)
            load_persona.handle()(self.handle_load_persona)
            set_persona.handle()(self.handle_set_personality)

            user_whitelist.handle()(self.handle_user_whitelist)
            group_whitelist.handle()(self.handle_group_whitelist)
            
            save_cmd.handle()(self.save_group)
            load_cmd.handle()(self.load_group)
            reset_cmd.handle()(self.reset_group)

            dev_doc_cmd.handle()(self.show_dev_doc)
            user_doc_cmd.handle()(self.show_user_doc)

            close_group.handle()(self.exit_group)
            open_group.handle()(self.choose_group)

            self._initialized = True

    def _get_group(self, group_id: str) -> GroupManagement:
        return self.groupmanager.get_group(group_id)
    
    def _is_superuser(self, user: str) -> bool:
        return user in map(str, get_driver().config.superusers)

    def _get_info(self, event: Event) -> str:
        "获取事件对应的组编号"
        if (self._is_superuser(event.get_user_id()) and self.ID_symbol is not None):
            return self.ID_symbol
        elif isinstance(event, GroupMessageEvent):
            return str(event.group_id)
        elif isinstance(event, PrivateMessageEvent):
            return self.groupmanager.private_group_id

    def _check_access(self, event: Event) -> bool:
        "依据白名单鉴权"
        user_id = event.get_user_id()
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = str(event.group_id)
            if self._is_superuser(user_id) and group_id in self.groupmanager.whitelist_manager.groups :
                return True
            else :
                return self.groupmanager.whitelist_manager._check_access(user_id, group_id, True)
        if isinstance(event, PrivateMessageEvent):
            if self._is_superuser(user_id) :
                return True
            else :
                return self.groupmanager.whitelist_manager._check_access(user_id, group_id, False)
            
    # 对话命令
    async def handle_chat(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return

        response = await self._get_group(self._get_info(event)).chat_handler.handle_chat(event, args, self._is_superuser(event.get_user_id()))
        await txt.finish(response)

    async def handle_markdown(self, event: Event):
        if not self._check_access(event):
            return
        
        response = await self._get_group(self._get_info(event)).chat_handler.handle_markdown()
        await markdown_cmd.finish(response)

    async def handle_model_prompt(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group("public").chat_handler.handle_model_prompt()
        await model_prompt_cmd.finish(response)
    
    async def handle_model_setting(self, event: Event, key: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.handle_model_setting(key)
        await model_setting_cmd.finish(response)

    async def handle_switch_thinking(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.switch_thinking()
        await switch_thinking_cmd.finish(response)

    async def handle_switch_rag(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.switch_rag()
        await switch_rag_cmd.finish(response)

    async def handle_switch_ssin(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.switch_ssin()
        await switch_ssin_cmd.finish(response)

    async def handle_switch_allin(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.switch_allin()
        await switch_allin_cmd.finish(response)


    async def handle_switch_search(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.switch_search()
        await switch_search_cmd.finish(response)

    async def handle_recall_memory(self, event: Event) -> str:
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.handle_recall_memory(self._is_superuser(event.get_user_id()))
        await recall_memory.finish(response)

    async def handle_print_memory(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.handle_print_memory()
        await print_memory.finish(response)

    async def handle_clean_memory(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.handle_clean_memory()
        await clean_memory.finish(response)

    async def handle_add_memory(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).chat_handler.handle_add_memory(args)
        await add_memory.finish(response)

    async def handle_delete_rag(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = await self._get_group(self._get_info(event)).chat_handler.handle_delete_index(args)
        await delete_rag.finish(response)

    async def handle_insert_rag(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        await insert_rag.send("开始插入，请稍等...")
        response = await self._get_group(self._get_info(event)).chat_handler.handle_insert_index(args)
        await insert_rag.finish(response)

    async def handle_clear_rag(self, event: Event):
        if not self._check_access(event):
            return
        
        response = await self._get_group(self._get_info(event)).chat_handler.handle_clear_index()
        await clear_rag.finish(response)

    async def handle_save_rag(self, event: Event):
        if not self._check_access(event):
            return
        
        response = await self._get_group(self._get_info(event)).chat_handler.handle_save_index()
        await save_rag.finish(response)

    # 人格管理命令
    async def handle_list_persona(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).personality_manager.handle_list_persona()
        await list_persona.finish(response)

    async def handle_save_persona(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = await self._get_group(self._get_info(event)).personality_manager.handle_save_persona(args)
        await save_persona.finish(response)

    async def handle_load_persona(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).personality_manager.handle_load_persona(args)
        await load_persona.finish(response)

    async def handle_set_personality(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = await self._get_group(self._get_info(event)).personality_manager.handle_set_personality(args)
        await set_persona.finish(response)

    # 白名单管理命令
    async def handle_user_whitelist(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = await self.groupmanager.whitelist_manager.handle_user_whitelist(args)
        await user_whitelist.finish(response)

    async def handle_group_whitelist(self, event: Event, args: Message = CommandArg()):
        if not self._check_access(event):
            return
        
        response = await self.groupmanager.whitelist_manager.handle_group_whitelist(args)
        info = Tools._parse_args(args.extract_plain_text().split(), "增加", "删除")
        if info is not None:
            if info[1] == "增加" :
                await self.groupmanager.add_group(info[0])
            elif info[1] == "删除" :
                await self.groupmanager.remove_group(info[0])
        await group_whitelist.finish(response)

    # 组管理器命令
    async def save_group(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).save_group()
        await save_cmd.finish(response)

    async def load_group(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).load_group()
        await load_cmd.finish(response)

    async def reset_group(self, event: Event):
        if not self._check_access(event):
            return
        
        response = await self.groupmanager.reset_group(self._get_info(event))
        await reset_cmd.finish(response)

    # 文档命令
    async def show_dev_doc(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).show_dev_doc()
        await dev_doc_cmd.finish(response)

    async def show_user_doc(self, event: Event):
        if not self._check_access(event):
            return
        
        response = self._get_group(self._get_info(event)).show_user_doc()
        await user_doc_cmd.finish(response)

    # 管理员命令
    async def choose_group(self, args: Message = CommandArg()):
        """控制群聊"""
        arg_text = args.extract_plain_text().strip()
        if match := re.search(r'\d+|public|private', arg_text):
            extracted_group = match.group()
            if extracted_group in self.groupmanager.groups :
                self.ID_symbol = extracted_group
                logger.info(f"当前组群：{self.ID_symbol}")
                await open_group.finish("✅ 选定成功")
            else :
                logger.warning("组群号无效")
                await open_group.finish("⚠️ 组群号无效")
        else :
            logger.warning("未检测到组群号")
            await open_group.finish("⚠️ 请输入组群号")

    async def exit_group(self):
        """解控群聊"""
        if self.ID_symbol is not None :
            self.ID_symbol = None
            await close_group.finish(f"✅ 解控成功")
        else :
            await close_group.finish(f"⚠️ 当前没有选中的组群")

'''except FinishedException:
    pass  # 忽略NoneBot的流程控制异常(如果调试中有异常，需要的话)'''

driver = get_driver()

container = None

@driver.on_startup
async def init():
    global container 
    container = initialize()
    version_info = (
        f"\n{'='*40}\n"
        f" HuaEr bot Initialized\n"
        f" Version: {container.information.full_version}\n"
        f" Build Date: {container.information.build_date}\n"
        f"{'='*40}\n"
    )
    logger.info(version_info)

@driver.on_shutdown
async def auto_save():
    logger.info("检测到终止指令，自动保存中...")

    tasks = []
    for group in container.groupmanager.groups.values():
        tasks.append(to_thread(group.save_group))
        tasks.append(group.chat_handler.handle_save_index())

    results = await gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"保存任务失败: {result}")

    logger.info("保存完毕！")

# ===================================================
#                   项目落款 / Project Footer
# ===================================================
# 版本号 / Version: 2.2.1 (stable)
# 最新修改日期 / Last Modified: 2025年8月11日 / August 11, 2025
# 开发团队 / Development Team: 华尔开发组 / Huaer Development Group
# ---------------------------------------------------
# 版权声明 / Copyright: © 2025 华尔开发组 
#                  © 2025 Huaer DevGroup. 
# ---------------------------------------------------
# 开源协议 / License: MIT
# 代码仓库 / Repository: github.com/inkink365/nonebot-plugin-huaer-bot
# 技术文档 / Documentation: github.com/inkink365/nonebot-plugin-huaer-bot/wiki
# ---------------------------------------------------
# 联系方式 / Contact:
#   - 电子邮件 / Email: HuaEr_DevGroup@outlook.com
#   - Q群 / Forum: 1006249997
# ===================================================