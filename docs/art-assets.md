# 美术资源编辑与转换

本文整理 MuMain 客户端美术资源的常见格式、可用工具，以及本仓库现有的地图编辑工作流。第三方工具由社区维护，支持的客户端 Season 和资源变体可能不同；操作前先备份原始资源，并用当前客户端验证输出。

## 仓库内的资源位置

客户端运行时资源主要位于 `src/bin/Data/`，构建时会复制到 `Main.exe` 旁边的 `Data/` 目录。常见目录包括：

| 资源 | 常见位置 |
|---|---|
| 玩家身体与装备模型、贴图 | `Data/Player/` |
| 怪物模型与贴图 | `Data/Monster/` |
| 道具模型与贴图 | `Data/Item/` |
| 地图地形、贴图、物件 | `Data/WorldN/`、`Data/ObjectN/` |

修改运行目录中的文件后，如果希望改动进入仓库或构建产物，请将文件同步回 `src/bin/Data/`。物品的模型引用和外观设置另见 [item-data.md](item-data.md)。

## 格式与工具

### `.bmd` 模型

`.bmd` 是客户端使用的模型格式，角色、怪物、装备和地图物件都可能引用它。

- [MU Online BMD Viewer](https://github.com/xulek/muonline-bmd-viewer) 可查看 MU Online 的 BMD 模型、动画和骨骼，并导出 GLB、PNG 贴图等，适合检查资源或导出后继续处理。它公开列出的导出格式不包含 MU `.bmd`，因此不能单独完成“编辑后写回客户端 BMD”。
- 社区也发布过 MU 客户端用的 BMD 编辑器，例如 [S12 BMD Editor 相关页面](https://tuservermu.eu/index.php?topic=96.0)。使用前应确认工具支持的 Season、模型类别以及骨骼和动画读写能力；不要直接用重要资源试验。
- 注意有些同名“BMD importer”是为任天堂游戏格式编写的。例如 [BleMD](https://github.com/niacdoial/blemd) 支持的是 Nintendo BMD/BDL，**不是 MU Online 的 BMD**。

本仓库的 mu-art-pipeline Skill 支持将 MU BMD v10/v12 导入为首帧姿势、加权 Blender 骨架和动作，也可把 Blender 中选中的网格导出为客户端 v12 BMD，并将材质贴图写成 OZT。导入会重建加权 Blender 骨架和每个动作对应的 Blender Action；从已有模型导出时会保留源骨架及 BMD 动作数据，并写入编辑后的网格，但不会把 Blender Action 的修改编码进 BMD 动作数据。新模型导出为单帧静态模型。审阅后可用 mu-art install 预览并安装到 src/bin/Data/；也可用 --data-root 指向正在运行的客户端 Data 目录。覆盖已有文件必须显式传入 --overwrite，旧文件会先备份到工作区。安装器会校验 BMD 和随模型导出的 OZJ/OZT 贴图，并报告未随包提供的贴图引用。导入器能打开模型或结构检查通过，都不代表生成文件已通过本客户端的画面和资源路径验证。详见项目 Skill：.agents/skills/mu-art-pipeline/SKILL.md。

### `.ozj`、`.ozt` 贴图

这些是客户端使用的图像资源格式，常见社区工具可在 `.ozj` 与 JPG、`.ozt` 与 TGA 之间转换。可参考 [MagicHand / MuEditor](https://magichand.ibhost.com.br/)；该项目及其他老工具的可用性、支持范围和下载来源可能变化。

通常的编辑流程是：备份原文件，将贴图转换为可编辑格式，在图像编辑器中修改，按客户端兼容的格式和原文件名转换回来，再放回原目录测试。尽量保持原贴图的尺寸、透明通道和命名；客户端按资源引用查找文件，改名可能导致贴图丢失。

### 地图文件与地形贴图

本仓库有内置的 **Map Editor**，可编辑地表贴图映射、地形高度、行走属性和地图物件，也能导入贴图、跨地图复用物件。它能摆放和复用已有 BMD 模型，但不编辑模型网格本身。

- Map Editor 的完整说明：[MAP_EDITOR.md](../src/MuEditor/UI/MapEditor/MAP_EDITOR.md)
- DevEditor 和编辑器构建入口：[dev-editor.md](dev-editor.md)
- 地图贴图导入支持 `.jpg` 或 `.ozj`，并复制到当前地图可用的扩展贴图槽位。
- 编辑行走属性时，客户端地图文件和服务器地图数据需要分别保存、部署；具体步骤和文件格式见 Map Editor 指南。

## 按目标选择流程

| 目标 | 建议流程 |
|---|---|
| 改角色/怪物颜色、花纹 | 转换并编辑对应贴图，保持文件名和尺寸等兼容条件，再进游戏检查 |
| 查看角色、怪物或物件模型 | 用 MU Online BMD Viewer 检查网格、骨骼、动画和贴图 |
| 改地图地表或摆设 | 用仓库的 Map Editor；地表贴图可从 T. Browse 导入，物件可从 O. Browse 复用 |
| 改角色/怪物/装备的模型网格 | 用 mu-art-pipeline Skill 将 BMD 导入 Blender 编辑并导出 v12，再预览并安装到客户端资源目录 |


## 角色改比例与 Q 版重塑经验

修改身体比例、重塑肩臂和手掌、复用 Player 动作或排查分件接缝时，先读[角色改比例与 Q 版重塑制作手册](character-restyling.md)。手册归档了原始截图到概念图、骨架与网格适配、武器握持、UV 与重叠面诊断、失败原因、参数边界和保存后检查，并附制作代码快照及前后对比。
