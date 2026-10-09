# 角色比例变换与原动作复用（试验）

用于明确要求改变角色身体比例的独立试验。目前实现固定使用 Dark Wizard Class01 五个身体部件、共享 Player 骨架和原始 Sword01；其他职业和装备必须先确认客户端槽位、骨骼及贴图映射。普通角色恢复仍使用原比例。

## 运行与交付

从仓库根目录执行，使用带 Pillow 的根目录 Python 环境和 Blender 5.2：

~~~powershell
& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/create_dwarf_experiment.py --output characters/dwarf_classic_trial_01
~~~

可用 --blender 指定 Blender 可执行文件。默认位置与 create_dark_wizard_group.py 一致。入口复制原始资源、解码贴图、构建骨架及网格、导入全部动作、挂接武器、渲染六个对照姿态，并回读 BMD 和保存后的 Blend。

输出只能位于 tools/art_pipeline/workspace 的子目录；已有试验目录拒绝覆盖。脚本没有安装步骤，不修改 src/bin/Data 或客户端源码。失败时保留日志和部分输出，修正问题后选新目录重跑。

主要输出：

- profile.json：本次比例参数；sources/：原始资源副本。
- runs/v01/Dwarf_Classic_Experiment.blend：五个独立身体网格，共享一套适配骨架，纹理打包。
- runs/v01/pose_comparison.png：站立、行走、奔跑、挥剑三姿态对照；左原始、右矮人。
- runs/v01/generated/Player/：实验 Player 和五个部件 BMD、原贴图。
- runs/v01/generated/Item/：原始剑及贴图，字节保持一致。
- runs/v01/report.json、bundle_validation.json、blend_validation.json：变换与检查报告。

在 Blender 选择 Dwarf_Classic_Group_Armature，用 Action Editor 选择 Dwarf_... 动作。默认动作 4，Blender 第 1 帧对应 BMD 第 0 关键帧；索引含义见 [Player 动作表](player-action-index.md)。左侧 Original_Reference 是静态对照，手动切换右侧动作不会同步左侧。

## 调整比例

复制 scripts/dwarf_experiment/classic_dwarf_profile.json 到工作区，修改后运行：

~~~powershell
& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/create_dwarf_experiment.py --output characters/dwarf_classic_trial_02 --profile tools/art_pipeline/workspace/my_dwarf_profile.json
~~~

所有数值必须有限且大于零；字段必须与默认配置一致。

| 参数 | 默认 | 作用 |
| --- | --- | --- |
| leg_length | 0.55 | 大腿、小腿长度；根高度及步幅接触适配参考 |
| arm_length | 0.70 | 上臂、前臂长度 |
| torso_length | 0.88 | 骨盆和脊柱长度 |
| body_width | 1.30 | 躯干宽度、肩部展开 |
| body_depth | 1.25 | 躯干厚度 |
| limb_thickness | 1.23 | 四肢横截面 |
| neck_length | 0.75 | 颈段长度 |
| head_size | 1.15 | 头、发辫及颈段横截面 |
| hand_size / foot_size | 1.08 | 手指和脚趾所在区域大小 |
| stride_scale | 0.55 | 根节点动画 XY 位移及锁定位置数组 XY |
| skin_blend_radius | 5.0 | 网格空间混合平滑半径，单位为模型坐标 |
| weapon_scale | 1.0 | 武器单独等比缩放；不会改变武器 BMD |

这些是骨骼局部区域的参数，不等于最终整个人物包围盒倍率。实现假设本项目 Biped 的局部 X 沿骨段长度，Y/Z 为横截面。骨骼名称规则及分段处理在 dwarf_geometry.py；换骨架前需要重新确认坐标轴和名称。

## 变换方法及原因

### 骨架适配，保留旋转动作

保留骨骼索引、层级、名称、动作索引、关键帧数量、锁定标记和全部原始旋转。每个子骨骼的局部位置按父骨骼区域的三轴比例缩放；根节点单独缩放水平位移和高度。源动画中存在逐帧局部位移时，同样逐帧适配，而非只改一份静态骨长。

局部矩阵保持 T(p') Rz Ry Rx，再按父子层级相乘。这样手臂和腿可缩短，骨架传给武器的矩阵仍只有旋转和平移。模型比例改动写入工作区副本，不依赖对整个角色施加渲染阶段的非等比缩放。

### 同时适配网格

仅改骨长会留下原始长肢体网格。试验以 Player 动作 0 / 关键帧 0 为参考姿态，将各顶点从原节点局部空间还原到参考空间，再进行连续形变。

每个主要骨段提供映射 H_i = G'_i A_i inverse(G_i)：G_i / G'_i 分别是新旧参考姿态骨矩阵，A_i 是区域比例。对参考空间点 p，用到原骨段的距离 d_i 计算 w_i = 1 / (radius² + d_i²)²；新位置为所有 H_i p 的加权平均，再转回目标 Node 的局部空间。

距离混合只用于离线网格变形，不改变原顶点的单节点绑定。空间中重合的分件顶点使用相同映射，可降低各部件独立缩放导致的接缝错位。法线采用变形 Jacobian 的逆转置并归一化；UV、纹理、拓扑、Node 不变。它无法自动修复原模型的关节造型或所有极端比例下的穿插。

### 地面与位移

先以站立姿态最低点校准根高度，再对动作 4、17、26 的每个关键帧，参考原靴子最低点的上下变化乘 leg_length，补偿目标根 Z。锁定动作的位置数组一并更新。

这是高度补偿，不是足部 IK。其他动作、接触时序、运行时插值、客户端移动速度与 PlaySpeed 尚未适配；缩短根位移不能自动保证不滑步。Blender 预览采用 24 FPS。

### 武器刚体挂接

详细代码依据、矩阵与坐标规则、Blender 约束设置、历史错误和修复验证已集中归档于 [武器挂接档案](weapon-attachment.md)，精确数值与文件指纹见 [验证快照](weapon-attachment-verification-20261009.json)。

当前样例将原始 Sword01 的自身姿态预烘焙后，按正常手持 Link=false 路径直接挂到源节点 33，不额外旋转或重设握柄；weapon_scale 仅作独立等比缩放。对其他物品、双手、背挂和非 1 角色缩放，应先查档案的适用边界。

### BMD 输出

bmd_patch.py 在原 BMD 解码后的字节上仅改顶点坐标、法线、骨骼局部位置和锁定位置数组，保持原版本与其他字节；支持零网格 Player。它不是通用 Blender 动作导出器。普通 import_bmd/export_bmd 仍不会把 Blender Action 编辑编码为 BMD 动画。

不得通过普通网格导出覆盖适配后的 Player 动画；保留本工具生成的 BMD 并回读检查。

## 单独重跑与检查

已有试验的 profile.json 改动后，必须选新的 run 名；以下命令不覆盖 runs/v01：

~~~powershell
& 'D:/Blender/5.2.2/blender-5.2.2-windows-x64/blender.exe' --background --factory-startup --python-exit-code 1 --python .agents/skills/mu-art-pipeline/scripts/dwarf_experiment/build_experiment.py -- --experiment characters/dwarf_classic_trial_01 --output runs/v02
& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/dwarf_experiment/validate_experiment.py --experiment characters/dwarf_classic_trial_01 --run runs/v02
& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/dwarf_experiment/make_contact_sheet.py --experiment characters/dwarf_classic_trial_01 --run runs/v02
& 'D:/Blender/5.2.2/blender-5.2.2-windows-x64/blender.exe' --background tools/art_pipeline/workspace/characters/dwarf_classic_trial_01/runs/v02/Dwarf_Classic_Experiment.blend --python-exit-code 1 --python .agents/skills/mu-art-pipeline/scripts/dwarf_experiment/inspect_saved_blend.py
~~~

入口自动执行的检查包括原始游戏文件 SHA-256、全部离散姿态有限值、旋转数据原样保留、BMD 回读和 UV/拓扑/节点一致、六姿态 Blender 与 BMD 顶点对照、两名角色的武器顶点与客户端手持计算对照及轴向缩放，以及 Blend 重开后的动作、分件、贴图及完整动作 39 武器缩放。

## 已完成样例及适用边界

工作区历史样例：characters/dwarf_classic_experiment_20261009/runs/v01。原始资源不变；5 个分件、60 骨、284 动作，检查 2,766 个离散姿态，保留 138,300 个骨骼旋转关键帧。站立高度约为原来的 76.06%；六姿态顶点误差最大约 0.000065；武器刚体和保存后重开检查通过。这个历史样例的旧挂接方向/位置有误；查看修复后的预览应使用 characters/dwarf_weapon_attachment_fixed_20261009/runs/v01。

修复样例的六姿态（原角色及矮人）剑顶点对照最大误差小于 0.00009，重开后动作 39 全关键帧最大误差约 0.0000774；旧样例站立姿态的相同客户端对照误差约 70.73。修复样例保留全部 284 动作，游戏源文件哈希不变。

这些结果仅证明该样例的数据与预览。尚未验证游戏内表现、其他职业及全部装备、双手握持、骑乘、布料、运行时接触和速度。原始单节点绑定和低面数模型仍限制关节质量；不要将通过数值检查表述为全部动作视觉上无问题。

## Q 版重塑与后续关节修复

需要进一步重塑肩臂、手掌、膝踝或排查比例改变后的接缝时，先读 [Q 版制作经验与源码入口](character-restyling.md)。技能内已归档最终修复源码、历史快照与参数依赖。按输入所处阶段选用算法，避免对已适配的骨架重复应用同一比例变换；拓扑连通仍需配合关节轮廓检查。
