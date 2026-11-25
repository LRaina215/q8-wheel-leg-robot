# Q8 R5 四轮足机器人

本仓库保存 8 执行器轮足车的可编辑 SolidWorks 总装、A1 打印件、整车载荷和线束设计，以及用于台阶、跳跃、行驶和恢复动作的 MuJoCo 模型、训练代码、权重和验收记录。

## 打开整车

将仓库克隆到本地，保留目录结构。在 SolidWorks 中打开 [交付总装](交付/SolidWorks/Q8R5_Q8_R5_整车.SLDASM)，选择 `Motion` 配置审阅装配与运动。固定方式、姿态配置和可选件见[装配与运动审阅说明](交付/审阅与装配说明.md)。[整车交互审阅](交付/R5_装配与运动审阅.html)可在本地浏览器打开。[A1 打印网格](交付/A1_STL)和[线束裁线表](交付/R5_线束裁线.csv)随总装交付。

| 目录 | 内容 |
| --- | --- |
| [交付/SolidWorks](交付/SolidWorks) 和 [source](source) | 可编辑的工程零件与装配、结构生成和检验脚本。部分原始建模脚本使用 Windows 上的 SolidWorks、原零件库或早期版本路径。 |
| [data](data) | 采购选型、质量与质心、轮架净距、配合和布线检查。 |
| [simulation](simulation) | [装车惯量 URDF](simulation/q8_r5_fitted.urdf)、MuJoCo 闭环模型、PPO 训练、动作回放与逐工况验收。 |
| [simulation/training_runs](simulation/training_runs) | 训练代码、模型配置、用于推理的最佳 ONNX 和最佳训练检查点。原目录名用于定位关联模型与权重。 |

## 复现 15 厘米台阶动作

在 Linux 环境中安装[训练依赖](simulation/requirements-training.txt)。版本来自原服务器的 Python 3.13 环境。以下命令从仓库根目录执行。

```bash
python -m pip install -r simulation/requirements-training.txt
python simulation/replay_step.py
```

默认回放双后腿同步蹬伸并收腿的样本（种子 `4619281`、工况 `0`、编号 `6`）。程序从平地重新仿真并输出 JSON。可加 `--mode direct` 改为后腿保持伸展、调整轮速后交替上台。两种模式都加载原接近及攀爬 ONNX 策略，最后阶段还使用接触与轮位反馈控制。

四批共 96 个起点中，保持后腿伸展后交替收腿有 21 次上台并站稳。双后腿同步收腿实际触发 29 次，其中 1 次由该动作完成。侧板接触与连杆闭合误差仍超过当前机械验收门槛。实机尚待验证。

## PPO 训练与权重

[分阶段攀爬 PPO 训练脚本](simulation/training_runs/stage-climb-y1o529Z5/code/stage_ppo.py)和[归档运行配置](simulation/training_runs/stage-climb-y1o529Z5/phase/run_spec.json)对应 224 个并行环境、650 次更新的训练。要在有 CUDA 的 Linux 机器上新开一轮，从仓库根目录执行以下命令。输出写入 `runs/step-phase`，同一目录已有最近检查点时训练脚本会尝试续训。

```bash
repo_root="$(pwd)"
mkdir -p runs/step-phase
cd runs/step-phase
STAGE_MODE=phase python "$repo_root/simulation/training_runs/stage-climb-y1o529Z5/code/stage_ppo.py" train soft_up --variant 0 --seed 5112502 --worlds 224 --updates 650
```

[攀爬策略权重与检查点](simulation/training_runs/stage-climb-y1o529Z5/phase)、[跳跃训练](simulation/training_runs/ppo-highjump-fUGFdEDX)和[多动作训练](simulation/training_runs/overnight-skills-nUArgHB3)分别保留各自的任务与结果口径。原仿真验收与质量估算说明见[训练模型与验收](simulation/训练模型与验收.md)。
