# 角色模型恢复与贴图处理：独立部件和共享骨架

文中 `workspace/` 指项目根目录下的 `tools/art_pipeline/workspace/`；命令从项目根目录执行。

## 默认恢复方式与用户确认

用户在 2026-10-08 确认 `DarkWizard_Client_Group` 这次创建完全符合要求，并要求以后采用同样方式恢复角色：**各身体部件保持为独立网格，共用一套 Player 骨架，保留全部源动作、UV、纹理及绑定节点。** 此规则适用于后续角色恢复，不只用于本次 Dark Wizard。

默认运行 `scripts/create_dark_wizard_group.py`。不要把恢复过程改为 Join、焊接或静态合并，也不要从已有 Corrected/OBJ/Blend 复制几何。只有用户明确要求静态快照或合并输出时，才使用[历史静态快照流程](dark-wizard-static-history.md)。

当前现成入口覆盖 Dark Wizard 初始 Class01 部件。恢复其它职业或装备组合时，先从客户端的职业/skin index/身体槽映射确定对应源文件，再复用下面的共享骨架算法；不能直接把 Class01 作为所有职业的部件配置。

已确认的工作文件为 `workspace/characters/dark_wizard_shared/DarkWizard_Client_Group.blend`：五个独立网格、一套 60 骨骼的 Player Armature、全部 284 个源动作。只激活站立动作不代表只导入了一个动作。

## 默认入口：创建分件模型组

恢复角色、编辑部件、预览动作或准备换装时，均使用本流程。源资源数值、骨骼与动作数量由当前 Player 文件读取；本案例为 60 根骨骼、284 个动作。

```powershell
& .venv/Scripts/python.exe `
  .agents/skills/mu-art-pipeline/scripts/create_dark_wizard_group.py `
  --output characters/dark_wizard_shared
```

输出目录必须不存在；再次创建时换一个 `--output`。脚本从原始游戏资源暂存输入，生成 `DarkWizard_Client_Group.blend`、同名 PNG、资源 SHA-256 清单 `source_manifest.json` 及模型组清单 `group_manifest.json`。生成过程不读取旧 Corrected、OBJ 或旧 Blend。

Blender Outliner 结构：

```text
DarkWizard_Client_Group（Collection）
└── Player_Shared_Armature（共同骨架，60 根骨骼）
    ├── HelmClass01
    ├── ArmorClass01
    ├── PantClass01
    ├── GloveClass01
    └── BootClass01
```

五个网格分别保留源 BMD 的顶点、面、UV 和绑定节点，共计 373 顶点、640 个三角面；不 Join、不焊接。各网格只有一个指向同一骨架的 Armature 修改器，每个顶点按原 `node` 以权重 1 绑定。贴图按 BMD 的 `skin_barbarian_01.jpg` 字段加载并打包，UV 为 `(U,1-V)`。骨架保存在集合内，模型选择和换装可以按独立对象进行。

### 本次可复用的完整创建过程

1. 用根目录 `.venv` 启动入口，在新的工作区目录暂存 `player.bmd`、五个 Class01 BMD 及源 OZJ，记录 SHA-256。原始游戏资源只读，生成目录已存在则拒绝覆盖。
2. 用 `parse_bmd()` 解码 v10/v12。按原始骨骼索引校验各部件实际使用节点及其父链；保留索引，不按辅助骨骼名称重新排序。
3. 只创建一个 Player Armature。用 **Player action 0/key 0** 计算参考矩阵，建立 60 根骨骼及父子关系；此参考姿态不等于初始显示的站立动作。
4. 分别创建 Helm、Armor、Pant、Glove、Boot 网格。各顶点从 BMD 骨骼局部坐标变换到共同参考骨架空间；保留原面序、原始位置、绑定节点和法线属性。
5. 五个对象分别 parent 到同一个骨架，各添加一个指向该骨架的 Armature 修改器。按顶点原始 `node` 分配对应骨骼组，权重为 1；不创建五套各自独立的骨架。
6. 按各 BMD 的纹理字段使用 `skin_barbarian_01.jpg`，从 OZJ 解包并打包图片到 Blend。逐面角写入 `(U,1-V)`，保持图片正常方向，不额外翻转。
7. 为 Player 每个动作建立独立 Action。使用下文的 rest/basis 换算、四元数连续性处理及线性通道，保留所有关键帧和源动作元数据；锁定位移动作按客户端规则处理根节点 XY。
8. 激活 **Player action 1/key 0**（Blender 第 1 帧）作为初始站立显示，设置当前播放范围 1～6。创建时检查变形结果与原始 BMD 的共同站立姿态吻合，再保存分件 `.blend`、预览和清单。

对应脚本均保存在本 Skill：

| 脚本 | 用途 |
| --- | --- |
| `scripts/create_dark_wizard_group.py` | 默认恢复入口；暂存资源并启动独立 Blender 进程。 |
| `scripts/build_dark_wizard_group_blender.py` | 组织模型组、设定初始动作、检查初始绑定并保存 Blend/清单。 |
| `scripts/mu_art_pipeline/character_sources.py` | 公共源文件配置、暂存及 SHA-256；不依赖旧静态工具。 |
| `scripts/mu_art_pipeline/poses.py` | BMD 局部/全局姿态数学及已使用骨骼父链校验。 |
| `scripts/mu_art_pipeline/blender_player_rig.py` | 一套 Player 骨架、全部动作、rest/basis 换算及源元数据。 |
| `scripts/mu_art_pipeline/blender_player_meshes.py` | 五个独立网格、共同骨架绑定、UV/纹理和源属性。 |
| `scripts/mu_art_pipeline/blender_character_preview.py` | 公共镜头与视口呈现；不依赖合并 OBJ 导入流程。 |

该入口后续生成的两个清单记录 `restoration_mode=separate_parts_shared_armature` 和 `merged_mesh=false`，便于后续确认输出方式。源文件快照与 `player_source_metadata.json` 保存在输出目录，不依赖最初创建时的临时会话。

### 骨骼与动作的转换依据

Blender 的网格坐标先放入共同的 Player action 0/key 0 参考骨架空间：`v_rest = B_rest[node] · v_local`。动作通道使用实际 Blender rest matrix 计算：

```text
L_i(key) = T(position) · Rz(z) · Ry(y) · Rx(x)  （BMD 旋转为弧度）
G_i(key) = G_parent(key) · L_i(key)             （根节点的 G_parent 为单位阵）
basis_i(key) = inverse(B_rest_i) · B_rest_parent · L_i(key)
v_final(key) = G_[vertex.node](key) · v_local
```

根节点的 `B_rest_parent` 为单位阵。这样 Armature 修改器的 inverse bind 与参考坐标抵消，最终仍为 `G_i(key) · v_local`。不能把 Corrected 的 action 1 世界坐标当作骨骼局部坐标再次绑定，否则会重复施加姿态。

Player 的全部 284 个动作保留为独立 Blender Actions，使用四元数旋转通道和线性关键帧。初始选中 `Player_001_PLAYER_STOP_MALE`，Blender 第 1 帧对应 BMD 第 0 关键帧。骨架保存完整源动作元数据，网格保留原始位置/node/法线属性；以后编辑、导出时可以追溯来源。

### 动作名称和编号查询

完整对应关系见 [Player 动作编号对照表](player-action-index.md)，包含全部 284 项、中文直译、关键帧数、常用动作及分类。按 Blender Action 的 `mu_bmd_action_index` 查找；初始动作索引 1 为 `PLAYER_STOP_MALE`，索引 0 为 `PLAYER_SET`。当前旧 Action 名称里的 `Action_...` 只是创建时的通用标签，具体含义以编号对应的源码枚举为准。

### 在 Blender 中操作

- 选中 `Player_Shared_Armature`，在 Dope Sheet 的 Action Editor 中选择其他 `Player_...` 动作。所有部件随共同骨架运动。
- 初始时间范围是站立动作的 1～6 帧。切换动作后，可根据 Action 的 `mu_bmd_keys` 属性设置时间范围；Blender 帧号始终为 BMD 关键帧索引加 1。
- 直接选择某个部件可独立编辑或隐藏。替换部件时仍需保留共同节点映射和共享 Armature 修改器。
- 为方便看贴图，默认关闭视口骨骼/附加物叠加显示。需要查看骨架时，在 Viewport Overlays 中开启 Bones，并可为骨架开启 In Front。

### 当前交付状态

2026-10-08 创建的 `workspace/characters/dark_wizard_shared/DarkWizard_Client_Group.blend` 已在 Blender 打开，随后用户明确确认符合要求。它包含5 个独立网格、1 个 Armature、60 根骨骼、284 个动作。初始站立姿态逐顶点与原始 BMD 的共享姿态计算结果比较，最大坐标误差约 `5.73e-5`（Blender 骨架/四元数浮点转换），低于创建时采用的 `2e-4` 限值。

完整动作来源另存于同目录 `player_source_metadata.json` 并载入 Blend 的 `Player_BMD_Source` 文本。将大段单行 JSON 通过文件载入 Blender Text；直接 `Text.write()` 写入时已观察到明显性能问题。

用户要求先不处理光照问题：当前模型组的自定义法线/Armature 变形后光照仍有异常，尚未修复；上述坐标匹配只证明几何绑定和初始姿态，不代表法线显示已验证。继续检查或修复光照时，应使用这个共享骨架场景，保留原始面角法线及节点属性作为依据。

### 与运行时的边界

本模型组复现客户端的“独立部件＋共同骨骼姿态”结构。锁定根位移的动作按客户端规则冻结根节点 XY 为该动作第 0 关键帧，`BodyHeight=0`；默认对象位移/朝向为 0、比例为 1。

Blender 预览统一使用 24 FPS，每个 BMD 关键帧占一帧；这不等于客户端按动作 PlaySpeed 播放的速度。运行时动作切换混合、头部转向、装备特效、布料和游戏世界位置没有烘焙进这个编辑场景。模型分件保存不等于已经完成逐部件导回游戏的验证，导出时仍应保持客户端原有身体槽和资源文件对应关系。

## 客户端实际选择的部件

Dark Wizard 是 `CLASS_WIZARD`，默认 `SkinIndex` 为 0。客户端按身体槽加载以下 Class01 文件，模型组保持相同的部件对应关系：

| 身体槽 / 网格对象 | 原始 BMD | 客户端模型槽 | 顶点 | UV 记录 | 面 |
| --- | --- | --- | ---: | ---: | ---: |
| 头部 `HelmClass01` | `HelmClass01.bmd` | `MODEL_BODY_HELM + 0` | 68 | 72 | 114 |
| 躯干 `ArmorClass01` | `ArmorClass01.bmd` | `MODEL_BODY_ARMOR + 0` | 92 | 105 | 150 |
| 裤子 `PantClass01` | `PantClass01.bmd` | `MODEL_BODY_PANTS + 0` | 71 | 91 | 120 |
| 手套 `GloveClass01` | `GloveClass01.bmd` | `MODEL_BODY_GLOVES + 0` | 72 | 57 | 130 |
| 靴子 `BootClass01` | `BootClass01.bmd` | `MODEL_BODY_BOOTS + 0` | 70 | 51 | 126 |

总计 **373 顶点、640 个三角面、1,920 个面角**。五个部件各有 56 个骨骼记录，但几何只引用其中部分节点。不要按职业名把纹理换成 `skin_wizard_01.jpg`。

源码位置：

- `src/source/Engine/Object/ZzzOpenData.cpp`：加载 `Player.bmd`、身体部件及贴图。
- `src/source/Engine/Object/ZzzCharacter.cpp`：逐 `BodyPart` 渲染，共用玩家姿态。
- `src/source/Data/DataHandler/LoadData.cpp`：`OpenModelTextures()` 从 BMD 的纹理字段选择文件。
- `src/source/Character/CharacterManager.cpp`、`src/source/Core/Globals/_enum.h`：职业、skin index 和 Player 动作枚举。

## 贴图错位根因与处理规则（2026-10-08）

### 源码证据

`src/source/Render/Sprites/GlobalBitmap.cpp` 的 `OpenJpegTurbo()` 用 TurboJPEG 解码 OZJ 内部 JPEG，没有使用 `TJFLAG_BOTTOMUP`，随后按原行序复制到纹理缓冲区。`UploadTextureSDLGpu()` 原样上传这些像素。`src/source/Render/Models/ZzzBMD.cpp` 的 `RenderMesh()` 使用 BMD 保存的 `TexCoordU/TexCoordV`，`src/shaders/basic_textured.frag.hlsl` 直接用传入 UV 采样。因此这条客户端链路的 V=0 对应图片顶部。

Blender 对正常打开的图片使用从底部开始的 UV。之前的支持代码 `import_bmd()` 把 BMD UV 原样赋给 Blender，Corrected OBJ 也保留了同样的错误约定。这使头、衣服、裤子等采到贴图图集上下相反的位置；图片已经连接、图片文件存在、UV 数值在 0～1 内都不能证明映射正确。

正确的边界转换为：

```text
BMD → Blender/OBJ：U_blender = U_bmd；V_blender = 1 - V_bmd
Blender → BMD：    U_bmd = U_blender；V_bmd = 1 - V_blender
```

图片保持正常方向；不要在转换 UV 后再次翻转图片，或在材质节点内再翻 V。本案例 JPEG 为 256×256，无需处理非二次幂纹理的补边比例。

### 原始 UV 修复记录

- 五个 Class01 BMD 的纹理字段均为 `skin_barbarian_01.jpg`，仍使用这个文件，不按职业名称猜换图片。
- 对 Corrected 按五个源 BMD 的三角面和面角索引重新写入全部 1,920 个 UV，使用 `(U,1-V)`。先严格核对五组网格的顶点数、面数和面顶点顺序，任一不匹配则中止。
- 同步修正 `workspace/Player/DarkWizard_Initial_Corrected.obj` 的 `vt` 记录。顶点、面索引和模型位置均保留。
- 当时的 `dark_wizard_initial_complete.blend` 及其 Blender 场景已经修正。Corrected 使用明确连接到 `UVMap` 的材质和打包图片；旧对照对象已隐藏，方便检查正确对象。
- 支持代码位于 `.agents/skills/mu-art-pipeline/scripts/mu_art_pipeline/blender_mcp.py`：新 BMD 导入执行 V 转换，导出执行逆转换。新导入网格标记 `mu_bmd_uv_convention = blender_bottom_left`。旧版导入、带源属性而没有此标记的网格保留原来的导出约定，避免旧场景重复反转；这些旧场景的 Blender 显示仍需重新导入或明确迁移 UV。

### 历史 Corrected 的 UV 修复命令

脚本已归入 Skill：`.agents/skills/mu-art-pipeline/scripts/repair_dark_wizard_uv.py`。

从项目根目录执行：

```powershell
& 'D:/Blender/5.2.2/blender-5.2.2-windows-x64/blender.exe' `
  --background tools/art_pipeline/workspace/previews/dark_wizard_initial_complete.blend `
  --python .agents/skills/mu-art-pipeline/scripts/repair_dark_wizard_uv.py
```

该命令要求五个源 Class01 BMD、`skin_barbarian_01.jpg` 和 Corrected OBJ 已放在 `workspace/Player/`。它在 `workspace/backups/dark_wizard_uv_<时间>/` 备份 Blend 与 OBJ，验证拓扑后从原始 BMD 重新生成 UV、打包图片并保存 Blend/OBJ，最后渲染正面和背面检查图。每次都从源 UV 重建，重复执行不会把 V 翻回错误方向。脚本比较修复前后每个顶点坐标，发现几何改变则报错。

这条命令用于历史静态 Corrected 的 UV 修复，不是角色恢复入口。新角色默认通过上面的分件模型组脚本恢复；静态工具详见历史参考。

### 验证记录

- 修复前逐面角比较：Corrected OBJ UV 与源 BMD 的原始 UV 误差小于 `5e-8`，确认旧输出没有执行 V 转换。
- 修复后全部 640 个面、1,920 个面角按源 BMD 重建，顶点坐标逐项不变。
- 在独立 Blender 进程实际执行新导入、新导入后的导出、旧导入兼容导出、静态网格导出；四项 UV 数值检查最大误差均为 0（检查导出场景数据，未进行游戏内验证）。
- 已查看正面、背面渲染：脸、头发、上衣、裤子、手套、靴子的图案回到对应部位。检查图为 `workspace/previews/dark_wizard_initial_corrected_texture_preview.png` 与同名 `_back.png`。
- 本次确认 Blender 中的 UV/贴图映射；尚未进行客户端内重新导入验证。

## 相关文件

- 用户确认的分件角色模型组：`workspace/characters/dark_wizard_shared/DarkWizard_Client_Group.blend`
- 分件模型组预览：同目录 `DarkWizard_Client_Group.png`
- 资源快照与来源清单：同目录 `sources/`、`source_manifest.json`
- 骨架、动作和部件清单：同目录 `group_manifest.json`
- 完整源动作元数据：同目录 `player_source_metadata.json`，Blend 内为 `Player_BMD_Source`
- [历史静态 Corrected 创建过程及核对证据](dark-wizard-static-history.md)
