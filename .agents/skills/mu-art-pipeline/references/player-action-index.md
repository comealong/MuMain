# Player 动作编号对照表（当前资源：284 个动作）

编号从 0 开始，直接对应 Player.bmd 的动作数组以及 Blender Action 的 `mu_bmd_action_index`。

## 提取依据与含义

- 枚举来源：`src/source/Core/Globals/_enum.h` 的 `PLAYER_SET` 至 `MAX_PLAYER_ACTION`。
- 当前 BMD 有 284 个动作；匹配配置为 `YDG_ADD_SKILL_RIDING_ANIMATIONS=False`。当前源码关闭宏时为 284 个动作，开启时为 290 个；开启会使原来的 186 号及之后的动作编号增加 6。
- 74 号 `PLAYER_FLY_RIDE` 与分段标记 `PLAYER_ATTACK_END` 同值，不能给标记另加一个编号。
- **源码枚举名及编号为确定映射；中文说明按英文命名直译，不能当作官方中文技能名称或逐帧视觉确认。** 同一动画可能被多个技能共用。
- 这些是整个 Player 的公共动作集合，包含其它职业、武器、骑乘和表情；不表示 Dark Wizard 能在游戏中使用全部动作。
- `UNKNOWN` 等源码名称没有更具体的动作定义，保留原名；`SET` 是 0 号设置/初始姿态条目。
- 关键帧数来自当前 BMD。Blender 第 1 帧对应关键帧索引 0；帧数不等于播放秒数。

## 重新提取

```powershell
& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/extract_player_actions.py
```

JSON/Markdown 输出到 `tools/art_pipeline/workspace/catalogs/`。加 `--update-skill` 会同步更新本 Skill 的 `references/player-action-index.md`。生成器根据 BMD 动作数量选择匹配的枚举配置，保留别名和源码行号。

## 常见动作速查

| 编号 | 源码名称 | 含义（直译） |
| ---: | --- | --- |
| 0 | `PLAYER_SET` | 设置/初始姿态 |
| 1 | `PLAYER_STOP_MALE` | 站立/待机 / 男性 |
| 2 | `PLAYER_STOP_FEMALE` | 站立/待机 / 女性 |
| 15 | `PLAYER_WALK_MALE` | 行走 / 男性 |
| 25 | `PLAYER_RUN` | 奔跑 |
| 38 | `PLAYER_ATTACK_FIST` | 攻击 / 拳击 |
| 146 | `PLAYER_SKILL_HAND1` | 技能动作 / 手部施法 / 1 |
| 147 | `PLAYER_SKILL_HAND2` | 技能动作 / 手部施法 / 2 |
| 151 | `PLAYER_SKILL_TELEPORT` | 技能动作 / 瞬移 |
| 187 | `PLAYER_GREETING1` | 问候 / 1 |
| 230 | `PLAYER_SHOCK` | 受击 |
| 231 | `PLAYER_DIE1` | 死亡 / 1 |
| 233 | `PLAYER_SIT1` | 坐下 / 1 |
| 245 | `PLAYER_CHANGE_UP` | 转职/变身动作 |
| 283 | `PLAYER_STOP_RAGEFIGHTER` | 站立/待机 / Rage Fighter 职业 |

## 分类导航（当前 284 动作配置）

| 编号范围 | 动作类别 |
| --- | --- |
| 0 | 设置/初始姿态 |
| 1–14 | 站立、持武器与骑乘待机 |
| 15–37 | 行走、奔跑、游泳、飞行 |
| 38–73 | 拳击、武器攻击及部分技能 |
| 74–129 | 骑乘、Dark Lord、黑马与 Fenrir 变体 |
| 130–145 | 上射、特殊攻击及第二套双手剑动作 |
| 146–185 | 通用施法、专用技能及骑乘变体 |
| 186–229 | 防御、表情、社交、舞蹈、起身 |
| 230–246 | 受击、死亡、坐姿、休息、活动与变身动作 |
| 247–283 | Rage Fighter 技能、骑乘变体及待机 |

完整表可按编号或 `PLAYER_` 名称搜索。所有编号均为 BMD 原始索引，不是 Blender 时间帧号。

## 完整对照

| 编号 | 源码枚举名称 | 可读含义（直译） | 关键帧数 |
| ---: | --- | --- | ---: |
| 0 | `PLAYER_SET` | 设置/初始姿态 | 3 |
| 1 | `PLAYER_STOP_MALE` | 站立/待机 / 男性 | 6 |
| 2 | `PLAYER_STOP_FEMALE` | 站立/待机 / 女性 | 6 |
| 3 | `PLAYER_STOP_SUMMONER` | 站立/待机 / 召唤师 | 8 |
| 4 | `PLAYER_STOP_SWORD` | 站立/待机 / 剑 | 7 |
| 5 | `PLAYER_STOP_TWO_HAND_SWORD` | 站立/待机 / 双手剑 | 6 |
| 6 | `PLAYER_STOP_SPEAR` | 站立/待机 / 矛 | 6 |
| 7 | `PLAYER_STOP_SCYTHE` | 站立/待机 / 镰刀 | 6 |
| 8 | `PLAYER_STOP_BOW` | 站立/待机 / 弓 | 7 |
| 9 | `PLAYER_STOP_CROSSBOW` | 站立/待机 / 弩 | 6 |
| 10 | `PLAYER_STOP_WAND` | 站立/待机 / 法杖 | 9 |
| 11 | `PLAYER_STOP_FLY` | 站立/待机 / 飞行 | 6 |
| 12 | `PLAYER_STOP_FLY_CROSSBOW` | 站立/待机 / 飞行 / 弩 | 6 |
| 13 | `PLAYER_STOP_RIDE` | 站立/待机 / 骑乘 | 6 |
| 14 | `PLAYER_STOP_RIDE_WEAPON` | 站立/待机 / 骑乘 / 持武器 | 6 |
| 15 | `PLAYER_WALK_MALE` | 行走 / 男性 | 7 |
| 16 | `PLAYER_WALK_FEMALE` | 行走 / 女性 | 7 |
| 17 | `PLAYER_WALK_SWORD` | 行走 / 剑 | 7 |
| 18 | `PLAYER_WALK_TWO_HAND_SWORD` | 行走 / 双手剑 | 7 |
| 19 | `PLAYER_WALK_SPEAR` | 行走 / 矛 | 7 |
| 20 | `PLAYER_WALK_SCYTHE` | 行走 / 镰刀 | 7 |
| 21 | `PLAYER_WALK_BOW` | 行走 / 弓 | 7 |
| 22 | `PLAYER_WALK_CROSSBOW` | 行走 / 弩 | 7 |
| 23 | `PLAYER_WALK_WAND` | 行走 / 法杖 | 8 |
| 24 | `PLAYER_WALK_SWIM` | 行走 / 游泳 | 7 |
| 25 | `PLAYER_RUN` | 奔跑 | 7 |
| 26 | `PLAYER_RUN_SWORD` | 奔跑 / 剑 | 7 |
| 27 | `PLAYER_RUN_TWO_SWORD` | 奔跑 / 双剑 | 7 |
| 28 | `PLAYER_RUN_TWO_HAND_SWORD` | 奔跑 / 双手剑 | 7 |
| 29 | `PLAYER_RUN_SPEAR` | 奔跑 / 矛 | 7 |
| 30 | `PLAYER_RUN_BOW` | 奔跑 / 弓 | 7 |
| 31 | `PLAYER_RUN_CROSSBOW` | 奔跑 / 弩 | 7 |
| 32 | `PLAYER_RUN_WAND` | 奔跑 / 法杖 | 12 |
| 33 | `PLAYER_RUN_SWIM` | 奔跑 / 游泳 | 7 |
| 34 | `PLAYER_FLY` | 飞行 | 6 |
| 35 | `PLAYER_FLY_CROSSBOW` | 飞行 / 弩 | 6 |
| 36 | `PLAYER_RUN_RIDE` | 奔跑 / 骑乘 | 7 |
| 37 | `PLAYER_RUN_RIDE_WEAPON` | 奔跑 / 骑乘 / 持武器 | 7 |
| 38 | `PLAYER_ATTACK_FIST` | 攻击 / 拳击 | 7 |
| 39 | `PLAYER_ATTACK_SWORD_RIGHT1` | 攻击 / 剑 / 右手 / 1 | 7 |
| 40 | `PLAYER_ATTACK_SWORD_RIGHT2` | 攻击 / 剑 / 右手 / 2 | 7 |
| 41 | `PLAYER_ATTACK_SWORD_LEFT1` | 攻击 / 剑 / 左手 / 1 | 7 |
| 42 | `PLAYER_ATTACK_SWORD_LEFT2` | 攻击 / 剑 / 左手 / 2 | 7 |
| 43 | `PLAYER_ATTACK_TWO_HAND_SWORD1` | 攻击 / 双手剑 / 1 | 7 |
| 44 | `PLAYER_ATTACK_TWO_HAND_SWORD2` | 攻击 / 双手剑 / 2 | 7 |
| 45 | `PLAYER_ATTACK_TWO_HAND_SWORD3` | 攻击 / 双手剑 / 3 | 7 |
| 46 | `PLAYER_ATTACK_SPEAR1` | 攻击 / 矛 / 1 | 7 |
| 47 | `PLAYER_ATTACK_SCYTHE1` | 攻击 / 镰刀 / 1 | 7 |
| 48 | `PLAYER_ATTACK_SCYTHE2` | 攻击 / 镰刀 / 2 | 7 |
| 49 | `PLAYER_ATTACK_SCYTHE3` | 攻击 / 镰刀 / 3 | 7 |
| 50 | `PLAYER_ATTACK_BOW` | 攻击 / 弓 | 7 |
| 51 | `PLAYER_ATTACK_CROSSBOW` | 攻击 / 弩 | 7 |
| 52 | `PLAYER_ATTACK_FLY_BOW` | 攻击 / 飞行 / 弓 | 7 |
| 53 | `PLAYER_ATTACK_FLY_CROSSBOW` | 攻击 / 飞行 / 弩 | 7 |
| 54 | `PLAYER_ATTACK_RIDE_SWORD` | 攻击 / 骑乘 / 剑 | 7 |
| 55 | `PLAYER_ATTACK_RIDE_TWO_HAND_SWORD` | 攻击 / 骑乘 / 双手剑 | 7 |
| 56 | `PLAYER_ATTACK_RIDE_SPEAR` | 攻击 / 骑乘 / 矛 | 7 |
| 57 | `PLAYER_ATTACK_RIDE_SCYTHE` | 攻击 / 骑乘 / 镰刀 | 7 |
| 58 | `PLAYER_ATTACK_RIDE_BOW` | 攻击 / 骑乘 / 弓 | 7 |
| 59 | `PLAYER_ATTACK_RIDE_CROSSBOW` | 攻击 / 骑乘 / 弩 | 7 |
| 60 | `PLAYER_ATTACK_SKILL_SWORD1` | 攻击 / 技能动作 / 剑 / 1 | 8 |
| 61 | `PLAYER_ATTACK_SKILL_SWORD2` | 攻击 / 技能动作 / 剑 / 2 | 7 |
| 62 | `PLAYER_ATTACK_SKILL_SWORD3` | 攻击 / 技能动作 / 剑 / 3 | 7 |
| 63 | `PLAYER_ATTACK_SKILL_SWORD4` | 攻击 / 技能动作 / 剑 / 4 | 7 |
| 64 | `PLAYER_ATTACK_SKILL_SWORD5` | 攻击 / 技能动作 / 剑 / 5 | 7 |
| 65 | `PLAYER_ATTACK_SKILL_WHEEL` | 攻击 / 技能动作 / 回旋攻击 | 13 |
| 66 | `PLAYER_ATTACK_SKILL_FURY_STRIKE` | 攻击 / 技能动作 / 怒击 | 11 |
| 67 | `PLAYER_SKILL_VITALITY` | 技能动作 / 生命强化 | 11 |
| 68 | `PLAYER_SKILL_RIDER` | 技能动作 / 骑乘技能 | 7 |
| 69 | `PLAYER_SKILL_RIDER_FLY` | 技能动作 / 骑乘技能 / 飞行 | 7 |
| 70 | `PLAYER_ATTACK_SKILL_SPEAR` | 攻击 / 技能动作 / 矛 | 9 |
| 71 | `PLAYER_ATTACK_DEATHSTAB` | 攻击 / 致命刺击 | 7 |
| 72 | `PLAYER_SKILL_HELL_BEGIN` | 技能动作 / 地狱系施法 / 准备 | 5 |
| 73 | `PLAYER_SKILL_HELL_START` | 技能动作 / 地狱系施法 / 起手 | 7 |
| 74 | `PLAYER_FLY_RIDE（别名：PLAYER_ATTACK_END）` | 飞行 / 骑乘 | 7 |
| 75 | `PLAYER_FLY_RIDE_WEAPON` | 飞行 / 骑乘 / 持武器 | 8 |
| 76 | `PLAYER_DARKLORD_STAND` | Dark Lord 职业 / 站立 | 6 |
| 77 | `PLAYER_DARKLORD_WALK` | Dark Lord 职业 / 行走 | 7 |
| 78 | `PLAYER_STOP_RIDE_HORSE` | 站立/待机 / 骑乘 / 马 | 6 |
| 79 | `PLAYER_RUN_RIDE_HORSE` | 奔跑 / 骑乘 / 马 | 6 |
| 80 | `PLAYER_ATTACK_STRIKE` | 攻击 / 打击 | 7 |
| 81 | `PLAYER_ATTACK_TELEPORT` | 攻击 / 瞬移 | 8 |
| 82 | `PLAYER_ATTACK_RIDE_STRIKE` | 攻击 / 骑乘 / 打击 | 6 |
| 83 | `PLAYER_ATTACK_RIDE_TELEPORT` | 攻击 / 骑乘 / 瞬移 | 9 |
| 84 | `PLAYER_ATTACK_RIDE_HORSE_SWORD` | 攻击 / 骑乘 / 马 / 剑 | 7 |
| 85 | `PLAYER_ATTACK_RIDE_ATTACK_FLASH` | 攻击 / 骑乘 / 攻击 / 闪光施法 | 7 |
| 86 | `PLAYER_ATTACK_RIDE_ATTACK_MAGIC` | 攻击 / 骑乘 / 攻击 / 施法 | 7 |
| 87 | `PLAYER_ATTACK_DARKHORSE` | 攻击 / 黑马 | 11 |
| 88 | `PLAYER_IDLE1_DARKHORSE` | 待机变体 / 1 / 黑马 | 51 |
| 89 | `PLAYER_IDLE2_DARKHORSE` | 待机变体 / 2 / 黑马 | 31 |
| 90 | `PLAYER_FENRIR_ATTACK` | 芬里尔坐骑 / 攻击 | 7 |
| 91 | `PLAYER_FENRIR_ATTACK_DARKLORD_AQUA` | 芬里尔坐骑 / 攻击 / Dark Lord 职业 / 水系施法 | 7 |
| 92 | `PLAYER_FENRIR_ATTACK_DARKLORD_STRIKE` | 芬里尔坐骑 / 攻击 / Dark Lord 职业 / 打击 | 7 |
| 93 | `PLAYER_FENRIR_ATTACK_DARKLORD_SWORD` | 芬里尔坐骑 / 攻击 / Dark Lord 职业 / 剑 | 7 |
| 94 | `PLAYER_FENRIR_ATTACK_DARKLORD_TELEPORT` | 芬里尔坐骑 / 攻击 / Dark Lord 职业 / 瞬移 | 7 |
| 95 | `PLAYER_FENRIR_ATTACK_DARKLORD_FLASH` | 芬里尔坐骑 / 攻击 / Dark Lord 职业 / 闪光施法 | 8 |
| 96 | `PLAYER_FENRIR_ATTACK_TWO_SWORD` | 芬里尔坐骑 / 攻击 / 双剑 | 7 |
| 97 | `PLAYER_FENRIR_ATTACK_MAGIC` | 芬里尔坐骑 / 攻击 / 施法 | 7 |
| 98 | `PLAYER_FENRIR_ATTACK_CROSSBOW` | 芬里尔坐骑 / 攻击 / 弩 | 7 |
| 99 | `PLAYER_FENRIR_ATTACK_SPEAR` | 芬里尔坐骑 / 攻击 / 矛 | 7 |
| 100 | `PLAYER_FENRIR_ATTACK_ONE_SWORD` | 芬里尔坐骑 / 攻击 / 单剑 | 7 |
| 101 | `PLAYER_FENRIR_ATTACK_BOW` | 芬里尔坐骑 / 攻击 / 弓 | 7 |
| 102 | `PLAYER_FENRIR_SKILL` | 芬里尔坐骑 / 技能动作 | 13 |
| 103 | `PLAYER_FENRIR_SKILL_TWO_SWORD` | 芬里尔坐骑 / 技能动作 / 双剑 | 13 |
| 104 | `PLAYER_FENRIR_SKILL_ONE_RIGHT` | 芬里尔坐骑 / 技能动作 / 右手单持 | 13 |
| 105 | `PLAYER_FENRIR_SKILL_ONE_LEFT` | 芬里尔坐骑 / 技能动作 / 左手单持 | 13 |
| 106 | `PLAYER_FENRIR_DAMAGE` | 芬里尔坐骑 / 受伤 | 6 |
| 107 | `PLAYER_FENRIR_DAMAGE_TWO_SWORD` | 芬里尔坐骑 / 受伤 / 双剑 | 6 |
| 108 | `PLAYER_FENRIR_DAMAGE_ONE_RIGHT` | 芬里尔坐骑 / 受伤 / 右手单持 | 6 |
| 109 | `PLAYER_FENRIR_DAMAGE_ONE_LEFT` | 芬里尔坐骑 / 受伤 / 左手单持 | 6 |
| 110 | `PLAYER_FENRIR_RUN` | 芬里尔坐骑 / 奔跑 | 13 |
| 111 | `PLAYER_FENRIR_RUN_TWO_SWORD` | 芬里尔坐骑 / 奔跑 / 双剑 | 13 |
| 112 | `PLAYER_FENRIR_RUN_ONE_RIGHT` | 芬里尔坐骑 / 奔跑 / 右手单持 | 13 |
| 113 | `PLAYER_FENRIR_RUN_ONE_LEFT` | 芬里尔坐骑 / 奔跑 / 左手单持 | 13 |
| 114 | `PLAYER_FENRIR_RUN_MAGOM` | 芬里尔坐骑 / 奔跑 / 魔剑士 | 13 |
| 115 | `PLAYER_FENRIR_RUN_TWO_SWORD_MAGOM` | 芬里尔坐骑 / 奔跑 / 双剑 / 魔剑士 | 13 |
| 116 | `PLAYER_FENRIR_RUN_ONE_RIGHT_MAGOM` | 芬里尔坐骑 / 奔跑 / 右手单持 / 魔剑士 | 13 |
| 117 | `PLAYER_FENRIR_RUN_ONE_LEFT_MAGOM` | 芬里尔坐骑 / 奔跑 / 左手单持 / 魔剑士 | 13 |
| 118 | `PLAYER_FENRIR_RUN_ELF` | 芬里尔坐骑 / 奔跑 / 精灵/弓箭手 | 13 |
| 119 | `PLAYER_FENRIR_RUN_TWO_SWORD_ELF` | 芬里尔坐骑 / 奔跑 / 双剑 / 精灵/弓箭手 | 13 |
| 120 | `PLAYER_FENRIR_RUN_ONE_RIGHT_ELF` | 芬里尔坐骑 / 奔跑 / 右手单持 / 精灵/弓箭手 | 13 |
| 121 | `PLAYER_FENRIR_RUN_ONE_LEFT_ELF` | 芬里尔坐骑 / 奔跑 / 左手单持 / 精灵/弓箭手 | 13 |
| 122 | `PLAYER_FENRIR_STAND` | 芬里尔坐骑 / 站立 | 11 |
| 123 | `PLAYER_FENRIR_STAND_TWO_SWORD` | 芬里尔坐骑 / 站立 / 双剑 | 11 |
| 124 | `PLAYER_FENRIR_STAND_ONE_RIGHT` | 芬里尔坐骑 / 站立 / 右手单持 | 11 |
| 125 | `PLAYER_FENRIR_STAND_ONE_LEFT` | 芬里尔坐骑 / 站立 / 左手单持 | 11 |
| 126 | `PLAYER_FENRIR_WALK` | 芬里尔坐骑 / 行走 | 20 |
| 127 | `PLAYER_FENRIR_WALK_TWO_SWORD` | 芬里尔坐骑 / 行走 / 双剑 | 20 |
| 128 | `PLAYER_FENRIR_WALK_ONE_RIGHT` | 芬里尔坐骑 / 行走 / 右手单持 | 20 |
| 129 | `PLAYER_FENRIR_WALK_ONE_LEFT` | 芬里尔坐骑 / 行走 / 左手单持 | 20 |
| 130 | `PLAYER_ATTACK_BOW_UP` | 攻击 / 弓 / 向上 | 7 |
| 131 | `PLAYER_ATTACK_CROSSBOW_UP` | 攻击 / 弩 / 向上 | 7 |
| 132 | `PLAYER_ATTACK_FLY_BOW_UP` | 攻击 / 飞行 / 弓 / 向上 | 7 |
| 133 | `PLAYER_ATTACK_FLY_CROSSBOW_UP` | 攻击 / 飞行 / 弩 / 向上 | 7 |
| 134 | `PLAYER_ATTACK_RIDE_BOW_UP` | 攻击 / 骑乘 / 弓 / 向上 | 7 |
| 135 | `PLAYER_ATTACK_RIDE_CROSSBOW_UP` | 攻击 / 骑乘 / 弩 / 向上 | 7 |
| 136 | `PLAYER_ATTACK_ONE_FLASH` | 攻击 / 单次闪击 | 11 |
| 137 | `PLAYER_ATTACK_RUSH` | 攻击 / 冲击 | 7 |
| 138 | `PLAYER_ATTACK_DEATH_CANNON` | 攻击 / 死亡炮击 | 7 |
| 139 | `PLAYER_ATTACK_REMOVAL` | 攻击 / 消除效果 | 11 |
| 140 | `PLAYER_ATTACK_STUN` | 攻击 / 眩晕攻击 | 7 |
| 141 | `PLAYER_HIGH_SHOCK` | 强受击 | 14 |
| 142 | `PLAYER_STOP_TWO_HAND_SWORD_TWO` | 站立/待机 / 双手剑 / 第二套变体 | 7 |
| 143 | `PLAYER_WALK_TWO_HAND_SWORD_TWO` | 行走 / 双手剑 / 第二套变体 | 7 |
| 144 | `PLAYER_RUN_TWO_HAND_SWORD_TWO` | 奔跑 / 双手剑 / 第二套变体 | 7 |
| 145 | `PLAYER_ATTACK_TWO_HAND_SWORD_TWO` | 攻击 / 双手剑 / 第二套变体 | 7 |
| 146 | `PLAYER_SKILL_HAND1` | 技能动作 / 手部施法 / 1 | 6 |
| 147 | `PLAYER_SKILL_HAND2` | 技能动作 / 手部施法 / 2 | 6 |
| 148 | `PLAYER_SKILL_WEAPON1` | 技能动作 / 持武器 / 1 | 6 |
| 149 | `PLAYER_SKILL_WEAPON2` | 技能动作 / 持武器 / 2 | 6 |
| 150 | `PLAYER_SKILL_ELF1` | 技能动作 / 精灵/弓箭手 / 1 | 6 |
| 151 | `PLAYER_SKILL_TELEPORT` | 技能动作 / 瞬移 | 7 |
| 152 | `PLAYER_SKILL_FLASH` | 技能动作 / 闪光施法 | 13 |
| 153 | `PLAYER_SKILL_INFERNO` | 技能动作 / 烈焰系施法 | 13 |
| 154 | `PLAYER_SKILL_HELL` | 技能动作 / 地狱系施法 | 18 |
| 155 | `PLAYER_RIDE_SKILL` | 骑乘 / 技能动作 | 7 |
| 156 | `PLAYER_SKILL_SLEEP` | 技能动作 / 睡眠 | 13 |
| 157 | `PLAYER_SKILL_SLEEP_UNI` | 技能动作 / 睡眠 / 独角兽坐骑 | 13 |
| 158 | `PLAYER_SKILL_SLEEP_DINO` | 技能动作 / 睡眠 / Dinorant 坐骑 | 13 |
| 159 | `PLAYER_SKILL_SLEEP_FENRIR` | 技能动作 / 睡眠 / 芬里尔坐骑 | 13 |
| 160 | `PLAYER_SKILL_CHAIN_LIGHTNING` | 技能动作 / 连锁闪电 | 5 |
| 161 | `PLAYER_SKILL_CHAIN_LIGHTNING_UNI` | 技能动作 / 连锁闪电 / 独角兽坐骑 | 4 |
| 162 | `PLAYER_SKILL_CHAIN_LIGHTNING_DINO` | 技能动作 / 连锁闪电 / Dinorant 坐骑 | 4 |
| 163 | `PLAYER_SKILL_CHAIN_LIGHTNING_FENRIR` | 技能动作 / 连锁闪电 / 芬里尔坐骑 | 4 |
| 164 | `PLAYER_SKILL_LIGHTNING_ORB` | 技能动作 / 闪电球 | 11 |
| 165 | `PLAYER_SKILL_LIGHTNING_ORB_UNI` | 技能动作 / 闪电球 / 独角兽坐骑 | 5 |
| 166 | `PLAYER_SKILL_LIGHTNING_ORB_DINO` | 技能动作 / 闪电球 / Dinorant 坐骑 | 5 |
| 167 | `PLAYER_SKILL_LIGHTNING_ORB_FENRIR` | 技能动作 / 闪电球 / 芬里尔坐骑 | 5 |
| 168 | `PLAYER_SKILL_DRAIN_LIFE` | 技能动作 / 吸取生命 | 6 |
| 169 | `PLAYER_SKILL_DRAIN_LIFE_UNI` | 技能动作 / 吸取生命 / 独角兽坐骑 | 7 |
| 170 | `PLAYER_SKILL_DRAIN_LIFE_DINO` | 技能动作 / 吸取生命 / Dinorant 坐骑 | 7 |
| 171 | `PLAYER_SKILL_DRAIN_LIFE_FENRIR` | 技能动作 / 吸取生命 / 芬里尔坐骑 | 7 |
| 172 | `PLAYER_SKILL_SUMMON` | 技能动作 / 召唤 | 11 |
| 173 | `PLAYER_SKILL_SUMMON_UNI` | 技能动作 / 召唤 / 独角兽坐骑 | 11 |
| 174 | `PLAYER_SKILL_SUMMON_DINO` | 技能动作 / 召唤 / Dinorant 坐骑 | 11 |
| 175 | `PLAYER_SKILL_SUMMON_FENRIR` | 技能动作 / 召唤 / 芬里尔坐骑 | 11 |
| 176 | `PLAYER_SKILL_BLOW_OF_DESTRUCTION` | 技能动作 / 毁灭打击 | 11 |
| 177 | `PLAYER_SKILL_SWELL_OF_MP` | 技能动作 / 魔力提升 | 5 |
| 178 | `PLAYER_SKILL_MULTISHOT_BOW_STAND` | 技能动作 / 多重射击 / 弓 / 站立 | 4 |
| 179 | `PLAYER_SKILL_MULTISHOT_BOW_FLYING` | 技能动作 / 多重射击 / 弓 / 飞行中 | 4 |
| 180 | `PLAYER_SKILL_MULTISHOT_CROSSBOW_STAND` | 技能动作 / 多重射击 / 弩 / 站立 | 4 |
| 181 | `PLAYER_SKILL_MULTISHOT_CROSSBOW_FLYING` | 技能动作 / 多重射击 / 弩 / 飞行中 | 4 |
| 182 | `PLAYER_SKILL_RECOVERY` | 技能动作 / 恢复 | 5 |
| 183 | `PLAYER_SKILL_GIGANTICSTORM` | 技能动作 / 巨型风暴 | 13 |
| 184 | `PLAYER_SKILL_FLAMESTRIKE` | 技能动作 / 火焰打击 | 14 |
| 185 | `PLAYER_SKILL_LIGHTNING_SHOCK` | 技能动作 / 闪电冲击 | 11 |
| 186 | `PLAYER_DEFENSE1` | 防御 / 1 | 6 |
| 187 | `PLAYER_GREETING1` | 问候 / 1 | 13 |
| 188 | `PLAYER_GREETING_FEMALE1` | 问候 / 女性 / 1 | 13 |
| 189 | `PLAYER_GOODBYE1` | 告别 / 1 | 12 |
| 190 | `PLAYER_GOODBYE_FEMALE1` | 告别 / 女性 / 1 | 12 |
| 191 | `PLAYER_CLAP1` | 鼓掌 / 1 | 12 |
| 192 | `PLAYER_CLAP_FEMALE1` | 鼓掌 / 女性 / 1 | 12 |
| 193 | `PLAYER_CHEER1` | 欢呼 / 1 | 12 |
| 194 | `PLAYER_CHEER_FEMALE1` | 欢呼 / 女性 / 1 | 12 |
| 195 | `PLAYER_DIRECTION1` | 指示方向 / 1 | 12 |
| 196 | `PLAYER_DIRECTION_FEMALE1` | 指示方向 / 女性 / 1 | 12 |
| 197 | `PLAYER_GESTURE1` | 手势 / 1 | 12 |
| 198 | `PLAYER_GESTURE_FEMALE1` | 手势 / 女性 / 1 | 12 |
| 199 | `PLAYER_UNKNOWN1` | UNKNOWN 表情（代码未给出更具体名称） / 1 | 12 |
| 200 | `PLAYER_UNKNOWN_FEMALE1` | UNKNOWN 表情（代码未给出更具体名称） / 女性 / 1 | 12 |
| 201 | `PLAYER_CRY1` | 哭泣 / 1 | 12 |
| 202 | `PLAYER_CRY_FEMALE1` | 哭泣 / 女性 / 1 | 12 |
| 203 | `PLAYER_AWKWARD1` | 尴尬 / 1 | 12 |
| 204 | `PLAYER_AWKWARD_FEMALE1` | 尴尬 / 女性 / 1 | 12 |
| 205 | `PLAYER_SEE1` | 观看 / 1 | 12 |
| 206 | `PLAYER_SEE_FEMALE1` | 观看 / 女性 / 1 | 12 |
| 207 | `PLAYER_WIN1` | 胜利 / 1 | 13 |
| 208 | `PLAYER_WIN_FEMALE1` | 胜利 / 女性 / 1 | 13 |
| 209 | `PLAYER_SMILE1` | 微笑 / 1 | 12 |
| 210 | `PLAYER_SMILE_FEMALE1` | 微笑 / 女性 / 1 | 12 |
| 211 | `PLAYER_SLEEP1` | 睡眠 / 1 | 13 |
| 212 | `PLAYER_SLEEP_FEMALE1` | 睡眠 / 女性 / 1 | 13 |
| 213 | `PLAYER_COLD1` | 寒冷 / 1 | 13 |
| 214 | `PLAYER_COLD_FEMALE1` | 寒冷 / 女性 / 1 | 12 |
| 215 | `PLAYER_AGAIN1` | 再来一次 / 1 | 7 |
| 216 | `PLAYER_AGAIN_FEMALE1` | 再来一次 / 女性 / 1 | 7 |
| 217 | `PLAYER_RESPECT1` | 致敬 / 1 | 16 |
| 218 | `PLAYER_SALUTE1` | 敬礼 / 1 | 19 |
| 219 | `PLAYER_SCISSORS` | 猜拳：剪刀 | 8 |
| 220 | `PLAYER_ROCK` | 猜拳：石头 | 8 |
| 221 | `PLAYER_PAPER` | 猜拳：布 | 8 |
| 222 | `PLAYER_HUSTLE` | HUSTLE 舞蹈/表情 | 11 |
| 223 | `PLAYER_PROVOCATION` | 挑衅 | 27 |
| 224 | `PLAYER_LOOK_AROUND` | 环顾 | 19 |
| 225 | `PLAYER_CHEERS` | 喝彩 | 27 |
| 226 | `PLAYER_KOREA_HANDCLAP` | 韩式助威鼓掌 | 26 |
| 227 | `PLAYER_POINT_DANCE` | POINT 舞蹈 | 100 |
| 228 | `PLAYER_RUSH1` | 冲击 / 1 | 13 |
| 229 | `PLAYER_COME_UP` | 起身 | 12 |
| 230 | `PLAYER_SHOCK` | 受击 | 7 |
| 231 | `PLAYER_DIE1` | 死亡 / 1 | 30 |
| 232 | `PLAYER_DIE2` | 死亡 / 2 | 7 |
| 233 | `PLAYER_SIT1` | 坐下 / 1 | 20 |
| 234 | `PLAYER_SIT2` | 坐下 / 2 | 20 |
| 235 | `PLAYER_SIT_FEMALE1` | 坐下 / 女性 / 1 | 20 |
| 236 | `PLAYER_SIT_FEMALE2` | 坐下 / 女性 / 2 | 20 |
| 237 | `PLAYER_HEALING1` | 治疗/休息 / 1 | 6 |
| 238 | `PLAYER_HEALING_FEMALE1` | 治疗/休息 / 女性 / 1 | 6 |
| 239 | `PLAYER_POSE1` | 摆姿势 / 1 | 6 |
| 240 | `PLAYER_POSE_FEMALE1` | 摆姿势 / 女性 / 1 | 6 |
| 241 | `PLAYER_JACK_1` | Jack 活动动作 / 1 | 16 |
| 242 | `PLAYER_JACK_2` | Jack 活动动作 / 2 | 20 |
| 243 | `PLAYER_SANTA_1` | 圣诞活动动作 / 1 | 20 |
| 244 | `PLAYER_SANTA_2` | 圣诞活动动作 / 2 | 16 |
| 245 | `PLAYER_CHANGE_UP` | 转职/变身动作 | 8 |
| 246 | `PLAYER_RECOVER_SKILL` | 恢复技能动作 | 7 |
| 247 | `PLAYER_SKILL_THRUST` | 技能动作 / 突刺 | 12 |
| 248 | `PLAYER_SKILL_STAMP` | 技能动作 / 踏击 | 10 |
| 249 | `PLAYER_SKILL_GIANTSWING` | 技能动作 / 大回旋 | 15 |
| 250 | `PLAYER_SKILL_DARKSIDE_READY` | 技能动作 / Darkside 技能准备 | 13 |
| 251 | `PLAYER_SKILL_DARKSIDE_ATTACK` | 技能动作 / Darkside 技能攻击 | 1 |
| 252 | `PLAYER_SKILL_DRAGONKICK` | 技能动作 / 龙踢 | 10 |
| 253 | `PLAYER_SKILL_DRAGONLORE` | 技能动作 / Dragon Lore 技能 | 10 |
| 254 | `PLAYER_SKILL_PHOENIX_SHOT` | 技能动作 / 凤凰射击 | 10 |
| 255 | `PLAYER_SKILL_ATT_UP_OURFORCES` | 技能动作 / 我方攻击提升 | 13 |
| 256 | `PLAYER_SKILL_HP_UP_OURFORCES` | 技能动作 / 我方生命提升 | 12 |
| 257 | `PLAYER_RAGE_UNI_ATTACK` | Rage Fighter 职业 / 独角兽坐骑 / 攻击 | 7 |
| 258 | `PLAYER_RAGE_UNI_ATTACK_ONE_RIGHT` | Rage Fighter 职业 / 独角兽坐骑 / 攻击 / 右手单持 | 7 |
| 259 | `PLAYER_RAGE_UNI_RUN` | Rage Fighter 职业 / 独角兽坐骑 / 奔跑 | 4 |
| 260 | `PLAYER_RAGE_UNI_RUN_ONE_RIGHT` | Rage Fighter 职业 / 独角兽坐骑 / 奔跑 / 右手单持 | 4 |
| 261 | `PLAYER_RAGE_UNI_STOP_ONE_RIGHT` | Rage Fighter 职业 / 独角兽坐骑 / 站立/待机 / 右手单持 | 4 |
| 262 | `PLAYER_RAGE_FENRIR` | Rage Fighter 职业 / 芬里尔坐骑 | 7 |
| 263 | `PLAYER_RAGE_FENRIR_TWO_SWORD` | Rage Fighter 职业 / 芬里尔坐骑 / 双剑 | 7 |
| 264 | `PLAYER_RAGE_FENRIR_ONE_RIGHT` | Rage Fighter 职业 / 芬里尔坐骑 / 右手单持 | 7 |
| 265 | `PLAYER_RAGE_FENRIR_ONE_LEFT` | Rage Fighter 职业 / 芬里尔坐骑 / 左手单持 | 7 |
| 266 | `PLAYER_RAGE_FENRIR_WALK` | Rage Fighter 职业 / 芬里尔坐骑 / 行走 | 10 |
| 267 | `PLAYER_RAGE_FENRIR_WALK_ONE_RIGHT` | Rage Fighter 职业 / 芬里尔坐骑 / 行走 / 右手单持 | 10 |
| 268 | `PLAYER_RAGE_FENRIR_WALK_ONE_LEFT` | Rage Fighter 职业 / 芬里尔坐骑 / 行走 / 左手单持 | 10 |
| 269 | `PLAYER_RAGE_FENRIR_WALK_TWO_SWORD` | Rage Fighter 职业 / 芬里尔坐骑 / 行走 / 双剑 | 10 |
| 270 | `PLAYER_RAGE_FENRIR_RUN` | Rage Fighter 职业 / 芬里尔坐骑 / 奔跑 | 6 |
| 271 | `PLAYER_RAGE_FENRIR_RUN_TWO_SWORD` | Rage Fighter 职业 / 芬里尔坐骑 / 奔跑 / 双剑 | 6 |
| 272 | `PLAYER_RAGE_FENRIR_RUN_ONE_RIGHT` | Rage Fighter 职业 / 芬里尔坐骑 / 奔跑 / 右手单持 | 6 |
| 273 | `PLAYER_RAGE_FENRIR_RUN_ONE_LEFT` | Rage Fighter 职业 / 芬里尔坐骑 / 奔跑 / 左手单持 | 6 |
| 274 | `PLAYER_RAGE_FENRIR_STAND` | Rage Fighter 职业 / 芬里尔坐骑 / 站立 | 5 |
| 275 | `PLAYER_RAGE_FENRIR_STAND_TWO_SWORD` | Rage Fighter 职业 / 芬里尔坐骑 / 站立 / 双剑 | 5 |
| 276 | `PLAYER_RAGE_FENRIR_STAND_ONE_RIGHT` | Rage Fighter 职业 / 芬里尔坐骑 / 站立 / 右手单持 | 5 |
| 277 | `PLAYER_RAGE_FENRIR_STAND_ONE_LEFT` | Rage Fighter 职业 / 芬里尔坐骑 / 站立 / 左手单持 | 5 |
| 278 | `PLAYER_RAGE_FENRIR_DAMAGE` | Rage Fighter 职业 / 芬里尔坐骑 / 受伤 | 3 |
| 279 | `PLAYER_RAGE_FENRIR_DAMAGE_TWO_SWORD` | Rage Fighter 职业 / 芬里尔坐骑 / 受伤 / 双剑 | 3 |
| 280 | `PLAYER_RAGE_FENRIR_DAMAGE_ONE_RIGHT` | Rage Fighter 职业 / 芬里尔坐骑 / 受伤 / 右手单持 | 3 |
| 281 | `PLAYER_RAGE_FENRIR_DAMAGE_ONE_LEFT` | Rage Fighter 职业 / 芬里尔坐骑 / 受伤 / 左手单持 | 3 |
| 282 | `PLAYER_RAGE_FENRIR_ATTACK_RIGHT` | Rage Fighter 职业 / 芬里尔坐骑 / 攻击 / 右手 | 4 |
| 283 | `PLAYER_STOP_RAGEFIGHTER` | 站立/待机 / Rage Fighter 职业 | 7 |
