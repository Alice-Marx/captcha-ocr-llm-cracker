"""
CAPTCHA验证码识别准确率测试 - ddddocr版本
使用ddddocr库进行验证码识别
"""

import requests
import base64
import json
import time
import re
import numpy as np
from datetime import datetime
import ddddocr

# ==================== 配置 ====================

# 本地验证码服务器
LOCAL_SERVER = "http://localhost:5000"

# 测试配置
SAMPLES_PER_LEVEL = 100

# 初始化ddddocr
ocr = ddddocr.DdddOcr(show_ad=False)


def generate_captcha(level, count=1):
    """生成验证码"""
    url = f"{LOCAL_SERVER}/api/generate"
    payload = {"level": level, "count": count}
    response = requests.post(url, json=payload)
    data = response.json()
    if data.get('success'):
        return data['data']
    else:
        raise Exception(f"生成验证码失败: {data}")


def recognize_with_ddddocr(image_base64):
    """
    使用ddddocr识别验证码
    返回: (识别结果, 耗时ms)
    """
    # 解码base64图片
    if image_base64.startswith('data:image'):
        image_base64 = image_base64.split(',')[1]
    
    image_bytes = base64.b64decode(image_base64)
    
    start_time = time.time()
    try:
        result = ocr.classification(image_bytes)
        elapsed_ms = (time.time() - start_time) * 1000
        # 清理结果，只保留字母和数字
        captcha_text = re.sub(r'[^A-Za-z0-9]', '', result).upper()[:4]
        return captcha_text, elapsed_ms
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return None, elapsed_ms


def calculate_confidence_interval(data, confidence=0.95):
    """计算置信区间"""
    n = len(data)
    if n == 0:
        return (0, 0)
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    se = std / np.sqrt(n)
    z = 1.96  # 95%置信区间
    margin = z * se
    return (mean - margin, mean + margin)


def test_level(level, samples=10):
    """
    测试某个等级的验证码
    返回: (准确率, 平均耗时, 置信区间, 详细结果)
    """
    print(f"\n{'='*50}")
    print(f"测试 Level {level} - 样本量: {samples}")
    print(f"{'='*50}")

    success_count = 0
    times = []
    results = []

    # 生成验证码
    captchas = generate_captcha(level, samples)

    for i, captcha in enumerate(captchas):
        captcha_id = captcha['id']
        expected = captcha['text']
        image = captcha['image']

        # 识别验证码
        recognized, elapsed_ms = recognize_with_ddddocr(image)

        # 判断是否正确
        is_correct = (recognized == expected) if recognized else False
        if is_correct:
            success_count += 1

        times.append(elapsed_ms)
        results.append({
            'expected': expected,
            'recognized': recognized,
            'correct': is_correct,
            'time_ms': elapsed_ms
        })

        # 打印每次结果
        status = "✓" if is_correct else "✗"
        rec_str = recognized if recognized else "None"
        print(f"  [{i+1}/{samples}] 期望: {expected} | 识别: {rec_str} | {status} | {elapsed_ms:.2f}ms")

    # 计算统计结果
    accuracy = success_count / samples * 100
    avg_time = np.mean(times) if times else 0
    ci = calculate_confidence_interval(times)

    return accuracy, avg_time, ci, results


def generate_markdown_report(results):
    """生成Markdown格式的测试报告"""
    report = f"""# CAPTCHA验证码识别准确率测试报告 (ddddocr)

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试工具**: ddddocr v1.6.1
**测试服务器**: {LOCAL_SERVER}
**样本量**: {SAMPLES_PER_LEVEL} 个/等级

## 测试结果汇总

| 测试组 | 样本量 | 识别准确率 | 平均耗时(ms) | 置信区间(95%) |
|--------|--------|-----------|-------------|--------------|
"""

    for level in [1, 2, 3, 4]:
        if level in results:
            acc, avg, ci, _ = results[level]
            report += f"| Level{level} | {SAMPLES_PER_LEVEL} | {acc:.2f}% | {avg:.2f} | ({ci[0]:.2f}, {ci[1]:.2f}) |\n"

    report += f"""
## 详细分析

### Level 1 - 基础文本验证码
- 特点: 纯文本，无任何视觉干扰
- 用途: 建立基准性能

### Level 2 - 噪点干扰验证码
- 特点: 10-15个随机干扰点
- 用途: 模拟轻度干扰

### Level 3 - 字符扭曲验证码
- 特点: 字符随机旋转15-25度
- 用途: 增加识别难度

### Level 4 - 综合复杂验证码
- 特点: 渐变背景 + 干扰线 + 字符扭曲
- 用途: 模拟商业系统验证码
"""
    return report


def main():
    print("=" * 60)
    print("CAPTCHA验证码识别准确率测试 (ddddocr)")
    print("=" * 60)
    print(f"工具: ddddocr")
    print(f"每个等级测试样本: {SAMPLES_PER_LEVEL}")
    print("=" * 60)

    all_results = {}

    # 测试4个等级
    for level in [1, 2, 3, 4]:
        accuracy, avg_time, ci, results = test_level(level, SAMPLES_PER_LEVEL)
        all_results[level] = (accuracy, avg_time, ci, results)

        print(f"\n--- Level {level} 结果 ---")
        print(f"准确率: {accuracy:.2f}%")
        print(f"平均耗时: {avg_time:.2f}ms")
        print(f"95%置信区间: ({ci[0]:.2f}, {ci[1]:.2f})")

    # 生成报告
    report = generate_markdown_report(all_results)

    # 保存报告
    with open("test_report_ddddocr.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("\n" + "=" * 60)
    print("测试完成！报告已保存到 test_report_ddddocr.md")
    print("=" * 60)

    # 打印报告
    print("\n" + report)


if __name__ == "__main__":
    main()
