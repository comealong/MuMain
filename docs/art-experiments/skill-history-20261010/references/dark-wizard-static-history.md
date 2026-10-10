# Dark Wizard 历史静态快照与 Corrected 创建记录

本页保留曾经从操作日志恢复的静态 Corrected 生成过程和独立核对证据。**恢复角色模型的默认流程已经改为独立部件＋共享 Player 骨架**，请使用[角色恢复与贴图处理](character-model-assembly-and-textures.md)中的 `create_dark_wizard_group.py`。

只有用户明确需要单帧静态对照或合并输出时，才使用本页的静态工具。`rebuild_dark_wizard_initial.py` 现在要求显式传入 `--static-snapshot`；直接运行会提示使用角色模型组入口。保留这段历史不表示它是默认恢复方案，也不允许从现有 Corrected 复制几何作为恢复输入。

文中 `workspace/` 指 `tools/art_pipeline/workspace/`；命令从项目根目录执行。

## 历史静态 Corrected 的创建方法

2026-10-08 已从原始操作日志恢复 `DarkWizard_Initial_Corrected` 的实际生成代码，并从原始游戏资源独立重建验证。此前文档中“找不到动作帧、无法恢复具体变换”的描述已经被本次发现取代。

- 输入为五个 Class01 BMD，以及共同的 `Player/player.bmd`。
- **共同姿态为 Player 的 `action_index=1`、`key_index=0`，均从 0 开始计数。** 客户端枚举中 1 对应 `PLAYER_STOP_MALE`。Player 文件有 60 根骨骼、284 个动作；此动作有 6 个关键帧，`lock_positions=false`。
- 每个顶点按自身 `node` 指向的 **Player 全局骨骼矩阵**变换。五个部件使用同一份矩阵；没有逐部件手工位移、旋转或缩放。
- 变换结果依次写为五组 OBJ，再导入 Blender，得到单个静态网格。共享姿态已烘焙进坐标，最终对象没有 armature、权重驱动或动画。
- 贴图使用 BMD 指定的 `skin_barbarian_01.jpg`；Blender/OBJ 的 UV 必须为 `(U,1-V)`。原始生成代码漏掉了这次 V 转换，随后已经修复。
- 重建脚本只接受源资源目录与新输出目录，**不读取 Corrected 的 OBJ/Blend，不以现有模型坐标为生成输入**。比较是独立的后续步骤。

## 恢复出的历史操作记录

原始生成工具为 Node REPL，先在内存中解码 Player、计算共享姿态，再写出 OBJ；不是从 Blender 里复制一个已拼好的对象。

| 北京时间（2026-10-08） | 原始操作 |
| --- | --- |
| 20:53:07.931 | 解密 v12 `player.bmd`，解析所有动作和骨骼的父节点、局部位置、欧拉旋转。 |
| 20:53:41.459 | 定义 `trs5`、`mult5`、`calc5`，从 **action 1 / key 0** 生成 `pose5`；读取五个 v10 部件，以 `pose5[vertex.node]` 变换顶点。 |
| 20:53:55.584 | 将变换后的坐标、旋转后的法线、原始面角索引写入 `DarkWizard_Initial_Corrected.obj/.mtl`。 |
| 20:53:58.321 | 用 `mu_blender.import_model` 导入该 OBJ。 |
| 20:54:06.630 | 用 `load_texture` 连接 `skin_barbarian_01.jpg`，移开旧 Initial/Combined 供比较。 |
| 20:55 起 | 曾把 Corrected 移到 X=1400 与旧版本对照；这是场景摆放，不参与 OBJ 的骨骼计算。最终参考对象位于原点、旋转为 0、缩放为 1。 |
| 20:58:05 / 21:08:57 | 曾错误试用 wizard 贴图，后来恢复 barbarian。更换图片未解决当时遗漏的 V 转换。 |

来源会话文件：`rollout-2026-10-08T20-51-58-01a11acc-bff4-7641-bc41-6988b859e236_01a11b92-0a45-7543-a4ff-421286aa6484.jsonl`。恢复出的三段创建代码及各自 UTC 时间保存在 `workspace/reconstruction/recovered_creation_steps.json`；相关工具调用摘录在同目录 `original_creation_tool_calls.json`。算法已经固化到本 Skill，不依赖以后还能访问原会话日志。

## 从原始 BMD 到最终坐标的完整步骤

### 1. 准备与校验输入

从 `src/bin/Data/Player/` 只读读取上述六个 BMD 和 `skin_barbarian_01.OZJ`，暂存到新输出目录的 `sources/`。使用现有 `parse_bmd()` 解析 v10/v12；不要对 v12 密文直接按 v10 布局读取。Player 没有网格，仅提供骨架和动作。

五个部件的顶点/法线实际使用节点如下：

| 部件 | 使用的 Player 骨骼索引 |
| --- | --- |
| Helm | 19, 20, 22 |
| Armor | 17, 18, 19, 26, 27, 35, 36 |
| Pant | 2, 3, 4, 10, 11, 17, 48, 49 |
| Glove | 26, 27, 28, 29, 30, 35, 36, 37, 38, 39 |
| Boot | 4, 5, 11, 12 |

这些节点及父链的名称、父索引与 Player 对应。部分未使用的 51～55 号辅助节点名称不同；不能因此重新排序骨骼或拒绝当前有效组合。

### 2. 计算唯一一份 Player 姿态

对 Player 的每根非 dummy 骨骼，读取 `bone.actions[1].positions[0]` 和 `rotations[0]`。旋转为**弧度**，列向量约定下：

```text
L_i = T(p_i) · Rz(z_i) · Ry(y_i) · Rx(x_i)
G_i = L_i                       （parent = -1）
G_i = G_parent · L_i             （有父节点）
```

dummy 的局部矩阵为单位阵。须递归计算父节点，不能假设所有父节点都排在子节点前面。

为防止欧拉顺序再次误用，局部矩阵前三行完整写为（cx=cos(x)，sx=sin(x)，其余同理）：

```text
[ cz*cy,  cz*sy*sx - sz*cx,  cz*sy*cx + sz*sx,  px ]
[ sz*cy,  sz*sy*sx + cz*cx,  sz*sy*cx - cz*sx,  py ]
[   -sy,             cy*sx,             cy*cx,  pz ]
[     0,                 0,                 0,   1 ]
```

当前动作 `lock_positions=false`，原始代码没有额外的根节点锁定位移、动画插值、游戏世界坐标、对象角度或比例参数。

### 3. 变换部件并保留面角关联

```text
vertex_final = G_[vertex.node] · (vertex.position, 1)
normal_final = normalize(G_[normal.node][0:3,0:3] · normal.normal)
UV_blender   = (UV_bmd.U, 1 - UV_bmd.V)
```

BMD 顶点是其绑定骨骼的局部坐标；本次静态重建直接乘共享矩阵，不再额外乘 inverse bind 矩阵。法线使用**法线自身的 node**，不拿顶点 node 代替，也不加平移。

依次输出 Helm、Armor、Pant、Glove、Boot。保留每个三角面的顶点、UV、法线索引及顺序；OBJ 的三个索引流分别从 1 开始，按各自数组长度累计偏移。UV 和法线数量不必等于顶点数量，不能共用一个偏移量。

坐标、法线输出 7 位小数，与历史 `toFixed(7)` 对应。五组均使用 `MU_Skin`；MTL 的 `map_Kd` 指向同目录 `skin_barbarian_01.jpg`，由 OZJ 原始 JPEG 解包而来，不翻转图片。

### 4. 导入 Blender 保存静态模型

新重建工具显式用 `forward_axis='Y', up_axis='Z'` 导入 OBJ，保留 MU 的 Z 向上坐标，关闭按 group 拆对象，得到 373 顶点、640 面的单个对象。图片打包进新 `.blend`。不要再叠加一次自动轴旋转或通过手工移动补接缝。

**静态外形复现与可动画角色是不同的交付内容。** 此步骤只复现 Corrected 的静态姿态。以后制作动画版本，应保留分件、原始 node/权重、共同 Player 骨架及动作；不能把已经烘焙的坐标再当骨骼局部坐标乘一次相同姿态。

## 仅在明确需要静态快照时使用的命令

### 从原始资源重建

```powershell
& .venv/Scripts/python.exe `
  .agents/skills/mu-art-pipeline/scripts/rebuild_dark_wizard_initial.py `
  --static-snapshot `
  --output reconstruction/dark_wizard_from_sources
```

`--output` 相对 `tools/art_pipeline/workspace/`，必须选择尚不存在的新目录。默认 `--source` 为 `src/bin/Data/Player/`。脚本生成 OBJ、MTL、JPEG、源文件快照及 `rebuild_manifest.json`；清单记录源文件 SHA-256、动作/关键帧、全部 60 根全局骨骼矩阵、各部件使用节点及边界。需要再次运行时换输出目录，例如 `reconstruction/dark_wizard_rebuild_02`。

### 新建独立 Blender 预览

```powershell
& 'D:/Blender/5.2.2/blender-5.2.2-windows-x64/blender.exe' `
  --background --factory-startup `
  --python .agents/skills/mu-art-pipeline/scripts/create_rebuilt_character_blend.py `
  -- tools/art_pipeline/workspace/reconstruction/dark_wizard_from_sources/DarkWizard_Initial_Rebuilt.obj
```

生成同名 `.blend` 和 `.png`，在独立进程中执行，不打开旧参考场景。输出已存在时拒绝覆盖。该预览脚本只适用于本案例的默认身高、姿态和镜头。

### 生成完成后只读核对

```powershell
& .venv/Scripts/python.exe `
  .agents/skills/mu-art-pipeline/scripts/verify_dark_wizard_rebuild.py `
  tools/art_pipeline/workspace/reconstruction/dark_wizard_from_sources/DarkWizard_Initial_Rebuilt.obj `
  tools/art_pipeline/workspace/Player/DarkWizard_Initial_Corrected.obj
```

比较器读取两个已经存在的文件，只比较，不生成、不修改任何几何；与重建脚本完全分开。失败时返回非零退出码。

## 本次独立复现的验证结果（2026-10-08）

- 本次生成的七个源资源快照 SHA-256 与历史 `workspace/Player/` 暂存资源逐项相同。
- 额外在 Python 运行时禁止读取任何 OBJ、Blend 或名称含 Corrected 的文件，再次从原始资源重建成功；两次生成的 OBJ 字节完全相同，SHA-256 为 `0abdae36ac4e251cd6082cc70bae31fda3e1a264e217f963705e061e5b208071`。独立性与确定性记录在同目录 `independent_repeat_report.json`。
- 新 OBJ 与 Corrected OBJ 五组共 **373 个顶点坐标逐项相同，最大误差 0**。
- 全部法线数值逐项相同，最大误差 0。
- 全部 640 个面的顶点/UV/法线索引及顺序相同。
- UV 已使用正确的 `(U,1-V)`，新旧文本最大误差约 `4.4e-8`，来自输出小数精度差异。
- 新坐标与当前 Blender 的 Corrected 对象进行只读比较，最大坐标误差约 `7.6e-6`，符合 Blender 单精度存储误差。
- 新 `.blend` 在独立进程中从新 OBJ 导入，确认仍为 373 顶点、640 面；已查看新渲染，头、躯干、裤子、手套、靴子及贴图对应正常。
- 报告位于 `workspace/reconstruction/dark_wizard_from_sources/comparison_report.json`、`live_blender_comparison.json` 和 `rebuild_manifest.json`。独立重建文件为同目录 `DarkWizard_Initial_Rebuilt.obj/.blend/.png`。

这证明已恢复用户认可的 Corrected 静态外形和纹理映射生成方法；尚未证明动画导出或客户端重新安装后的表现。

## 后续组合时的判断依据

- 五个独立 BMD 各自的 action 0 并不等于共同 Player 的同一姿态。直接拼接它们不能复现 Corrected，容易出现手臂、小腿及腰部错位。
- 共用一个骨架意味着共用同一份姿态矩阵；仅把五个对象 Join 不会自动修正各自已经采用的不同变换。
- `main_character_class01_parts.blend` 保存的是独立导入状态，不是 Corrected 的几何生成输入。
- `DarkWizard_Initial` 和 `DarkWizard_Initial_Combined` 是旧对照，不作为正确重建来源。
- 几何、UV、纹理文件选择分别验证。贴图已连接、图片已打包、UV 都在 0～1 内，均不能单独证明贴图正确。

