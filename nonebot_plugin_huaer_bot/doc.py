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
        1. 撤回
        2. 模型列表
        3. 禁用思考
        4. 显示思考
        5. 记忆清除
        6. 对话 [对话内容]
        7. MD(markdown显示)
        8. 模型设置 [对应模型编号]
        9. 记忆添加 [用户/助手] [记忆内容]

        
        10. 人格列表
        11. 人格设置 [人格描述]
        12. 人格读取 [人格名称] [公共/私有]
        13. 人格储存 [人格名称] [公共/私有]

        14. 群聊白名单 [群号] [增加/删除]
        15. 用户白名单 [QQ号] [增加/删除]

        16. 保存配置
        17. 加载配置
        18. 重置配置

        19. readme 
        20. 功能列表

        21. 退出群聊
        22. 选择群聊 [群号|public|private]
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