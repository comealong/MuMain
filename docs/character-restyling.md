# 角色改比例与 Q 版重塑制作手册

完整手册及修复源码已归档到项目 mu-art-pipeline skill，后续在技能内维护，避免工作区清理后丢失或多份文档发生分歧。

- [完整制作经验、阶段选择与源码入口](../.agents/skills/mu-art-pipeline/references/character-restyling.md)：肩臂和手掌重塑、膝踝过渡、武器握持、UV、接缝、失败原因、参数与检查边界。
- [肩臂与手掌代码](../.agents/skills/mu-art-pipeline/scripts/chibi_experiment/arm_anatomy.py)。
- [膝踝连续曲面代码](../.agents/skills/mu-art-pipeline/scripts/chibi_experiment/continuous_legs.py)。
- [身体融合与共享分件边界代码](../.agents/skills/mu-art-pipeline/scripts/chibi_experiment/connected_body.py)。
- [保存后及动作中的接缝检查](../.agents/skills/mu-art-pipeline/scripts/chibi_experiment/inspect_saved.py)。
- [源码指纹与来源](../.agents/skills/mu-art-pipeline/references/chibi-experiments/source-index.json)。

技能中保留了实际运行版本的固定路径和 Class01 参数作为历史源码。复用时先按手册选择输入阶段，将相关代码复制到新的实验目录并适配路径、节点、尺度和 UV，不能原地运行旧构建入口覆盖历史成果。

此目录原有的 art-experiments 快照保留供既有链接回溯；新修订的经验以技能内手册为准。本次归档没有重新构建模型或修改游戏数据。
