<p align="center">
  <img src="assets/teaser.png" alt="HatchPet 肥嘟嘟——陪伴 Codex 的金黄色桌宠" width="100%">
</p>

<p align="center">
  <strong>一只会在 Codex 工作时作出回应的快乐金黄色伙伴。</strong><br>
  <a href="README.md">English</a> · <a href="操作手册与说明.md">中文操作手册与说明</a>
</p>

# HatchPet：肥嘟嘟

> 提示：思路和源代码参考项目 https://github.com/srwang0506/HatchPet-CapybaraLulu.git

肥嘟嘟（Feidudu）是一套面向 Codex 桌面体验打造的完整桌宠。我们希望它能让漫长的编码过程多一点温度和生气，因此为它确立了鲜明而稳定的形象：金黄色梨形胖身体、两只圆润长耳、奶油色肚皮、醒目的红棕色大鼻子、明亮圆眼睛、短手、厚实双脚和一条弯曲尾巴。

这个仓库实现的并不只是一张装饰头像，而是一套完整的角色动画系统。肥嘟嘟会跟随指针方向、响应桌面交互，并在 Codex 工作、等待输入、等待审阅或任务受阻时给出清晰反应。所有动作都以真实桌宠尺寸下的辨识度为标准，活泼但不会抢走屏幕工作的注意力。

可直接安装的桌宠包位于 [`pet/`](pet/)；其中只有一份紧凑清单和一张动态 WebP 图集，不需要后台服务、网络请求或第三方可执行程序。

<p align="center">
  <img src="assets/feidudu-in-motion.png" alt="肥嘟嘟跑步、跳跃、打招呼、工作、等待与检查成果" width="100%">
</p>

## 主要特性

- 九种 Codex 原生状态：待机、向右跑、向左跑、打招呼、跳跃、受阻、等待输入、工作中、等待审阅。
- 20 个同步图像时间相位，每相位 80ms，形成无缝的 1.60 秒全局循环。
- 在原生状态内部编排了 15 段可见动作。
- 两条 Sprite V2 注视行覆盖 16 个方向。
- 透明 192 × 208 单元格，图集规格为 8 × 11、1536 × 2288。
- 提供静态 RGBA 备用图集，适合减少动态效果或调试。
- 保留完整生产图行、拆分帧、预览、验证报告和构建脚本。

## 快速开始

### 环境要求

- Windows、macOS 或 Linux
- Python 3.10 或更高版本
- 支持自定义桌宠的 ChatGPT/Codex 客户端

只有在重新构建或验证素材时才需要 Pillow：

```bash
python -m pip install -r requirements.txt
```

### 安装

在项目根目录运行：

```bash
python scripts/install.py
```

如果系统中的 Python 3 命令是 `python3`：

```bash
python3 scripts/install.py
```

安装器会：

1. 校验肥嘟嘟的 Sprite V2 清单；
2. 将已有的 `feidudu` 安装备份到 `~/.codex/backups/feidudu/`；
3. 把桌宠复制到 `~/.codex/pets/feidudu/`；
4. 除非传入 `--no-select`，否则把 `[desktop].selected-avatar-id` 设置为 `custom:feidudu`。

完全退出并重新打开桌面客户端；如未自动启用，请打开 **Settings → Pets（设置 → Pets）**，选择 **肥嘟嘟**。

只安装、不更改当前桌宠：

```bash
python scripts/install.py --no-select
```

在临时目录中测试安装、完全不触碰真实 Codex 目录：

```bash
python scripts/install.py --codex-home .tmp-codex
```

## 状态行为

| 图集行 | 原生状态 | 肥嘟嘟的动作 |
|---:|---|---|
| 0 | `idle` | 呼吸、眨眼、变换口型并轻轻回稳 |
| 1 | `running-right` | 两轮完整的向右步态 |
| 2 | `running-left` | 逐帧镜像且相位一致的向左步态 |
| 3 | `waving` | 抬起一只手向用户打招呼 |
| 4 | `jumping` | 蓄力、起跳、到达最高点并落地 |
| 5 | `failed` | 在任务受阻或失败时作出反应 |
| 6 | `waiting` | 等待用户输入并请求关注 |
| 7 | `running` | 使用固定的橙色笔记本电脑工作 |
| 8 | `review` | 在同一台笔记本电脑前等待审阅 |
| 9–10 | 指针注视 | 以 22.5° 为步进覆盖 000° 到 337.5° |

九个原生状态行共享同一个动态 WebP 时钟。进入状态不会重置时钟，因此每条状态序列都被设计为任意相位进入也能连续循环。两条注视行在所有时间帧中保持完全不变，保证指针跟随稳定。

## 动作档案

<p align="center">
  <img src="assets/all-frames.png" alt="肥嘟嘟完整同步动作档案" width="100%">
</p>

透明独立帧位于 [`assets/frames/`](assets/frames/)，同步运行相位位于 [`assets/state-phases/`](assets/state-phases/)，轻量动画预览位于 [`assets/gifs/`](assets/gifs/)。

面向维护者，仓库在 [`references/source-images/`](references/source-images/) 中保留内部美术方向档案，在 [`assets/source/`](assets/source/) 中保留生成阶段的工作图行。它们与角色规范共同保证后续动作迭代可复现、形象一致。最终采用的内置图像生成提示词集合记录在 [`references/IMAGEGEN-PROMPTS.md`](references/IMAGEGEN-PROMPTS.md)。

## Sprite V2 规格

| 属性 | 数值 |
|---|---:|
| 列数 | 8 |
| 行数 | 11 |
| 单元格 | 192 × 208 px |
| 图集 | 1536 × 2288 px |
| 运行帧数 | 20 |
| 单帧时长 | 80 ms |
| 循环时长 | 1600 ms |
| Sprite 版本 | 2 |

正式动态图集为 [`pet/spritesheet.webp`](pet/spritesheet.webp)，静态备用图集为 [`assets/spritesheet-static.webp`](assets/spritesheet-static.webp)，[`assets/state-phases.json`](assets/state-phases.json) 是打包运行文件时使用的精确相位映射。

## 减少动态效果

静态图集拥有相同的 8 × 11 几何结构，可以在不修改 `pet.json` 的情况下替换动态图集：

```bash
cp assets/spritesheet-static.webp ~/.codex/pets/feidudu/spritesheet.webp
```

PowerShell：

```powershell
Copy-Item assets\spritesheet-static.webp "$HOME\.codex\pets\feidudu\spritesheet.webp" -Force
```

替换后请重启客户端。再次运行安装器即可恢复动态版本。

## 重建与验证

仓库提供可复用的 `hatch-pet` Sprite V2 工具和肥嘟嘟专用的归一化辅助脚本。

根据已签入的静态与动态图集重建文档展示图：

```bash
python scripts/build_gallery.py
python scripts/build_readme_assets.py
```

验证静态图集：

```bash
python hatch-pet/scripts/validate_atlas.py assets/spritesheet-static.webp \
  --json-out assets/validation-static-feidudu.json --require-v2
```

验证动态图集及其精确相位映射：

```bash
python hatch-pet/scripts/validate_atlas.py pet/spritesheet.webp \
  --json-out assets/validation-runtime-feidudu.json \
  --require-v2 --allow-animated --allow-transparent-rgb-residue

python hatch-pet/scripts/validate_smooth_state_webp.py pet/spritesheet.webp \
  --source-atlas assets/spritesheet-static.webp \
  --phase-manifest assets/state-phases.json \
  --json-out assets/validation-smooth-feidudu.json \
  --require-all-states --min-motion-clips 12 --max-motion-clips 15
```

运行通用工具测试：

```bash
python -m unittest discover -s hatch-pet/tests -v
```

## 项目结构

```text
HatchPet-Feidudu-main/
├── pet/                         # 可直接安装的肥嘟嘟桌宠包
│   ├── pet.json
│   └── spritesheet.webp
├── assets/
│   ├── source/                  # 生成的色键源行与角色基准图
│   ├── frames/                  # 透明静态源帧
│   ├── state-phases/            # 每种状态的 20 个运行相位
│   ├── gifs/                    # 轻量状态预览
│   ├── runtime-previews/        # 相位表与动态 WebP 预览
│   ├── spritesheet-static.webp  # 减少动态效果/调试图集
│   └── state-phases.json        # 运行相位映射
├── references/source-images/    # 内部美术方向档案与联系表
├── hatch-pet/                   # 可复用 Sprite V2 构建和质检工具
├── scripts/                     # 肥嘟嘟构建、展示与安装脚本
├── README.md                    # 英文项目说明
├── README.zh-CN.md              # 本中文翻译
└── 操作手册与说明.md              # 详细中文用户手册
```

## 角色与贡献规则

请保持肥嘟嘟的核心轮廓和解剖结构：金黄色梨形身体、两只长耳、奶油色椭圆肚皮、超大的红棕色椭圆鼻子、圆眼睛、恰好两只手、两只脚和一条弯尾巴。默认形象不穿衣服。橙色笔记本电脑只用于工作与审阅状态；爱心属于可选表情道具，不是基础身份的一部分。

修改动作或打包逻辑前，请阅读 [`AGENTS.md`](AGENTS.md) 和 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 美术资产与分发

正式运行包与开发阶段的美术档案、生产记录彼此分离。制作最小发行包时，只需分发 [`pet/`](pet/) 和必要文档；如需连同完整开发档案发布，请先核对其中视觉材料的权利与分发范围。仓库声明见 [`NOTICE`](NOTICE)。

## 许可证

项目代码遵循 [`LICENSE`](LICENSE) 中的许可条款。视觉资产与开发材料可能适用不同权利，请在分发前阅读 [`NOTICE`](NOTICE)。
