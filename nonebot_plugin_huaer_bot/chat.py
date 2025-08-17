import re
import json
import time
import httpx
from pathlib import Path
from json import JSONDecodeError
from tavily import AsyncTavilyClient
from asyncio import to_thread, create_task, gather
from typing import Optional, Dict, Any, List, Tuple

from nonebot import logger
from nonebot import require
from nonebot.adapters import Message, Event
from nonebot.adapters.onebot.v11 import MessageSegment
from .config import ConfigManager, ChatConfig, Tools, FUNC, API_URL, SAPI_KEY, API_KEY, PRE_MOD, PUBLIC_DIR, MODELS, EMB_URL, SAPI_URL

require("nonebot_plugin_htmlrender")

from nonebot_plugin_htmlrender import md_to_pic

class ChatHandler:
    '''对话响应类'''
    def __init__(self, 
                 chat_config: ChatConfig):
        self.cc = chat_config

        self.cooldown_until = 0 #辅助特殊模型冷却功能
        self.recall_times = 0 #辅助撤回功能
        self.tavily_client = AsyncTavilyClient(SAPI_KEY)
        self.http_client = httpx.AsyncClient() # 创建客户端实例
        
        self.role_map = {"user": "用户", "assistant": "助手", "system": "系统"}
        # function calling专用prompt
        self.func_call = {"role": "system", "content": "你是专门负责处理function calling的助手,\
                          请根据给到的消息和tools的描述按需返回恰当的函数参数(不需要则留空)"}
        self.tools_map = { # function calling tool函数名称与信息映射
            "_llm_tool_ddg_search": self._llm_tool_creator(
                    "_llm_tool_ddg_search", "联网搜索功能", 
                    {"queries":("List[str]", "需要查询的问题,一般仅一条"),
                    "max_results":("int", "返回网页数量(应为1~10,一般小于等于5)")}
                ),
            "_llm_tool_rag_retrieve": self._llm_tool_creator(
                    "_llm_tool_rag_retrieve", "信息检索功能，当一段信息可能在前文被提及或与用户特征有关时可启用", 
                    {"queries":("List[str]", "需要检索的内容,分块,请挑重点且语言精炼"),
                    "num":("int", "每个问题返回的文档量,多跳检索(应为1~5,一般小于等于3)")}
                ),
            "_llm_tool_rag_index": self._llm_tool_creator(
                    "_llm_tool_rag_index", "信息记录功能,当一段信息可能在后文被用到时可启用;但应作为长期记忆,不必当做历史记录使用；\
                    始终通过'用户[用户名(可能为特殊字符)]:'或'助手:'等字段区分不同角色；\
                    并提取如下格式信息:'用户[XXX]/助手 认为/希望/许诺/说/让用户[B]记住/...(诸如此类的动词) 某事'", #加限定，减少幻觉
                    {"contents":("List[str]", "需要记录的内容,分块,请挑重点且语言精炼")}
                ),
        }

    # 辅助函数
    def _manage_memory(self):
        """管理记忆上下文"""
        while len(self.cc.mess) > self.cc.rd:
            del self.cc.mess[0]

    def _create_mess(self, role: str, content: str, name: str = None, show_time: bool = False) -> dict:
        '''生成对话记录'''
        if not content : return None

        chara = self.role_map[role]
        if name : chara += f'[{name}]'
        chara += ": " 
        content = chara + content

        t = f"时间[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] " 
        if show_time:
            content = t+content
        return {"role": role,"content": content}
    
    def _chat_info(self) -> str:
        """读取对话记录"""
        dialogue_log = "\n".join(
            [f"[{msg['role'].upper()}]: \n {msg['content']}" 
            for msg in self.cc.mess[-(self.cc.rd):]]
        )
        return f"\n{'#'*40}\n当前人格:\n{self.cc.current_personality}\n\n对话记录:\n{dialogue_log}\n{'#'*40}\n"
    
    def _rag_info(self) -> str:
        """读取RAG索引内容"""
        dialogue_log = "\n".join([f"{text}\n" for text, hash_id in self.cc.hipporag])
        return f"\n{'#'*40}\n当前人格:\n{self.cc.current_personality}\n\nRAG记录:\n{dialogue_log}\n{'#'*40}\n"

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
    
    # 为Function Calling提供的工具函数
    def _llm_tool_creator(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Tuple[str, str]],
        **additional_info: Any 
    ) -> List[Dict[str, Any]]:
        '''
        构造单个function tool
            name: 函数名称（需与实际执行函数一致）
            description: 函数功能描述
            parameters: 函数参数定义（字典结构）
            additional_info: 其他函数相关说明
        '''
        for param,desc in parameters.items():
            parameters[param] = {"type": desc[0], "description": desc[1]}

        function_def = {
            'name': name,
            'description': description,
            'parameters': {
                'type': 'object',
                'properties': parameters,
                'required': list(parameters.keys())  # 自动设置所有参数为必需
            }
        }
        
        return [{'type': 'function','function': function_def}] + ([additional_info]  if additional_info else [])

    # 显然现在没有用到ddgs，由于链接不上的问题；但曾经设计时如此，故保留
    async def _llm_tool_ddg_search(self, queries: List[str], max_results: int = 5) -> Optional[List[Dict]]:
        '''联网搜索功能'''
        try:
            if not SAPI_KEY:
                logger.error(f"搜索失败: 请先设置api_key")
                return None
            
            if not queries: # 可能是llm刻意留空，故不报错
                return None
                    
            results = []
            if SAPI_URL:
                for q in queries:
                    payload = {
                                "messages": [{"role": "user","content": q}],
                                "resource_type_filter": [{"type": "web","top_k": max_results}],
                            }
                    headers = {'Authorization': SAPI_KEY}
                    response = await self.http_client.post(
                        SAPI_URL,
                        json=payload,
                        headers=headers,
                        timeout=60,
                    )
                    response.raise_for_status()
                    for rr in response.json()["references"]:  
                        results.append({
                            "title": rr["title"],
                            "content": rr["content"]
                        })
            else:
                responses = await gather(*(self.tavily_client.search(q, max_results=max_results) for q in queries), return_exceptions=True)
                for response in responses:
                    if isinstance(response, Exception):
                        logger.error(f"搜索失败: {response}")
                    else:
                        for rr in response["results"]:
                            results.append({
                                "title": rr["title"],
                                "content": rr["content"]
                            })
            if results: logger.debug(f"搜索成功，内容:\n{results}")
            return results
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise
        
    async def _llm_tool_rag_index(self, contents: List[str]):
        '''信息记录功能'''
        try:
            if not EMB_URL:
                logger.error(f"记录失败：请先设置嵌入模型接口")
                return

            if not contents:
                return
            
            logger.debug(f"RAG_index插入中: \n{contents}")
            
            await self.cc.hipporag.index(contents)

            logger.debug(f"RAG_index插入成功")
        except Exception as e:
            logger.error(f"index保存失败: {str(e)}")
            raise

    async def _llm_tool_rag_retrieve(self, queries: List[str], num: int = 2) -> Optional[List[str]]:
        '''信息检索功能'''
        try:
            if not queries:
                return None
            
            res = await self.cc.hipporag.retrieve(queries, num)
            
            retrieved_docs = [solution.docs for solution in res]
            
            if retrieved_docs: logger.debug(f"检索到的内容列表: {retrieved_docs}")
            return retrieved_docs
        except Exception as e:
            logger.warning(f"检索失败,可能是尚无相关信息: {str(e)}")
            raise

    async def _call_api(self, mess: List[dict], tools: Optional[List] = None) -> Optional[dict]:
        """执行API请求"""
        payload = {
            "model": FUNC if tools else MODELS[self.cc.mod],
            "messages": mess,
            "max_tokens": self.cc.max_token,
        }
        
        # 注入工具（如果有）
        if tools : payload["tools"] = tools

        logger.debug(payload)

        try:
            # 发送异步POST请求
            response = await self.http_client.post(
                API_URL,
                json=payload,
                headers={
                    "Authorization" : API_KEY,
                    "Content-Type" : "application/json"
                },
                timeout=60,
            )
            # 检查HTTP状态码
            response.raise_for_status()
            # 返回JSON响应
            return response.json()
        except Exception as e:
            logger.error(f"API请求失败: {e}")
            return None
        
    def _process_response(self, data: dict) -> dict:
        """处理API响应"""
        result = {
            "thinking": "### 深度思考:\n",
            "response": "",
            "assistant_msg": None,
            "tool_calls": [], 
        }
        
        try:
            message = data['choices'][0]['message']

             # 处理思考内容
            result["thinking"] += message.get('reasoning_content', "\n此模型无思考功能\n")

            # 处理常规回复内容
            result["response"] = message.get('content', '').strip()
            result["assistant_msg"] = self._create_mess("assistant", result["response"], None, True)

             # 处理函数调用
            if 'tool_calls' in message:
                result["tool_calls"] = []
                for call in message['tool_calls']:
                    func_info = call['function']
                    result["tool_calls"].append({
                        "id": call['id'],
                        "name": func_info['name'],
                        "arguments": func_info['arguments'],
                        "type": call.get('type', 'function')
                    })

            if self.cc.tkc:
                result["response_message"] = result["thinking"] + "\n### 谈话:\n" + result["response"]
            else:
                result["response_message"] = result["response"]
            
        except Exception as e:
            logger.error(f"响应处理失败: {str(e)}")
            result["error"] = f"响应解析错误: {str(e)}"
            result["response_message"] = "抱歉，响应解析出现错误"

        logger.debug(result)
        
        return result
    
    async def _handle_rag_indexing(self, cont: List[str]):
            """辅助信息记录后台运行"""
            if self.cc.search and self.cc.ssin:
                await self._llm_tool_rag_index(cont)
            if self.cc.allin:
                await self._llm_tool_rag_index([self.cc.mess[-2]["content"], self.cc.mess[-1]["content"]])
            else:
                results = await self._call_api(
                    [self.func_call, 
                    {"role": "user", "content": "消息: " + self.cc.mess[-2]["content"] + "\n   "},
                    {"role": "user", "content": "消息: " + self.cc.mess[-1]["content"]}
                    ], self.tools_map["_llm_tool_rag_index"])
                for info in self._process_response(results)["tool_calls"]:
                    params = json.loads(info["arguments"])
                    await getattr(self, "_llm_tool_rag_index")(**params)

    def switch_thinking(self) -> str:
        if self.cc.tkc :
            self.cc.tkc = False
            return "✅ 已隐藏思考过程"
        else :
            self.cc.tkc = True
            return "✅ 已显示思考过程"
        
    def switch_ssin(self) -> str:
        if self.cc.ssin :
            self.cc.ssin = False
            return "✅ 已关闭搜索存储"
        else :
            self.cc.ssin = True
            return "✅ 已开启搜索存储"
        
    def switch_allin(self) -> str:
        if self.cc.allin :
            self.cc.allin = False
            return "✅ 已关闭全记录"
        else :
            self.cc.allin = True
            return "✅ 已开启全记录"
    
    def switch_rag(self) -> str:
        if self.cc.rag :
            self.cc.rag = False
            return "✅ 已关闭RAG功能"
        else :
            if self.cc.group == 1:
                return "⚠️ 私聊无法开启RAG"
            else:
                self.cc._reset_rag()
                self.cc.rag = True
                return "✅ 已开启RAG功能"
        
    def switch_search(self) -> str:
        if self.cc.search :
            self.cc.search = False
            return "✅ 已关闭搜索功能"
        else :
            self.cc.search = True
            return "✅ 已开启搜索功能"
    
    def handle_model_prompt(self) -> str:
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

    def handle_model_setting(self, key: Message) -> str:
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
        self.cc.mess.append(
            self._create_mess("user", user_input, user_info['name'], True)
        ) # 群聊可获取用户名称，私聊加为好友后方可获取。

        # 使用function calling对对话记录进行润色
        prompt = []
        cont = [] # 为保存搜索记录提供
        if self.cc.search or self.cc.rag:
            tools = []
            if self.cc.search : tools += self.tools_map["_llm_tool_ddg_search"]
            if self.cc.rag : tools += self.tools_map["_llm_tool_rag_retrieve"]
            results = await self._call_api([self.func_call, {"role": "user", "content": "消息: " + self.cc.mess[-1]["content"]}], tools)
            if not results : 
                logger.error("⚠️ function call失败")
            else:
                for info in self._process_response(results)["tool_calls"]:
                    params = json.loads(info["arguments"])
                    tasks = []
                    tasks.append(getattr(self, info["name"])(**params))
                    tool_results = await gather(*tasks, return_exceptions=True)
                    for ret in tool_results :
                        if isinstance(ret, Exception):
                            logger.error(f"⚠️ 工具调用失败: {info['name']} - {str(ret)}")
                            continue
                        if not ret: continue

                        if "ddg" in info["name"]:
                            cont = [value["content"] for value in ret]
                            prompt.append(f"(资料: {ret})\n")
                        if "rag" in info["name"]:
                            prompt.append(f"(记录: {ret})\n") 

        pro_str = " ".join(prompt)
        pro_lst = [self._create_mess("system", pro_str)] if pro_str else []

        # 执行API请求
        response = await self._call_api(([self._create_mess("system", self.cc.current_personality)] + pro_lst + self.cc.mess)
                                        if pro_lst 
                                        else ([self._create_mess("system", self.cc.current_personality)] + self.cc.mess))
        if not response:
            self.cc.mess.pop()
            return "⚠️ 服务暂不可用"
        
        # 处理响应
        result = self._process_response(response)
        self.cc.mess.append(result["assistant_msg"])

        if self.recall_times > 0: self.recall_times -= 1 #增加可撤回次数

        if self.cc.prt : logger.info(self._chat_info())

        # 执行RAG插入(后台任务)
        if self.cc.rag:
            create_task(self._handle_rag_indexing(cont))
        
        # 更新API调用时间
        if not superuser and self.cc.mod in PRE_MOD:  # 特殊模型
            self.cooldown_until = time.time() + self.cc.cooldown
        
        return result["response_message"]
    
    # 记忆命令
    
    def handle_print_memory(self) -> str:
        '记忆输出命令'
        return self._chat_info()
    
    def handle_recall_memory(self, superuser: bool) -> str:
        """记忆撤回命令"""
        if len(self.cc.mess) > 0 and (superuser or self.recall_times < self.cc.max_recall/2):
            self.cc.mess = self.cc.mess[:-2]
            self.recall_times += 1
            if self.cc.prt : logger.info(self._chat_info())
            return "✅ 已撤回上轮对话"
        elif len(self.cc.mess) >= 2:
            return "⚠️ 撤回数量达上限"
        else:
            return "⚠️ 无对话记录"
        
    def handle_clean_memory(self) -> None:
        "记忆清除命令"
        if not self.cc.mess:
            return "⚠️ 记忆体为空"
        else:
            self.cc.mess.clear()
            return "✅ 清除成功"
        
    def handle_add_memory(self, args: Message) -> str:
        '''记忆添加命令'''
        if(len(self.cc.mess) >= self.cc.rd):
            return "⚠️ 记忆体已满，请先清理"
        try:
            parsed = Tools._parse_args(args.extract_plain_text().split(), "用户", "助手")
            if not parsed:
                return "⚠️ 格式错误，正确格式：/记忆添加 [用户/助手] [记忆内容]"

            text, role = parsed

            self.cc.mess.append(
                self._create_mess(self.role_map[role], text)
            )  # 在多人语境中text最好添加用户名，如：用户[xxx]: .....

            logger.info(self._chat_info())
            return "✅ 添加成功"
        except Exception as e:
            logger.exception(f"未知错误:{e}")
            return "⚠️ 系统异常，请联系管理员"
        
    # RAG命令

    async def handle_delete_index(self, args: Message) -> str:
        """RAG删除命令"""
        if not self.cc.rag:
            return "⚠️ RAG功能未开启"
        try:
            await self.cc.hipporag.delete(args.extract_plain_text().split(" "))
            # if self.cc.prt : logger.info(self._rag_info())
            return "✅ 删除成功"
        except ValueError as e:
            logger.exception(f"删除失败: {e}")
            return "ℹ️ 文档不存在"
        except Exception as e:
            logger.exception(f"未知错误:{e}")
            return "⚠️ 系统异常，请联系管理员"
    
    async def handle_insert_index(self, args: Message) -> str:
        '''RAG添加命令'''
        if not self.cc.rag:
            return "⚠️ RAG功能未开启"
        try:
            await self.cc.hipporag.index(args.extract_plain_text().split(" "))
            # if self.cc.prt : logger.info(self._rag_info())
            return "✅ 添加成功"
        except ValueError as e:
            logger.exception(f"添加失败: {e}")
            return "ℹ️ 文档已存在"
        except Exception as e:
            logger.exception(f"未知错误:{e}")
            return "⚠️ 系统异常，请联系管理员"
        
    async def handle_save_index(self) -> str:
        """RAG保存命令（包括图结构和嵌入存储）"""
        if not self.cc.rag:
            return "⚠️ RAG功能未开启"
        try:
            await self.cc.hipporag.save()
            return "✅ 保存成功"
        except Exception as e:
            logger.exception(f"保存失败: {e}")
            return "⚠️ 系统异常，请联系管理员"
        
    async def handle_clear_index(self) -> str:
        """RAG清空命令"""
        if not self.cc.rag:
            return "⚠️ RAG功能未开启"
        try:
            self.cc.rag_file = str(self.cc.personality_file / "RAG_file_base") # 需要清空时，切换至基文件
            self.cc._reset_rag()
            await self.cc.hipporag.clear()
            return "✅ 清除成功"
        except Exception as e:
            logger.exception(f"清空时发生未知错误: {e}")
            return "⚠️ 系统异常，请联系管理员"

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
        self.cc.rag_file = str(self.cc.file / "RAG_file_base") # 将rag位置定向到base，使得rag可以任意清空
        self.cc.current_personality = new_personality
        self.cc.mess.clear()
        logger.info(f"人格已更新: {new_personality}")

    def _save_personality(self, name: str, opt: bool):
        """opt = True，存储于私有文件夹；opt = False，存储于公有"""
        json_pub = PUBLIC_DIR / "personalitys" / f"personality_{name}" / f"{name}.json"
        json_pri = self.cc.personality_file / f"personality_{name}" / f"{name}.json"
        rag_pub = PUBLIC_DIR / "personalitys" / f"personality_{name}" / f"RAG_file_{name}"
        rag_pri = self.cc.personality_file / f"personality_{name}" / f"RAG_file_{name}"

        save_path = json_pri if opt else json_pub
        self.cc.rag_file = str(rag_pri) if opt else str(rag_pub) # 重置rag的位置
        if save_path.exists():
            raise FileExistsError("该人格名称已存在")
        else:
            Path(self.cc.rag_file).mkdir(exist_ok=True, parents=True)
        data = {
            "personality": self.cc.current_personality,
            "memory": self.cc.mess
        }
        ConfigManager.save_json(data, save_path)

    def _load_personality(self, name: str, opt: bool):
        """opt = True，读取于私有文件夹；opt = False，读取于公有"""
        json_pub = PUBLIC_DIR / "personalitys" / f"personality_{name}" / f"{name}.json"
        json_pri = self.cc.personality_file / f"personality_{name}" / f"{name}.json"
        rag_pub = PUBLIC_DIR / "personalitys" / f"personality_{name}" / f"RAG_file_{name}"
        rag_pri = self.cc.personality_file / f"personality_{name}" / f"RAG_file_{name}"

        file_path = json_pri if opt else json_pub
        self.cc.rag_file = str(rag_pri) if opt else str(rag_pub) # 读取人格对应的rag
        if not file_path.exists():
            raise FileNotFoundError
        
        with open(file_path, "r") as f:
            raw_data = f.read()
            if not raw_data.strip():
                raise ValueError("空文件内容")
        data = ConfigManager.load_json(file_path, {})
        self.cc.current_personality = data.get("personality", "")
        self.cc.mess = data.get("memory", [])

    # 人格命令
    async def handle_set_personality(self, args: Message) -> str:
        '''人格设置命令'''
        if new_persona := args.extract_plain_text():
            try:
                self._set_personality(new_persona)

                if self.cc.rag:
                    self.cc._reset_rag()
                    await self.cc.hipporag.clear()

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
            parsed = Tools._parse_args(args.extract_plain_text().split(), "公共", "私有")
            if not parsed:
                return "⚠️ 格式错误，正确格式：/人格储存 [人格名称] [公共/私有]"
            
            name, place = parsed
            if '/' in name or '\\' in name:
                raise ValueError("名称包含非法字符")
                
            await to_thread(self._save_personality, name, True if place == "私有" else False)

            if self.cc.rag:
                if not Path(self.cc.rag_file).exists(): 
                    Path(self.cc.rag_file).mkdir()
                self.cc._reset_rag()
                await self.cc.hipporag.save()

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

    def handle_load_persona(self, args: Message) -> str:
        '''人格读取命令'''
        try:
            parsed = Tools._parse_args(args.extract_plain_text().split(), "公共", "私有")
            if not parsed:
                return "⚠️ 格式错误，正确格式：/人格读取 [人格名称] [公共/私有]"

            name, place = parsed
            if '/' in name or '\\' in name:
                raise ValueError("⚠️ 名称包含非法字符")
                
            self._load_personality(name, True if place == "私有" else False)

            if self.cc.rag:
                self.cc._reset_rag()

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
        
    def handle_list_persona(self) -> str:
        '''人格列出命令'''
        # 获取存储目录下所有文件夹名称
        def extract_names(base_dir):
            if not base_dir.exists():
                return []
            persona_dirs = [d for d in base_dir.glob("personality_*") if d.is_dir()]
            return [d.name.replace("personality_", "") for d in persona_dirs]

        # 获取私有和公共目录下的人格name列表
        persona_names_private = extract_names(self.cc.personality_file)
        persona_names_public = extract_names(PUBLIC_DIR / "personalitys")
        
        # 构建提示信息
        if not persona_names_private and not persona_names_public:
            return "⚠️ 无可用人格配置"

        # 格式化私有人格列表
        private_list = "\n".join([f"· {name}" for name in persona_names_private])
        # 格式化公共人格列表
        public_list = "\n".join([f"· {name}" for name in persona_names_public])

        msg = (
            "📂 可用人格列表：\n"
            f"私有人格：\n{private_list if private_list else '  无'}\n\n"
            f"公共人格：\n{public_list if public_list else '  无'}\n\n"
            "使用人格读取命令以切换人格。"
        )
        
        return msg   
