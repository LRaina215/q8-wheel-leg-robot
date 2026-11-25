# Q8 R5 平地动作验证

本目录提供 Q8 R5 的简化模型。轴系为 X 向前、Y 向左、Z 向上。四角各有一台髋电机和一台轮电机。

| 文件 | 用途 |
|---|---|
| q8_r5.urdf | ROS 运动学模型。每角由 hip 驱动，follower 按 +1、carrier 按 −1 模仿同角髋关节，wheel 单独转动。导入器需支持 mimic。|
| q8_r5.xml | MuJoCo 平地动力学模型。车身自由浮动，每角的被动杆与轮架在 D 销处用 connect 约束闭合。|
| pilot.py | 核对两个模型在五组 CAD 姿态的轮心位置，按六组增益整定 PD 控制器，测试平地动作。|
| pilot_results.json | 本机 MuJoCo 3.6.0 实际运行记录。|
| build_model.py | 在项目目录中从 R5 单腿尺寸与质量数据重新生成两份模型。|

## 复现

在有 Python、NumPy 和 mujoco==3.6.0 的环境中运行以下命令。两个模型和 pilot.py 可以复制到同一新目录运行，无需安装 SolidWorks。脚本将结果写入指定文件。

```sh
python pilot.py --output my_results.json
```

## 模型假设

- 髋安装点前后各 112 mm、左右各 119 mm，连杆长 110 mm，两基铰相距 62 mm。每侧轮心在对应髋轴平面外侧 86 mm。轮胎 Ø100 × 35 mm。
- 6.0 kg 是设计工况，6.6 kg 是在同一车身增重 0.6 kg 的敏感性工况。巡航质心取前一轮质量表作先验。腿的分组质量来自项目估算，370 g 髋电机中暂分 20 g 给输出法兰；分组转动惯量以零件包络近似，车身惯量以等效长方体近似。未单独模拟电池晃动、齿隙和胎体压缩。
- 地面可与四个轮胎及简化底板接触。杆件几何用于显示。这个模型用于平地和轮子离地判断，尚未包含台阶与轮架、雷达支架等的实物碰撞外形。
- 控制律运行于 2 ms 仿真步长。髋采用项目 22.2 V 扭矩速度估算包络，轮端用 1 N·m 控制上限并随转速降额。回馈、电源瞬态、轮胎受载和实际驱控时延需另行标定。
- 六组髋 PD 增益只在 6.0 kg 平地下蹲上选取；同一参数用于站立、前进、增重倒车、增重下蹲及单轮收起。此次没有训练 PPO 神经网络策略。接地轮数按地面接触距离判断，没有规定最低承重。
- 单轮收起时，仅左前髋从 −7° 收到 −27°，其余三髋维持 −7°。结果文件分别记录保持段净空、保持段三轮接地比例、整个采样过程中最少接地轮数。轮子能离开平地，并不能单独推导出同等高度的台阶通过能力。

运动学尺寸来自项目 `source/common.py` 和 `source/corner/source/design.py`。质量估算见 `source/corner/source/engineering.py` 与 `data/analysis.json`。闭环约束与轮电机参数可查 [MuJoCo connect 文档](https://mujoco.readthedocs.io/en/stable/XMLreference.html#equality-connect) 和 [DFRobot FIT0403 规格](https://wiki.dfrobot.com/fit0403)。

