# 动作查询、编号与时间约定

## 以当前源数据建立映射

动作编号来自实际资源的动作数组；可读名称来自当前客户端枚举。不要按过去的动作编号、Blender 显示名或同职业的旧文件猜动作含义。

条件编译可能改变编号范围。提取时选择与实际 BMD 动作数及连续索引范围一致的枚举配置，保留同值别名；分段标记不是新增动作。匹配不唯一或范围不完整时停止解析，不能静默采用旧表。

`scripts/mu_art_pipeline/player_actions.py` 提供源码枚举与资源匹配算法。`scripts/extract_player_actions.py` 生成实际资源的 JSON/Markdown 目录：

~~~powershell
& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/extract_player_actions.py
~~~

可用 `--header`、`--model` 指定源文件，`--output` 选择工作区下的目录。输出放在 `tools/art_pipeline/workspace` 中，含来源指纹、枚举配置、别名和关键帧数。动作目录是资源数据，不写回 skill；旧的 `--update-skill` 参数仅兼容接受，不再更新 skill。

自动生成器中的可读释义不等同于官方技能名称，也不构成逐帧视觉确认。同一个动作可能有多个调用场景，动作存在也不代表当前角色能在游戏中使用它。

## Blender 选择与时间

- 按 Action 的 `mu_bmd_action_index` 匹配源动作，按 `mu_bmd_keys` 获取范围，不依赖对象显示名。
- 当前 BMD 导入约定中，源 key 从零开始，Blender frame 从一开始：`frame = key + 1`。其它导入格式需另确认起始偏移。
- 切动作需选对应 Action/slot，并更新播放范围；仅替换显示名不改变实际通道。
- 获取故障姿态时，记录实际动作索引、key/frame 及子帧。不能用“看上去像挥剑”代替具体求值状态。
- 每个源关键帧对应一个编辑帧，不代表客户端的实际播放秒数；还要考虑 PlaySpeed、插值、动作切换及运行时控制。

数值检查覆盖的离散关键帧、帧间抽样与实际查看的图各自记录在实验报告。导入所有动作或检查全部离散关键帧都不能声称完整的连续时间视觉验收。
