
<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="imgs/IMG_1411.PNG" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-huaer-bot

_✨基于硅基/DeepSeek API的智能对话插件✨_

<a href="https://nonebot.dev/">
<img src="https://img.shields.io/badge/NoneBot-2.0+-red.svg" alt="nonebot">
</a>
<a href="https://python.org/">
<img src="https://img.shields.io/badge/python-3.8+-orange.svg" alt="python">
</a>
<a href="https://mit-license.org/">
<img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="license">
</a>
<a href="https://www.siliconflow.com/">
<img src="https://img.shields.io/badge/API-siliconflow-green" alt="license">
</a>
<a href="https://github.com/inkink365/nonebot-plugin-huaer-bot">
<img src="https://img.shields.io/badge/poetry-managed-cyan" alt="license">
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
- 具有高度灵活的群管理功能，易于多群使用、功能拓展
- 内置md渲染器（nonebot-plugin-htmlrender）；可方便的查看代码，公式等文本
- 基于siliconflow丰富的API，可以轻而易举的导入其它大语言模型
- 添加白名单功能，能够十分方便的管理用户，且便于自定义响应规则

## 🧐 快速上手/配置
- 在项目文件所在位置下，找到 **'config.toml'** 文件，可在其中根据注释修改配置，添加自己的API key。也可以在nb2项目中的 `.env` 文件中添加 `HUAER_CONFIG_PATH` 变量指定配置文件生成位置（绝对路径，运行后自动生成）。
- 启动后通过 “/群聊白名单” 添加您的Q群，之后通过 “/对话” 与HuaEr聊天！

## 🎉 详细使用
#### 指令表

|             指令+参数             |             说明             | 权限(U : user,S : superuser) |
| :---------------------------: | :--------------------------: | :--: |
|         __对话命令__          |       对话功能的具体实现      |S
|  1. 撤回                      | 撤回上一段对话记录，可在配置文件中设置限额，管理员（superuser）不受限制 | U/S
| 2. 模型列表                   | 列出所有可选模型 | S
|  3. 禁用思考                  | 部分模型具备思考功能，此命令可设定是否显示思考内容 | S
|  4. 显示思考                  | 参见上文 | S
|  5. 对话 [对话内容]           | 核心功能，可设置调用限制，参见配置文件 | U/S
|  6. MD                        | markdown显示上一段回复，无历史记录或记忆体容量为0则无效 | U/S
|  7. 模型设置 [对应模型编号]    | 通过查看`2.模型列表`内容选定模型 | S
|       __人格命令__            |        与bot行为相关的设定       |
|  8. 记忆清除                  | 清空记忆体 | S
|  9. 人格列表                  | 此群已经存储的人格（私有人格）或公共人格将被列出| S
|  10. 人格设置 [人格描述]      | 设定一个人格吧！| S
|  11. 人格读取 [人格名称] [公共/私有]| 通过查看`9.模型列表`内容选定人格（参数位置不敏感）| S
|  12. 人格储存 [人格名称] [公共/私有]| 为模型取名后存储至指定文件夹（参数位置不敏感）| S
|        __白名单命令__              |   内置两种响应规则，参见配置文件    |
|  13. 群聊白名单 [群号] [增加/删除]  | 操作群聊白名单（参数位置不敏感）| S
|  14. 用户白名单 [QQ号] [增加/删除]  | 操作用户白名单（参数位置不敏感）| S
|        __组管理器命令__            |      对于每个群都会生成的管理容器
|  15. 保存配置                      |  将此群的配置保存到自身配置文件中 | S
|  16. 加载配置                      |  加载此群自身的配置文件 | S
|  17. 重置配置                      |  恢复默认配置 | S
|         __文档命令__               |  信息文本 | S
|  18. readme                        | 用户文档 | U/S
|  19. 功能列表                      | 列出指令表（精简版）| S
|        __管理员命令__               | 见备注一 |
|  20. 退出群聊                      | 取消对选中组群的控制 | S
|  21. 选择群聊 [群号\|public\|private]| 选择要控制的群聊，其中public代表默认配置，private代表全体私聊，群号即为对应群聊 | S

#### 备注
1. 当管理员使用指令时，默认作用于当前所在的组群；但设置 __控制群聊__ 后，无论在什么位置，指令都会作用于被控制的群聊（目前多管理员同时设置控制群聊可能会有一定冲突）
2. 刚加入白名单的群（所有的私聊被认为是一个群）会自动生成独立的默认配置文件（在`项目文件夹/data/groups/群号`），并且在每次启动时读取；可直接修改这些文件来变更规则
3. 私聊功能出于性能考虑，功能有所限制；具体的，无记忆功能，且只能使用最近一次保存的人格，可通过修改 `项目文件夹/data/groups/private` 下的json文件更改
4. 建议私聊前先添加机器人好友，不然无法获取用户昵称

## 🔭 records
- _25.5.10_ v2.1.1 默认配置debug完毕 
- _25.7.5_ v2.1.2 正式发布

## 🙏 感谢
- D圣的开源和S圣的平台搭建
- nonebot-plugin-htmlrender超好用的插件
- 各位用户朋友们