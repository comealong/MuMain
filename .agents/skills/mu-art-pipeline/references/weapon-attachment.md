# 武器挂接档案：Player 手持 Sword01

归档日期：2026-10-09。范围：当前 MuMain 客户端、共享 Player 骨架、Dark Wizard Class01 与经典矮人样例、右手静态 Sword01。代码文件及资源指纹、逐姿态误差见 [验证快照](weapon-attachment-verification-20261009.json)。这是已完成试验的依据记录，未安装到游戏数据，未进行游戏内验证。

## 目录

- [插槽与渲染分支](#插槽与渲染分支)
- [矩阵与坐标](#矩阵与坐标)
- [Blender 实现](#blender-实现)
- [错误原因与修复](#错误原因与修复)
- [检查结果与重现](#检查结果与重现)
- [适用边界](#适用边界)

## 插槽与渲染分支

节点编号为原始 Player BMD 的零基 Node，不是 Blender 骨骼列表序号。

| 用途 | Node | 当前骨名 | 父节点 | 路径 |
| --- | --- | --- | --- | --- |
| 右手武器 | 33 | knife_gdf | 28：Bip01 R Hand | 正常手持 Link=false |
| 左手武器 | 42 | hand_bofdgne01 | 37：Bip01 L Hand | 正常手持 Link=false；当前试验未实现 |
| 背挂物品 | 47 | Bone05 | 17 | 玩家背挂逻辑选择；不是手部插槽 |

默认角色节点赋值见 [ZzzCharacter.cpp](../../../../src/source/Engine/Object/ZzzCharacter.cpp:12068)。特殊怪物有自己的 LinkBone 映射，不能将上表用于所有模型。

### 正常手持

调用与处理顺序：

1. [RenderCharacterBackItem](../../../../src/source/Engine/Object/ZzzCharacter.cpp:15227) 判断安全区、特定表情/游泳动作等背挂条件。
2. 未被背挂逻辑截走时，[武器循环](../../../../src/source/Engine/Object/ZzzCharacter.cpp:10074) 选择手中的物品。普通剑使用物品动作 0。
3. [正常手持调用](../../../../src/source/Engine/Object/ZzzCharacter.cpp:10171) 为 RenderLinkObject(0, 0, 0, ..., Link=false, Translate)。Link=false 并不表示物品脱离骨骼；这里仍由武器插槽驱动。
4. [Link=false 分支](../../../../src/source/Engine/Object/ZzzCharacter.cpp:6943) 调用 Owner->RotationPosition(socket, p, Position)，再设置物品 BodyOrigin。RotationPosition 使用旋转变换 p，不包含插槽平移，并复制 socket 到 ParentMatrix；此处 p=(0,0,0)，BodyOrigin 因而为角色位置。分支内还显式复制插槽矩阵到 ParentMatrix。
5. [物品 Animation 调用](../../../../src/source/Engine/Object/ZzzCharacter.cpp:6994) 传入 Parent=true 和 ParentMatrix，将该矩阵作为物品根骨的外部父矩阵。
6. 物品 Transform / SkinVertex 按自己的顶点 Node 变换，输出到角色位置。

这里要保留武器自身的骨矩阵；仅把原始顶点放到玩家节点下，会漏掉物品姿态。

### 背挂及 Link=true

[背挂分支](../../../../src/source/Engine/Object/ZzzCharacter.cpp:15305) 将 LinkBone 改为 47，并按右/左物品调用 Link=true。对于普通剑，[默认附加变换](../../../../src/source/Engine/Object/ZzzCharacter.cpp:6825) 使用角度 (70°,0°,90°)，平移为 (-20,5,40)。弓、盾、披风等有不同条件与偏移。

普通非盾左侧背挂还会在该矩阵右乘角度 (145°,0°,275°)、平移 (0,10,-30) 的附加矩阵；Rage Fighter 有其他取值，见 [左侧附加处理](../../../../src/source/Engine/Object/ZzzCharacter.cpp:6920)。这些值位于 Link=true 分支，不能套用到正常左右手手持。

## 矩阵与坐标

使用列向量、右侧变换先执行。BMD 动画角度是弧度；客户端 AngleMatrix 的输入是度，其顺序为 Rz × Ry × Rx，见 [AngleMatrix](../../../../src/source/Core/Math/ZzzMathLib.cpp:185)。

设：

- O：角色位置，3 维向量。
- P_s：玩家插槽 s 的姿态矩阵，包含玩家父子骨骼层级。
- I_n：武器动作自身的第 n 个骨骼矩阵，已组合其物品内部层级，尚未乘玩家插槽。
- v：武器顶点，n 取该顶点的原始 Node。
- q：试验参数 weapon_scale，默认 1。

角色缩放为 1、无额外 BoneScale/_Scale 的普通手持路径：

~~~text
物品骨矩阵：B_n = P_s × I_n
最终位置：  v_world = O + xyz(B_n × [v,1])
~~~

依据：[Animation 外部父矩阵组合](../../../../src/source/Render/Models/ZzzBMD.cpp:292)、[SkinVertex](../../../../src/source/Render/Models/ZzzBMD.cpp:430)、[RotationPosition](../../../../src/source/Render/Models/ZzzBMD.cpp:725)。

试验另行等比调节武器时采用：

~~~text
v_world = O + xyz(P_s × S(q,q,q) × I_n × [v,1])
~~~

缩放围绕插槽原点作用于已求出的物品姿态，物品根的局部位移也随之缩放。q 是离线预览功能，不是对客户端任意 BodyScale 行为的完整模拟；q=1 才是本次原始剑大小的对照条件。

客户端 SkinVertex 在 Translate=true 时还会乘物品 BodyScale 并加 BodyOrigin；_Scale 和 m_LastBoneScale 会影响不同位置的变换。使用非 1 角色缩放时，应追踪玩家 BoneTransform 的生成、物品 BodyScale 和 BodyOrigin 的具体坐标空间，不能直接在上述试验公式外随意再乘一次比例。

### 当前 Sword01 的自身姿态

资源：src/bin/Data/Item/Sword01.bmd；纹理：sword02.OZJ。该剑为 1 个网格、42 个顶点，所有顶点 Node=0；动作 0 只有 1 个关键帧。其唯一骨骼 Box01 为根骨：

~~~text
位置 ≈ (0.0492190011, 0, -0.0785629973)
旋转 ≈ (1.5707960129, 0.8115779757, 0) 弧度
~~~

武器自身旋转并非零；预烘焙 I_0 × v 后挂到插槽，再做一次相同旋转就会重复变换。上述数据仅用于识别本次资源，不应写死到通用导入器。

## Blender 实现

使用已有 Player 骨架与源 Node 映射。角色 5 个身体网格仍独立，共用一套骨架；武器没有身体的 Armature 修改器。

| 部分 | 设置或行为 |
| --- | --- |
| 剑网格 | 预烘焙武器动作 0 / key 0 的 I_n × v；UV 转换为 (U,1-V) |
| 对照 | 原角色与矮人共享同一个剑 Mesh 数据块 |
| Socket | Empty，Copy Transforms，target=对应角色 rig |
| subtarget | 源 Node 33 对应骨名；不是集合索引 33 |
| 约束空间 | target_space=WORLD，owner_space=WORLD |
| 骨骼位置 | head_tail=0，使用骨头位置，不使用显示骨长末端 |
| 剑父级 | Socket；matrix_parent_inverse=单位矩阵 |
| 剑局部矩阵 | S(q,q,q)，默认单位矩阵，无额外旋转/握柄平移 |
| 身体比例 | 已写入目标骨架平移及网格坐标；不向武器继承非等比缩放 |

Blender 在保存/组织层级时可能重排骨骼集合。恢复和检查插槽应查骨骼 mu_bmd_node=33 元数据及约束 subtarget，不能使用 rig.data.bones[33] 作为源编号判断。

当前实现入口：

- [weapon_attachment.py](../scripts/dwarf_experiment/weapon_attachment.py)：插槽常量、源 BMD 姿态求值、客户端手持顶点对照。
- [build_experiment.py](../scripts/dwarf_experiment/build_experiment.py)：make_weapon_mesh、mount_weapon、check_pose。
- [inspect_saved_blend.py](../scripts/dwarf_experiment/inspect_saved_blend.py)：重开后的插槽元数据与完整动作 39 检查。
- [create_dwarf_experiment.py](../scripts/create_dwarf_experiment.py)：独立工作区入口。

## 错误原因与修复

旧试验在已预烘焙的剑上施加 R(70°,0°,90°) × S(q) × T(-(0,5,0))。它混入 Link=true 的旋转，并人为重设握柄中心，导致手持位置和方向错误。

旧检查仅验证“剑矩阵等于脚本给定的挂接矩阵”和“轴向比例一致”。即使挂接参数本身错误，这两项也会通过。

修复包括：

1. 按正常手持 Link=false 使用节点 33，保留原始物品姿态，局部矩阵仅保留等比缩放。
2. 用源 Player / Sword BMD 独立计算客户端组合后的每个剑顶点，与 Blender 的世界顶点比较；原角色和矮人都检查。
3. 重开 Blend 后检查动作 39 全部关键帧的顶点偏差及轴向缩放。
4. 修正检查器按 Blender 集合序号识别插槽的问题，使用 mu_bmd_node。

## 检查结果与重现

修复样例根目录位于仓库 tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/runs/v01。

| 对照姿态 | 动作 / 零基 key | 矮人剑顶点最大误差 | 原角色剑顶点最大误差 |
| --- | --- | --- | --- |
| 站立 | 4 / 0 | 0.000056267 | 0.000069017 |
| 行走 | 17 / 3 | 0.000024918 | 0.000031630 |
| 奔跑 | 26 / 3 | 0.000026701 | 0.000058375 |
| 挥剑准备 | 39 / 1 | 0.000028328 | 0.000043047 |
| 挥剑中段 | 39 / 4 | 0.000076084 | 0.000089625 |
| 挥剑后段 | 40 / 3 | 0.000046292 | 0.000060569 |

误差定义：全部剑顶点的世界坐标逐分量绝对差最大值，单位为模型坐标，不是屏幕像素或欧氏距离。六姿态允许误差为 0.001。

- 六姿态、两名角色的最大误差：0.0000896250236124。
- 重开后动作 39 的所有关键帧：最大剑顶点误差 0.0000773730129850，阈值 0.001。
- 重开后的最大轴向比例误差：0.00000107288360596，阈值 0.00001；轴向比例由世界矩阵 3×3 部分的奇异值计算。
- 旧样例站立姿态的手动对照偏差：70.7303359077。来源是此前 Blender 单独探测，不是旧 report.json 的字段；资源路径及记录见验证快照。
- 5 个分件、60 骨、284 动作保留；原始游戏文件哈希不变，Sword01.bmd 与 sword02.OZJ 输出副本的字节不变。

历史生成日志中曾出现重开检查因骨骼集合顺序而失败；检查器修复后单独重跑通过。最终结果以 blend_validation.json 为准，不将历史失败日志写成一次完整入口运行成功。

### 查看证据

- [六姿态预览](../../../../tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/runs/v01/pose_comparison.png)
- [可编辑 Blend](../../../../tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/runs/v01/Dwarf_Classic_Experiment.blend)
- [生成报告](../../../../tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/runs/v01/report.json)
- [BMD 回读报告](../../../../tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/runs/v01/bundle_validation.json)
- [重开检查最终报告](../../../../tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/runs/v01/blend_validation.json)

工作区大文件未复制进技能。技能内验证快照保存了报告摘要、原始资源 SHA-256、源码和脚本指纹、成果路径及成果指纹；即使工作区样例被清理，归档中的结论、范围与证据身份仍可查阅。

### 重现

从仓库根目录运行，使用带 Pillow 的根 Python 环境与配置好的 Blender；输出选全新工作区目录：

~~~powershell
& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/create_dwarf_experiment.py --output characters/dwarf_weapon_attachment_repro_01
~~~

对现有修复样例只重跑保存后检查（会更新工作区检查报告，不修改 Blend 或游戏文件）：

~~~powershell
& 'D:/Blender/5.2.2/blender-5.2.2-windows-x64/blender.exe' --background tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/runs/v01/Dwarf_Classic_Experiment.blend --python-exit-code 1 --python .agents/skills/mu-art-pipeline/scripts/dwarf_experiment/inspect_saved_blend.py
~~~

## 适用边界

本次证明所选姿态和完整动作 39 的离散关键帧挂接符合该客户端计算路径。全 284 动作被保留，不等于每个动作的武器接触与视觉质量都经过检查。

未覆盖其他职业/怪物的插槽、自带多帧动画武器、双手 IK、骑乘、布料、背挂实际预览、武器特效，以及运行时插值和非 1 BodyScale。静态剑生成器目前要求一网格、动作 0 一关键帧；其他资源不能静默套用。

改变身体比例后，空间网格变形和手掌姿态可能仍需人工调整。武器刚体方向正确不保证所有握持接触都理想；不要用重复的旋转/偏移掩盖骨架、坐标空间或动作错误。
