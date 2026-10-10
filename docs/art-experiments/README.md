# 美术实验历史归档

这里保存从 mu-art-pipeline skill 移出的、需要版本控制的历史文件。skill 中继续维护通用制作方法；具体模型、动作、数值和冻结场景代码保存在实验档案中。

- chibi-20261009、chibi-joints-20261009：原截图、结果和冻结源码压缩包。
- source-index.json：原实验指纹索引，内容保持迁移时的原样。
- skill-history-20261010/references：原模型恢复记录和武器挂接检查结果。
- skill-history-20261010/scripts/chibi_experiment：原场景专用修复脚本，保留用于追溯。
- [迁移对照](skill-history-20261010/relocations.json)：旧 skill 路径、当前版本控制路径、工作区副本路径及 SHA-256。

历史报告中的 skill_path 等字段记录旧路径；查找实际文件时使用迁移对照。冻结脚本可能包含旧目录、模型、节点、动作和固定参数；复用前先复制到工作区并适配，不作为通用入口运行。

完整的本机探索记录、后续截图、参数和检查结果仍在 tools/art_pipeline/workspace/knowledge/skill_generalization_20261010。该工作区默认由 Git 忽略；本目录中的迁移文件受 Git 跟踪，不依赖本机工作区来保留。

通用方法和脚本调用说明见 [角色重塑文档](../character-restyling.md)。
