from .config import ChatConfig, Information, MODELS

class Documentation:
    '''文档类'''
    def __init__(self, 
                 chat_config: ChatConfig):
        self.chat_config = chat_config
        self.information = Information()

    def _dev_doc_content(self) -> str:
        """生成开发者文档内容"""
        return f"""
        ##################
        系统版本: {self.information.full_version}
        1. 思考
        2. 对话 [对话内容]
        3. MD(markdown显示)

        4. 模型列表
        5. 模型设置 [对应模型编号]

        6. 撤回
        7. 记忆清除
        8. 记忆输出
        9. *记忆添加 [用户/助手] [记忆内容]

        10. RAGS
        11. SSIN
        12. ALLIN
        13. 联网搜索
        14. *RAG清空
        15. *RAG保存
        16. *RAG添加 [添加内容]
        17. *RAG删除 [删除内容]
        
        18. 人格列表
        19. 人格设置 [人格描述]
        20. 人格读取 [人格名称] [公共/私有]
        21. 人格储存 [人格名称] [公共/私有]

        22. 群聊白名单 [群号] [增加/删除]
        23. 用户白名单 [QQ号] [增加/删除]

        24. 保存配置
        25. 加载配置
        26. 重置配置

        27. readme 
        28. 功能列表

        29. 退出群聊
        30. 选择群聊 [群号|public|private]
        ##################
        """.replace('    ', '') 

    def _user_doc_content(self) -> str:
        """生成用户文档内容，可自行修改"""
        current_model = MODELS[self.chat_config.mod]
        memory_rounds = int(self.chat_config.rd / 2)
        
        return f"""
        ####################
        欢迎使用Huaer bot! (v{self.information.full_version})
        
        这是一个基于nonebot+napcat+deepseek的聊天机器人。

        当前组群：
        {self.chat_config.name}

        当前模型:
        {current_model}

        当前人格:
        {self.chat_config.current_personality}

        记忆能力:
        {memory_rounds}轮对话

        最大token:
        {self.chat_config.max_token}

        深度思考:
        {'已启用' if self.chat_config.tkc else '暂不显示'}

        RAG功能:
        {'已启用' if self.chat_config.rag else '暂未启用'}

        联网搜索:
        {'已启用' if self.chat_config.search else '暂未启用'}

        （如需修改请联系管理员）
        
        基本功能：
        0./readme : 查看本说明
        1./对话 [+内容] : 基础对话功能
        2./撤回 : 取消上一轮对话
        3./MD : 以markdown格式渲染回复

        祝您使用愉快。
        ####################
        """.replace('    ', '') 

    def show_dev_doc(self) -> str:
        """显示开发者文档"""
        return self._dev_doc_content()

    def show_user_doc(self) -> str:
        """显示用户文档"""
        return self._user_doc_content()