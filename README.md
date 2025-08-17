
<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="imgs/IMG_1411.PNG" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-huaer-bot

_✨基于SiliconFlow、Tavily API，HippoRAG的智能对话插件✨_

<a href="https://nonebot.dev/">
<img src="https://img.shields.io/badge/NoneBot-2.0+-red.svg" alt="nonebot">
</a>
<a href="https://python.org/">
<img src="https://img.shields.io/badge/python-3.10+-orange.svg" alt="python">
</a>
<a href="https://mit-license.org/">
<img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="license">
</a>
<a href="https://www.siliconflow.com/">
<img src="https://img.shields.io/badge/API-siliconflow-green" alt="license">
</a>
<a href="https://github.com/OSU-NLP-Group/HippoRAG">
<img src="https://img.shields.io/badge/RAG-HippoRAG-cyan" alt="license">
</a>
<a href="https://pypi.org/project/nonebot-plugin-huaer-bot/">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-huaer-bot.svg" alt="pypi">
</a>
<a href="https://www.deepseek.com/" target="_blank"><img src="https://github.com/deepseek-ai/DeepSeek-V2/blob/main/figures/badge.svg?raw=true" alt="deepseek">
</a>

</div>

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-huaer-bot

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-huaer-bot
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-huaer-bot
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-huaer-bot
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-huaer-bot
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot-plugin-huaer-bot"]

</details>

## 📜 功能特性
- 具有人格定制功能，可以自由设定人格
- 内置md渲染器；可方便的查看代码，公式等文本
- 具有高度灵活的群管理功能，易于多群使用、功能拓展
- 基于siliconflow丰富的API，可以轻而易举的导入其它大语言模型
- 添加白名单功能，能够十分方便的管理用户，且便于自定义响应规则
- 新增RAG(检索增强生成)，使bot具备了长期记忆的功能
- 新增联网搜索功能，拓展了bot的知识库

## 🧐 快速上手/配置
- 在项目文件所在位置下，找到 **'config.toml'** 文件，可在其中根据注释修改配置，添加自己的API key。也可以在nb2项目中的 `.env` 文件中添加 `HUAER_CONFIG_PATH` 变量指定配置文件生成位置（绝对路径，运行后自动生成）。
- 启动后通过 “/群聊白名单” 添加您的Q群，之后通过 “/对话” 与HuaEr聊天！

## 🎉 详细使用
#### 指令表

|             指令+参数             |             说明             | 权限(U : user,S : superuser) |
| :---------------------------: | :--------------------------: | :--: |
|         __对话命令__          |       对话功能的具体实现      |
|  1. 思考                  | 部分模型具备思考功能，此命令可设定是否显示思考内容 (switch型,即关闭时此命令会使其开启，反之亦然) | S
|  2. 对话 [对话内容]           | 核心功能，可设置调用限制，参见配置文件 | U/S
|  3. MD                        | markdown显示上一段回复，无历史记录或记忆体容量为0则无效 | U/S
| 4. 模型列表                   | 列出所有可选模型 | S
| 5. 模型设置 [对应模型编号]    | 通过查看`2.模型列表`内容选定模型 | S
|  6. 联网搜索 | 是否启用联网搜索(switch) | S
|         __记忆命令__          |       具体实现实则属于对话类      |
|  7. 撤回                      | 撤回上一段对话记录，可在配置文件中设置限额，管理员（superuser）不受限制 | U/S
|  8. 记忆清除                  | 清空记忆体 | S
|  9. 记忆输出 | 输出目前记忆体的所有内容，方便调试 | S
|  10. *记忆添加 [用户/助手] [记忆内容]  | 手动增加一段记忆，建议成对添加，多用户语境建议在内容前加上用户名或助手标识 | S
|  11. RAGS  | 开/关RAG功能(switch) | S
|  12. *SSIN  | 是否存储搜索到的信息至RAG索引(switch) | S
|  13. ALLIN | 是否存储所有对话内容至RAG索引(switch) | S
|  14. *RAG清空  | 清空RAG索引，相当于清空RAG部分的记忆 | S
|  15. *RAG保存  | 保存当前RAG索引内容 | S
|  16. *RAG添加 [添加内容] | 添加文档至RAG索引(多个内容可用空格分隔) | S
|  17. *RAG删除 [删除内容]  | 从RAG索引删除文档(多个内容可用空格分隔) | S
|       __人格命令__            |        与bot行为相关的设定       |
|  18. 人格列表                  | 此群已经存储的人格（私有人格）或公共人格将被列出| S
|  19. 人格设置 [人格描述]      | 设定一个人格吧！（会清空当前记忆）| S
|  20. 人格读取 [人格名称] [公共/私有]| 通过查看 `9.人格列表`内容选定人格（参数位置不敏感）| S
|  21. 人格储存 [人格名称] [公共/私有]| 为人格取名后存储至指定文件夹（包括记忆）（参数位置不敏感）| S
|        __白名单命令__              |   内置两种响应规则，参见配置文件    |
|  22. 群聊白名单 [群号] [增加/删除]  | 操作群聊白名单（参数位置不敏感）| S
|  23. 用户白名单 [QQ号] [增加/删除]  | 操作用户白名单（参数位置不敏感）| S
|        __组管理器命令__            |      对于每个群都会生成的管理容器
|  24. 保存配置                      |  将此群的配置保存到自身配置文件中 | S
|  25. 加载配置                      |  加载此群自身的配置文件 | S
|  26. 重置配置                      |  恢复默认配置 | S
|         __文档命令__               |  信息文本 | 
|  27. readme                        | 用户文档 | U/S
|  28. 功能列表                      | 列出指令表（精简版）| S
|        __管理员命令__               | 见备注一 |
|  29. 退出群聊                      | 取消对选中组群的控制 | S
|  30. 选择群聊 [群号\|public\|private]| 选择要控制的群聊，其中public代表默认配置，private代表全体私聊，群号即为对应群聊 | S

#### 备注
0. 强烈建议完整理解配置文件后再开始
1. 当管理员使用指令时，默认作用于当前所在的组群；但设置 __控制群聊__ 后，无论在什么位置，指令都会作用于被控制的群聊（目前多管理员同时设置控制群聊可能会有一定冲突）
2. 刚加入白名单的群（所有的私聊被认为是一个群）会自动生成独立的默认配置文件（在`项目文件夹/data/groups/群号`），并且在每次启动时读取；可直接修改这些文件来变更规则(包括一些不能显式修改的参数)
3. 私聊功能出于性能考虑，功能有所限制；具体的，无记忆功能，且只能使用最近一次设定的人格，可通过修改 `项目文件夹/data/groups/private` 下的json文件更改
4. 建议私聊前先添加机器人好友，不然无法获取用户昵称
5. 标注*号的函数在完全了解功能及可能缺陷前请尽可能少的使用<details><summary>对 于RAG功能的一些说明</summary>
    a. 对于RAG类命令，事实上bug相当多，且没有太多使用场景。虽引出接口，但一般不必使用。如：
    - `save`相关实则并不必要，增删操作会自动保存
    - `index`考虑应用场景，必需运行完毕才会返回；而这个过程耗时较长且如果中途强制退出会造成三元组不匹配，使索引无法使用
    - `clear`算是这些函数中最稳定的一个，但是不建议频繁使用
    - `delete`较为稳定，可以使用，但不建议频繁；
  
    b. 如果遇上了RAG相关错误,最暴力的解决方式是删除整个RAG存储文件夹（往往以RAG_file开头），让系统重建；但更精准的方法，目前已知的仅有手动修改。同时，由于RAG对存储的特殊需求，整个RAG实例都并非完全运行在内存中，故增删操作会对已存储的信息（如人格）造成影响。对于clear和人格设置有一定优化，不会影响到已存储人格。__出于对可能的修改的防护，请备份重要的RAG文件__
    </details>
6. 不建议过多修改包含base/pubilc的配置，会对重置造成影响
7. 考虑到RAG可能的巨量文档，没有设定诸如“RAG输出”的方法，但在`chat.py`中引出了`_rag_info()`接口，可以获取当前索引中所有文档

## 🔭 records
- _25.5.10_ v2.1.1 默认配置debug完毕 
- _25.7.5_ v2.1.2 正式发布
- _25.7.27_ v2.1.12 增加“记忆添加”功能
- _25.8.11_ v2.2.0 新增自动保存，优化索引构建(增加了时间,显式声明角色)，增加了RAG和联网搜索功能
- _25.8.17_ v2.2.1 添加了国内搜索源
- NV: 如果有大批量文档输入和检索需求的话，会尝试增加上传文件功能；
- NV :如果可行的话，会尝试更新基于vits的tts功能。

## 🙏 感谢
- D圣的开源和S圣的平台搭建
- nonebot-plugin-htmlrender超好用的插件
- 伟大的HippoRAG开源项目
- 各位用户朋友们