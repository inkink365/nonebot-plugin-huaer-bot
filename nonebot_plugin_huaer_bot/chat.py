import re
import time
import httpx
from json import JSONDecodeError
from typing import List, Optional

from nonebot import logger
from nonebot import require
from nonebot.adapters import Message, Event
from nonebot.adapters.onebot.v11 import MessageSegment
from .config import ConfigManager, ChatConfig, API_URL, HEADERS, PRE_MOD, PUBLIC_DIR, MODELS

require("nonebot_plugin_htmlrender")

from nonebot_plugin_htmlrender import md_to_pic

class ChatHandler:
    '''对话响应类'''
    def __init__(self, 
                 chat_config: ChatConfig):
        self.cooldown_until = 0 #辅助特殊模型冷却功能
        self.recall_times = 0 #辅助撤回功能

        self.cc = chat_config

    # 辅助函数
    def _manage_memory(self):
        """管理记忆上下文"""
        while len(self.cc.mess) > self.cc.rd:
            del self.cc.mess[0]
    
    def _chat_info(self) -> None:
        """生成格式化对话记录"""
        dialogue_log = "\n".join(
            [f"[{msg['role'].upper()}] {msg['content']}" 
            for msg in self.cc.mess[-(self.cc.rd):]]
        )
        logger.info(f"\n{'#'*40}\n当前人格:\n{self.cc.current_personality}\n\n对话记录:\n{dialogue_log}\n{'#'*40}\n")

    async def _check_api_limit(self, superuser: bool) -> bool:
        """检查API调用限制"""
        if self.cc.mod not in PRE_MOD:
            return False,None
        elif time.time() < self.cooldown_until and not superuser:
            remaining = self.cooldown_until-time.time()
            return True,f"特殊模型冷却中，剩余时间：{remaining:.0f}秒"
        return False,None

    async def _get_user_info(self, event: Event) -> dict:
        """安全获取用户信息"""
        name = getattr(event.sender, "nickname", "未知用户")
        # 过滤控制字符并截断过长名称
        clean_name = re.sub(r'[\x00-\x1F\x7F]', '', name)[:20]  
        return {
            "name": clean_name,
            "id": str(getattr(event, "user_id", ""))
        }

    async def _call_api(self, messages: List[dict]) -> Optional[dict]:
        """执行API请求"""
        payload = {
            "model": MODELS[self.cc.mod],
            "messages": [{
                "role": "system",
                "content": self.cc.current_personality
            }] + messages,
            "max_tokens": self.cc.max_token,
        }
        
        try:
            # 创建异步客户端实例
            async with httpx.AsyncClient() as client:
                # 发送异步POST请求
                response = await client.post(
                    API_URL,
                    json=payload,
                    headers=HEADERS,
                    timeout=60
                )
                # 检查HTTP状态码
                response.raise_for_status()
                # 返回JSON响应
                return response.json()
        except Exception as e:
            logger.error(f"API请求失败: {e}")
            return None
        
    async def _process_response(self, data: dict) -> dict:
        """处理API响应"""
        result = {
            "thinking": "### 深度思考:\n",
            "response": "",
            "assistant_msg": None
        }
        
        try:
            result["thinking"] += data['choices'][0]['message']['reasoning_content']
        except KeyError:
            result["thinking"] += "\n此模型无思考功能\n"
        
        assistant_content = data['choices'][0]['message']['content'].strip()
        result["response"] = assistant_content
        result["assistant_msg"] = {
            "role": "assistant",
            "content": assistant_content
        }
        
        if self.cc.tkc:
            result["response_message"] = result["thinking"] + "\n### 谈话:\n" + result["response"]
        else:
            result["response_message"] = result["response"]
        
        return result

    # 对话命令
    async def disable_thinking(self) -> str:
        self.cc.tkc = False
        return "✅ 已隐藏思考过程"

    async def enable_thinking(self) -> str:
        self.cc.tkc = True
        return "✅ 已显示思考过程"
    
    async def handle_model_prompt(self) -> str:
        """生成模型选择提示"""
        return "📂 可用模型列表：\n" + "\n".join(
            f"{i+1}.{model}" for i, model in enumerate(MODELS)
        )
        
    async def handle_markdown(self) -> MessageSegment:
        """处理Markdown转换"""
        try:
            last_content = self.cc.mess[-1]['content']
            img = await md_to_pic(last_content)
            return MessageSegment.image(img)
        except Exception as e:
            logger.error(f"Markdown转换失败: {e}")
            return MessageSegment.text("❌ 渲染失败,可能是因为没有对话记录。")

    async def handle_recall(self, superuser: bool) -> str:
        """处理撤回请求"""
        if len(self.cc.mess) > 0 and (superuser or self.recall_times < self.cc.max_recall/2):
            self.cc.mess = self.cc.mess[:-2]
            self.recall_times += 1
            if self.cc.prt : self._chat_info()#debug
            return "✅ 已撤回上轮对话"
        elif len(self.cc.mess) >= 2:
            return "⚠️ 撤回数量达上限"
        else:
            return "⚠️ 无对话记录"

    async def handle_model_setting(self, key: Message) -> str:
        """处理模型设置"""
        if req := key.extract_plain_text():
            if match := re.search(r'\d+', req):
                selected = int(match.group()) - 1
                if 0 <= selected < len(MODELS):
                    self.cc.mod = selected
                    return "✅ 模型修改成功"
            return "📛 请输入有效序号！"
        else:
            return "⚠️ 请输入文本"

    async def handle_chat(self, event: Event, args: Message, superuser: bool) -> str:
        """处理对话请求"""

        if self.cc.prt : logger.info(f"对话事件启动, 群:{self.cc.group}, 模型:{MODELS[self.cc.mod]}")
        
        if not (user_input := args.extract_plain_text()):
            return "📛 请输入有效内容"
        
        # API调用限制检查
        boolean, string = await self._check_api_limit(superuser)
        if boolean : return string
        
        # 记忆管理
        self._manage_memory()
        
        # 构建对话记录
        user_info = await self._get_user_info(event)
        self.cc.mess.append({
            "role": "user",
            "content": f"用户[{user_info['name']}]: {user_input}"#群聊可获取用户名称，私聊加为好友后方可获取。
        })
        
        # 执行API请求
        response = await self._call_api(self.cc.mess)
        if not response:
            self.cc.mess.pop()
            return "⚠️ 服务暂不可用"
        
        # 处理响应
        result = await self._process_response(response)
        self.cc.mess.append(result["assistant_msg"])

        if self.recall_times > 0: self.recall_times -= 1 #增加可撤回次数

        if self.cc.prt : self._chat_info()
        
        # 更新API调用时间
        if not superuser and self.cc.mod in PRE_MOD:  # 特殊模型
            self.cooldown_until = time.time() + self.cc.cooldown
        
        return result["response_message"]


class PersonalityManager:
    '''人格管理类，保存人格会附带当前记忆'''
    def __init__(self,
                 chat_config: ChatConfig):
        
        self.cc = chat_config 

    # 辅助函数
    def _set_personality(self, new_personality: str):
        """设置新人格并重置记忆"""
        if len(new_personality) > self.cc.max_token:
            #最大人设长度不超过maxtoken
            raise ValueError("人格描述过长")
        self.cc.current_personality = new_personality
        self.cc.mess.clear()
        logger.info(f"人格已更新: {new_personality}")

    def _save_personality(self, name: str, opt: bool):
        """opt = True，存储于私有文件夹；opt = False，存储于公有"""
        save_path = self.cc.file / f"(p){name}.json" if opt else PUBLIC_DIR / f"(p){name}.json"
        if save_path.exists():
            raise FileExistsError("该人格名称已存在")
        data = {
            "personality": self.cc.current_personality,
            "memory": self.cc.mess
        }
        ConfigManager.save_json(data, save_path)

    def _load_personality(self, name: str, opt: bool):
        """opt = True，读取于私有文件夹；opt = False，读取于公有"""
        file_path_private = self.cc.file / f"(p){name}.json"
        file_path_public = PUBLIC_DIR / f"(p){name}.json"
        file_path = file_path_private if opt else file_path_public
        if not file_path.exists():
            raise FileNotFoundError
        
        with open(file_path, "r") as f:
            raw_data = f.read()
            if not raw_data.strip():
                raise ValueError("空文件内容")
        data = ConfigManager.load_json(file_path, {})
        self.cc.current_personality = data.get("personality", "")
        self.cc.mess = data.get("memory", [])

    def _parse_args(self, args: Message) -> Optional[tuple]:
        '''人格参数解析器'''
        arg = args.extract_plain_text().split()

        if len(arg) != 2:
            return None
            
        # 智能识别参数位置
        place = next((a for a in arg if a in ("公共", "私有")), None)
        id = next((g for g in arg if g != place), None)
        
        return (id, place) if id and place else None

    # 人格命令
    async def handle_set_personality(self, args: Message) -> str:
        '''人格设置命令'''
        if new_persona := args.extract_plain_text():
            try:
                self._set_personality(new_persona)
                return f"✅ 人格已更新为：{new_persona}"
            except ValueError as e:  # 专门捕获输入验证异常
                logger.error(f"人格验证失败：{str(e)}")
                return f"❌ 人格设置失败：{str(e)}"
            except Exception as e:
                logger.exception("未知错误：")
                return "⚠️ 系统异常，请联系管理员"
        else:
            return "📝 请输入人格描述文本"

    async def handle_save_persona(self, args: Message) -> str:
        '''人格储存命令'''
        try:
            parsed = self._parse_args(args)
            if not parsed:
                return "⚠️ 格式错误，正确格式：/人格储存 [人格名称] [公共/私有]"
            
            name, place = parsed
            if '/' in name or '\\' in name:
                raise ValueError("名称包含非法字符")
                
            self._save_personality(name, True if place == "私有" else False)
            return f"💾 人格 [{name}] 保存成功"
            
        except ValueError as e:
            logger.warning(f"人格储存参数错误：{str(e)}")
            return f"❌ 保存失败：{str(e)}"
        except FileExistsError:
            logger.warning(f"该人格名称已存在")
            return "⚠️ 保存失败：该人格名称已存在"
        except JSONDecodeError:
            logger.error("人格文件格式错误")
            return "❌ 保存失败：文件格式异常"
        except IOError as e:
            logger.error(f"IO错误：{str(e)}")
            return "❌ 保存失败：文件系统错误"
        except Exception as e:
            logger.exception("未知保存错误")
            return "⚠️ 系统异常，请联系管理员"

    async def handle_load_persona(self, args: Message) -> str:
        '''人格读取命令'''
        try:
            parsed = self._parse_args(args)
            if not parsed:
                return "⚠️ 格式错误，正确格式：/人格读取 [人格名称] [公共/私有]"

            name, place = parsed
            if '/' in name or '\\' in name:
                raise ValueError("⚠️ 名称包含非法字符")
                
            self._load_personality(name, True if place == "私有" else False)
            return f"🔄 已切换到人格 [{name}]"
            
        except FileNotFoundError:
            logger.error("人格不存在")
            return "❌ 人格不存在"
        except JSONDecodeError:
            logger.error("人格文件损坏")
            return "❌ 加载失败：文件内容损坏"
        except KeyError as e:
            logger.error(f"数据字段缺失：{str(e)}")
            return "❌ 加载失败：人格数据不完整"
        except Exception as e:
            logger.exception("未知加载错误")
            return "⚠️ 系统异常，请联系管理员"
        
    async def handle_list_persona(self) -> str:
        '''人格列出命令'''
        # 获取存储目录下所有json文件
        persona_files_private = [f.stem[3:] for f in self.cc.file.glob("(p)*.json") if f.is_file()]
        persona_files_public = [f.stem[3:] for f in PUBLIC_DIR.glob("(p)*.json") if f.is_file()]
        
        # 构建提示信息
        if not persona_files_private and not persona_files_public:
            return "⚠️ 无可用人格配置"

        persona_list = "\n".join([f"· {name}" for name in persona_files_private])
        persona_list_public = "\n".join([f"· {name}" for name in persona_files_public])
        msg = (
            "📂 可用人格列表：\n"
            f"{persona_list if persona_list else '空'}\n\n"
            "来自public：\n"
            f"{persona_list_public if persona_list_public else '空'}\n\n"
            "使用人格读取命令以切换人格。"
        )
        
        return msg
        
    async def handle_clean_memory(self) -> None:
        "记忆清除命令"
        if not self.cc.mess:
            return "⚠️ 记忆体为空"
        else:
            self.cc.mess.clear()
            return "✅ 清除成功"