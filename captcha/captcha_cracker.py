"""
CAPTCHA验证码自动破解测试脚本
使用小米MiMo视觉模型识别验证码
"""

import os
import requests
import base64
import json
import time
import re
import ddddocr

# 初始化ddddocr
ocr = ddddocr.DdddOcr(show_ad=False)


# ==================== 配置 ====================

# 本地验证码服务器
LOCAL_SERVER = "http://localhost:5000"

# 小米MiMo API配置 (兼容OpenAI接口)
MIMO_API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MIMO_API_KEY = os.environ.get("MIMO_API_KEY", "")  # 通过环境变量设置，避免硬编码泄露
MIMO_MODEL = "mimo-v2.5"

# 登录凭据
USERNAME = "admin"
PASSWORD = "admin123"

# 破解策略配置
OCR_ATTEMPTS = 2   # ddddocr 尝试次数
LLM_ATTEMPTS = 5   # MiMo API 尝试次数


# ==================== 函数定义 ====================

def get_captcha():
    """
    从本地服务器获取验证码
    返回: (captcha_id, captcha_image_base64)
    """
    url = f"{LOCAL_SERVER}/api/get-login-captcha"
    response = requests.get(url)
    data = response.json()

    if data.get('success'):
        captcha_id = data['data']['id']
        captcha_image = data['data']['image']  # data:image/png;base64,...
        return captcha_id, captcha_image
    else:
        raise Exception(f"获取验证码失败: {data}")


def recognize_with_ddddocr(image_base64):
    """
    使用ddddocr识别验证码
    参数: image_base64 - base64编码的图片（含data:image前缀）
    返回: 识别出的验证码文本
    """
    # 解码base64图片
    if image_base64.startswith('data:image'):
        image_base64 = image_base64.split(',')[1]
    
    image_bytes = base64.b64decode(image_base64)
    
    result = ocr.classification(image_bytes)
    # 清理结果，只保留字母和数字
    captcha_text = re.sub(r'[^A-Za-z0-9]', '', result).upper()[:4]
    return captcha_text


def recognize_with_mimo(image_base64):
    """
    使用小米MiMo识别验证码
    参数: image_base64 - base64编码的图片（含data:image前缀）
    返回: 识别出的验证码文本
    """
    headers = {
        "Authorization": f"Bearer {MIMO_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = """请识别这张验证码图片中的字符。
要求：
1. 只输出识别出的字符，不要输出任何其他内容
2. 验证码由4个大写字母或数字组成
3. 如果看不清，根据最可能的形状猜测
4. 直接输出字符，例如: AB3K"""

    # 尝试多种格式
    # 格式1: 标准OpenAI多模态格式
    payload = {
        "model": MIMO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    max_retries = 3
    for attempt in range(max_retries):
        response = requests.post(MIMO_API_URL, headers=headers, json=payload)
        result = response.json()

        # 检查是否是速率限制错误
        if 'error' in result:
            error_msg = result['error'].get('message', '')
            if 'rate' in error_msg.lower() or 'limit' in error_msg.lower():
                wait_time = 5 * (attempt + 1)
                print(f"    速率限制，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue

        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            # 清理结果，只保留字母和数字
            captcha_text = re.sub(r'[^A-Za-z0-9]', '', content).upper()
            # 只取前4个字符
            captcha_text = captcha_text[:4]
            return captcha_text
        else:
            raise Exception(f"AI识别失败: {result}")

    raise Exception("AI识别失败: 多次重试后仍达到速率限制")


def login(captcha_id, captcha_code):
    """
    执行登录操作
    返回: 登录结果
    """
    url = f"{LOCAL_SERVER}/api/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "captcha_id": captcha_id,
        "captcha_code": captcha_code
    }

    response = requests.post(url, json=payload)
    return response.json(), response.status_code


def attempt_login(use_mimo=False):
    """
    尝试一次完整的登录流程
    参数: use_mimo - 是否使用MiMo API（否则使用ddddocr）
    返回: (success, message)
    """
    method = "MiMo API" if use_mimo else "ddddocr"
    print(f"--- [{method}] ---")

    # 1. 获取验证码
    print("[1] 获取验证码...")
    captcha_id, captcha_image = get_captcha()
    print(f"    验证码ID: {captcha_id}")

    # 2. 识别验证码
    print(f"[2] {method}识别验证码中...")
    if use_mimo:
        captcha_code = recognize_with_mimo(captcha_image)
    else:
        captcha_code = recognize_with_ddddocr(captcha_image)
    print(f"    识别结果: {captcha_code}")

    # 3. 尝试登录
    print("[3] 尝试登录...")
    result, status_code = login(captcha_id, captcha_code)

    if result.get('success'):
        print(f"    ✓ 登录成功! HTTP {status_code}")
        return True, result.get('message')
    else:
        print(f"    ✗ 登录失败: {result.get('message')}")
        return False, result.get('message')


# ==================== 主程序 ====================

def main():
    print("=" * 50)
    print("CAPTCHA验证码自动破解")
    print("=" * 50)
    print(f"目标服务器: {LOCAL_SERVER}")
    print(f"登录账号: {USERNAME}")
    total = OCR_ATTEMPTS + LLM_ATTEMPTS
    print(f"策略: 前{OCR_ATTEMPTS}次ddddocr，后{LLM_ATTEMPTS}次MiMo API")
    print("=" * 50)

    # 阶段1: 使用ddddocr
    print("\n>>> 阶段1: 使用ddddocr <<<")
    for i in range(1, OCR_ATTEMPTS + 1):
        print(f"\n[尝试 {i}/{total}]")
        try:
            success, message = attempt_login(use_mimo=False)
            if success:
                print(f"\n>>> 破解成功! (使用ddddocr) <<<")
                return
        except Exception as e:
            print(f"    错误: {e}")
        if i < OCR_ATTEMPTS:
            time.sleep(1)

    # 阶段2: 使用MiMo API
    print("\n>>> 阶段2: 使用MiMo API <<<")
    for i in range(OCR_ATTEMPTS + 1, total + 1):
        print(f"\n[尝试 {i}/{total}]")
        try:
            success, message = attempt_login(use_mimo=True)
            if success:
                print(f"\n>>> 破解成功! (使用MiMo API) <<<")
                return
        except Exception as e:
            print(f"    错误: {e}")
        if i < total:
            time.sleep(2)

    print("\n>>> 达到最大尝试次数，破解失败 <<<")


if __name__ == "__main__":
    main()
