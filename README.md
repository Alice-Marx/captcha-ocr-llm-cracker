# 基于 OCR 与 LLM 的验证码智能破解系统

网络安全技术课程设计项目（0202-2 组）。项目用 Flask 自建了一套包含 4 个难度等级的验证码服务系统，并分别用传统 OCR（ddddocr）与多模态大模型（小米 MiMo v2.5）两条技术路线对各级验证码做自动识别测试，对比准确率与耗时，以此评估验证码方案的抗自动化识别强度。

## 验证码难度分级

| 等级 | 特点 |
|------|------|
| Level 1 | 纯文本，无视觉干扰，用于建立基准 |
| Level 2 | 10–15 个随机噪点干扰 |
| Level 3 | 字符随机旋转 15–25 度 |
| Level 4 | 渐变背景 + 随机干扰线 + 字符扭曲，模拟商业系统验证码 |

## 项目结构

```
├── captcha/                     # 源代码
│   ├── main.py                  # Flask 验证码服务（生成 / 校验 / 登录 API）
│   ├── captcha_cracker.py       # ddddocr + MiMo 大模型的自动破解脚本
│   ├── test_ddddocr.py          # ddddocr 识别准确率测试
│   ├── test_report.py           # MiMo 大模型识别准确率测试
│   ├── requirements.txt
│   ├── templates/               # 登录页与验证码生成页
│   └── reports/                 # 测试报告（准确率 / 耗时 / 置信区间）
└── docs/
    ├── 0202-2组-夏楠-网络安全技术课程设计报告.docx
    └── 基于OCR与LLM的验证码智能破解系统研究与实现.pptx
```

## 快速开始

```sh
cd captcha
pip install -r requirements.txt   # 另需单独安装 ddddocr
python main.py                    # 启动后访问 http://localhost:5000
```

登录页演示账号：`admin / admin123`（仅本地演示用）。

## 复现识别测试

先启动验证码服务（`python main.py`），再分别运行：

```sh
# ddddocr 路线
python test_ddddocr.py

# LLM 路线（密钥通过环境变量传入，不要写进代码）
export MIMO_API_KEY=sk-xxxx
python test_report.py        # 批量测试并生成报告
python captcha_cracker.py    # 单次自动破解演示
```

## 测试结果

ddddocr v1.6.1（100 样本/等级）：

| 测试组 | 识别准确率 | 平均耗时(ms) |
|--------|-----------|-------------|
| Level 1 | 96.00% | 5.42 |
| Level 2 | 78.00% | 4.76 |
| Level 3 | 67.00% | 4.97 |
| Level 4 | 40.00% | 5.23 |

MiMo v2.5 多模态大模型（5 样本/等级）：

| 测试组 | 识别准确率 | 平均耗时(ms) |
|--------|-----------|-------------|
| Level 1 | 100.00% | 2813.59 |
| Level 2 | 80.00% | 2399.04 |
| Level 3 | 60.00% | 8711.13 |
| Level 4 | 60.00% | 8379.67 |

结论：传统 OCR 速度快 3 个数量级，但准确率随干扰强度衰减明显；大模型对复杂干扰更鲁棒，但耗时与调用成本高。完整数据见 [captcha/reports](captcha/reports/)。

## 免责声明

本项目仅用于课程教学与授权环境下的安全研究，演示验证码机制的可攻破性以说明安全设计要点。请勿将相关技术用于任何未授权的系统。
