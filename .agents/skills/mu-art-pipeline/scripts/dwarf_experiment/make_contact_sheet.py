"""Lay out the generated pose renders for visual review; no game assets are written."""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw, ImageFont

from paths import experiment_from_arguments

EXPERIMENT = experiment_from_arguments()
FONT = Path('C:/Windows/Fonts/msyh.ttc')
BACKGROUND = (23, 27, 34)
FOREGROUND = (235, 239, 245)
POSES = (
    ('standing', '持剑站立 · 动作 4 / 关键帧 0'),
    ('walk', '持剑行走 · 动作 17 / 关键帧 3'),
    ('run', '持剑奔跑 · 动作 26 / 关键帧 3'),
    ('sword_windup', '挥剑准备 · 动作 39 / 关键帧 1'),
    ('sword_swing', '挥剑中段 · 动作 39 / 关键帧 4'),
    ('sword_followthrough', '挥剑后段 · 动作 40 / 关键帧 3'),
)
HEADER_HEIGHT = 100
CAPTION_HEIGHT = 60


def labelled_pose(path, label):
    image = Image.open(path).convert('RGB')
    result = Image.new('RGB', (image.width, image.height + CAPTION_HEIGHT), BACKGROUND)
    result.paste(image, (0, CAPTION_HEIGHT))
    draw = ImageDraw.Draw(result)
    font = ImageFont.truetype(str(FONT), 26)
    draw.text((24, 12), label, font=font, fill=FOREGROUND)
    draw.text((image.width - 310, 12), '左：原角色  右：矮人', font=font, fill=FOREGROUND)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--run', default='runs/v01')
    args = parser.parse_args()
    output = (EXPERIMENT / args.run).resolve()
    if not output.is_relative_to(EXPERIMENT.resolve()):
        raise ValueError('Run must be inside the experiment')
    tiles = [labelled_pose(output / 'previews' / (name + '.png'), label) for name, label in POSES]
    width, height = tiles[0].size
    sheet = Image.new('RGB', (width * 2, height * 3 + HEADER_HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 14), '经典矮人比例试验 · 复用原动作 · 同一把原始游戏武器', font=ImageFont.truetype(str(FONT), 38), fill=FOREGROUND)
    draw.text((24, 62), '独立工作区样例；没有修改游戏资源。武器使用刚体挂接，未作非等比缩放。', font=ImageFont.truetype(str(FONT), 23), fill=FOREGROUND)
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 2) * width, HEADER_HEIGHT + (index // 2) * height))
    sheet.save(output / 'pose_comparison.png')
    tiles[0].save(output / 'standing_comparison.png')


if __name__ == '__main__':
    main()
