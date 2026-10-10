"""Export the complete source-backed Player action index with readable Chinese glosses."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from mu_art_pipeline.character_sources import ROOT, WORKSPACE
from mu_art_pipeline.player_actions import extract_player_actions

TERMS = {
 'SET':'设置/初始姿态', 'STOP':'站立/待机', 'STAND':'站立', 'WALK':'行走', 'RUN':'奔跑',
 'SWIM':'游泳', 'FLY':'飞行', 'FLYING':'飞行中', 'MALE':'男性', 'FEMALE':'女性',
 'SUMMONER':'召唤师', 'DARKLORD':'Dark Lord 职业', 'RAGEFIGHTER':'Rage Fighter 职业',
 'RAGE':'Rage Fighter 职业', 'MAGOM':'魔剑士', 'ELF':'精灵/弓箭手',
 'TWO_HAND_SWORD':'双手剑', 'TWO_SWORD':'双剑', 'ONE_SWORD':'单剑',
 'SWORD':'剑', 'SPEAR':'矛', 'SCYTHE':'镰刀', 'CROSSBOW':'弩', 'BOW':'弓', 'WAND':'法杖',
 'ATTACK':'攻击', 'FIST':'拳击', 'RIGHT':'右手', 'LEFT':'左手', 'ONE_RIGHT':'右手单持',
 'ONE_LEFT':'左手单持', 'RIDE':'骑乘', 'RIDER':'骑乘技能', 'HORSE':'马', 'DARKHORSE':'黑马',
 'FENRIR':'芬里尔坐骑', 'UNI':'独角兽坐骑', 'DINO':'Dinorant 坐骑',
 'SKILL':'技能动作', 'WEAPON':'持武器', 'HAND':'手部施法', 'MAGIC':'施法',
 'WHEEL':'回旋攻击', 'FURY_STRIKE':'怒击', 'VITALITY':'生命强化', 'DEATHSTAB':'致命刺击',
 'HELL':'地狱系施法', 'INFERNO':'烈焰系施法', 'BEGIN':'准备', 'START':'起手',
 'STRIKE':'打击', 'TELEPORT':'瞬移', 'FLASH':'闪光施法', 'AQUA':'水系施法',
 'IDLE':'待机变体', 'DAMAGE':'受伤', 'UP':'向上', 'ONE_FLASH':'单次闪击', 'RUSH':'冲击',
 'DEATH_CANNON':'死亡炮击', 'REMOVAL':'消除效果', 'STUN':'眩晕攻击', 'HIGH_SHOCK':'强受击',
 'SLEEP':'睡眠', 'CHAIN_LIGHTNING':'连锁闪电', 'LIGHTNING_ORB':'闪电球', 'DRAIN_LIFE':'吸取生命',
 'SUMMON':'召唤', 'BLOW_OF_DESTRUCTION':'毁灭打击', 'SWELL_OF_MP':'魔力提升',
 'MULTISHOT':'多重射击', 'RECOVERY':'恢复', 'GIGANTICSTORM':'巨型风暴',
 'FLAMESTRIKE':'火焰打击', 'LIGHTNING_SHOCK':'闪电冲击', 'DEFENSE':'防御',
 'GREETING':'问候', 'GOODBYE':'告别', 'CLAP':'鼓掌', 'CHEER':'欢呼', 'DIRECTION':'指示方向',
 'GESTURE':'手势', 'UNKNOWN':'UNKNOWN 表情（代码未给出更具体名称）', 'CRY':'哭泣',
 'AWKWARD':'尴尬', 'SEE':'观看', 'WIN':'胜利', 'SMILE':'微笑', 'COLD':'寒冷',
 'AGAIN':'再来一次', 'RESPECT':'致敬', 'SALUTE':'敬礼', 'SCISSORS':'猜拳：剪刀',
 'ROCK':'猜拳：石头', 'PAPER':'猜拳：布', 'HUSTLE':'HUSTLE 舞蹈/表情', 'PROVOCATION':'挑衅',
 'LOOK_AROUND':'环顾', 'CHEERS':'喝彩', 'KOREA_HANDCLAP':'韩式助威鼓掌', 'POINT_DANCE':'POINT 舞蹈',
 'COME_UP':'起身', 'SHOCK':'受击', 'DIE':'死亡', 'SIT':'坐下', 'HEALING':'治疗/休息',
 'POSE':'摆姿势', 'JACK':'Jack 活动动作', 'SANTA':'圣诞活动动作', 'CHANGE_UP':'转职/变身动作',
 'RECOVER_SKILL':'恢复技能动作', 'THRUST':'突刺', 'STAMP':'踏击', 'GIANTSWING':'大回旋',
 'DARKSIDE_READY':'Darkside 技能准备', 'DARKSIDE_ATTACK':'Darkside 技能攻击',
 'DRAGONKICK':'龙踢', 'DRAGONLORE':'Dragon Lore 技能', 'PHOENIX_SHOT':'凤凰射击',
 'ATT_UP_OURFORCES':'我方攻击提升', 'HP_UP_OURFORCES':'我方生命提升', 'TWO':'第二套变体',
}


def action_gloss(name: str) -> str:
    remaining = name.removeprefix('PLAYER_')
    terms = sorted(TERMS, key=len, reverse=True)
    result = []
    while remaining:
        match = next((key for key in terms if remaining.startswith(key)
                      and (len(remaining) == len(key) or remaining[len(key)] in '_0123456789')), None)
        if match:
            result.append(TERMS[match])
            remaining = remaining[len(match):].lstrip('_')
            continue
        token = re.match(r'\d+|[^_]+', remaining).group()
        result.append(token)
        remaining = remaining[len(token):].lstrip('_')
    return ' / '.join(result)


def render_markdown(catalog: dict) -> str:
    lines = [f'# Player 动作编号对照表（当前资源：{catalog["action_count"]} 个动作）', '',
             '编号从 0 开始，直接对应 Player.bmd 的动作数组以及 Blender Action 的 `mu_bmd_action_index`。', '',
             '## 提取依据与含义', '',
             '- 枚举来源：`src/source/Core/Globals/_enum.h` 的 `PLAYER_SET` 至 `MAX_PLAYER_ACTION`。',
             f'- 当前 BMD 有 {catalog["action_count"]} 个动作；匹配配置为 `YDG_ADD_SKILL_RIDING_ANIMATIONS={catalog["defines"]["YDG_ADD_SKILL_RIDING_ANIMATIONS"]}`。当前源码关闭宏时为 284 个动作，开启时为 290 个；开启会使原来的 186 号及之后的动作编号增加 6。',
             '- 74 号 `PLAYER_FLY_RIDE` 与分段标记 `PLAYER_ATTACK_END` 同值，不能给标记另加一个编号。',
             '- **源码枚举名及编号为确定映射；中文说明按英文命名直译，不能当作官方中文技能名称或逐帧视觉确认。** 同一动画可能被多个技能共用。',
             '- 这些是整个 Player 的公共动作集合，包含其它职业、武器、骑乘和表情；不表示 Dark Wizard 能在游戏中使用全部动作。',
             '- `UNKNOWN` 等源码名称没有更具体的动作定义，保留原名；`SET` 是 0 号设置/初始姿态条目。',
             '- 关键帧数来自当前 BMD。Blender 第 1 帧对应关键帧索引 0；帧数不等于播放秒数。', '',
             '## 重新提取', '', '```powershell',
             '& .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/extract_player_actions.py',
             '```', '',
             'JSON/Markdown 仅输出到 `tools/art_pipeline/workspace/catalogs/`，不覆盖 Skill 的通用指导。生成器根据源资源选择匹配的枚举配置，保留别名和源码行号。', '',
             '## 完整对照', '', '| 编号 | 源码枚举名称 | 可读含义（直译） | 关键帧数 |',
             '| ---: | --- | --- | ---: |']
    quick = quick_reference(catalog)
    position = lines.index('## 完整对照')
    lines[position:position] = quick
    for action in catalog['actions']:
        names = action['name']
        if action['aliases']:
            names += '（别名：' + ', '.join(action['aliases']) + '）'
        lines.append(f"| {action['index']} | `{names}` | {action['gloss_zh']} | {action['keys']} |")
    return '\n'.join(lines) + '\n'



def quick_reference(catalog: dict) -> list[str]:
    common = {'PLAYER_SET', 'PLAYER_STOP_MALE', 'PLAYER_STOP_FEMALE', 'PLAYER_WALK_MALE',
              'PLAYER_RUN', 'PLAYER_ATTACK_FIST', 'PLAYER_SKILL_HAND1', 'PLAYER_SKILL_HAND2',
              'PLAYER_SKILL_TELEPORT', 'PLAYER_GREETING1', 'PLAYER_SHOCK', 'PLAYER_DIE1',
              'PLAYER_SIT1', 'PLAYER_CHANGE_UP', 'PLAYER_STOP_RAGEFIGHTER'}
    lines = ['## 常见动作速查', '', '| 编号 | 源码名称 | 含义（直译） |', '| ---: | --- | --- |']
    for action in catalog['actions']:
        if action['name'] in common:
            lines.append(f"| {action['index']} | `{action['name']}` | {action['gloss_zh']} |")
    if catalog['action_count'] != 284:
        return lines + ['', '按源码名称或编号查找下面的完整表；分类范围随编译配置变化。', '']
    lines.extend(['', '## 分类导航（当前 284 动作配置）', '',
                  '| 编号范围 | 动作类别 |', '| --- | --- |',
                  '| 0 | 设置/初始姿态 |', '| 1–14 | 站立、持武器与骑乘待机 |',
                  '| 15–37 | 行走、奔跑、游泳、飞行 |', '| 38–73 | 拳击、武器攻击及部分技能 |',
                  '| 74–129 | 骑乘、Dark Lord、黑马与 Fenrir 变体 |',
                  '| 130–145 | 上射、特殊攻击及第二套双手剑动作 |',
                  '| 146–185 | 通用施法、专用技能及骑乘变体 |',
                  '| 186–229 | 防御、表情、社交、舞蹈、起身 |',
                  '| 230–246 | 受击、死亡、坐姿、休息、活动与变身动作 |',
                  '| 247–283 | Rage Fighter 技能、骑乘变体及待机 |', '',
                  '完整表可按编号或 `PLAYER_` 名称搜索。所有编号均为 BMD 原始索引，不是 Blender 时间帧号。', ''])
    return lines


def write_catalog(catalog: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / 'player-actions.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    markdown = render_markdown(catalog)
    (output / 'player-actions.md').write_text(markdown, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--header', type=Path, default=ROOT / 'src/source/Core/Globals/_enum.h')
    parser.add_argument('--model', type=Path, default=ROOT / 'src/bin/Data/Player/player.bmd')
    parser.add_argument('--output', type=Path, default=Path('catalogs'))
    parser.add_argument('--update-skill', action='store_true',
                        help='Deprecated compatibility flag; catalogs are written only to the workspace')
    args = parser.parse_args()
    output = (WORKSPACE / args.output).resolve()
    if not output.is_relative_to(WORKSPACE.resolve()):
        raise ValueError('Catalog output must be inside the art workspace')
    catalog = extract_player_actions(args.header, args.model)
    for action in catalog['actions']:
        action['gloss_zh'] = action_gloss(action['name'])
    write_catalog(catalog, output)
    if args.update_skill:
        print('--update-skill is deprecated; resource catalogs remain in the workspace.', file=sys.stderr)
    print(json.dumps({'action_count': catalog['action_count'], 'defines': catalog['defines'],
                      'catalog_json': str(output / 'player-actions.json'),
                      'catalog_markdown': str(output / 'player-actions.md')}))


if __name__ == '__main__':
    main()
