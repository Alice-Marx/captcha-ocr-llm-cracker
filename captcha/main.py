import os
import io
import random
import string
import base64
import math
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, render_template, session
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'captcha_secret_key_2026'

# 存储验证码信息 (内存存储，生产环境应使用Redis)
captcha_store = {}

# 验证码配置
CAPTCHA_CONFIG = {
    'width': 200,
    'height': 80,
    'char_count': 4,
    'font_size': 36,
    'expire_seconds': 300  # 5分钟过期
}


def generate_random_text(length=4):
    """生成随机验证码文本"""
    # 使用数字和大写字母，排除容易混淆的字符
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(random.choice(chars) for _ in range(length))


def get_random_color(min_val=0, max_val=2000):
    """生成随机颜色"""
    return (random.randint(min_val, max_val),
            random.randint(min_val, max_val),
            random.randint(min_val, max_val))


def create_level1_captcha(text):
    """
    Level 1: 最基础的纯文本验证码，没有任何视觉干扰
    用于建立基准性能
    """
    width = CAPTCHA_CONFIG['width']
    height = CAPTCHA_CONFIG['height']

    # 白色背景
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 尝试加载字体
    try:
        font = ImageFont.truetype("arial.ttf", CAPTCHA_CONFIG['font_size'])
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                      CAPTCHA_CONFIG['font_size'])
        except:
            font = ImageFont.load_default()

    # 计算文本位置（居中）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # 黑色文字，无任何干扰
    draw.text((x, y), text, fill=(0, 0, 0), font=font)

    return image


def create_level2_captcha(text):
    """
    Level 2: 引入随机噪点干扰
    每个验证码图像中添加10-15个随机位置的干扰点
    """
    width = CAPTCHA_CONFIG['width']
    height = CAPTCHA_CONFIG['height']

    # 浅色背景
    image = Image.new('RGB', (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", CAPTCHA_CONFIG['font_size'])
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                      CAPTCHA_CONFIG['font_size'])
        except:
            font = ImageFont.load_default()

    # 绘制文字
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x_start = (width - text_width * len(text) // 2) // 4
    y = (height - text_height) // 2

    for i, char in enumerate(text):
        x = x_start + i * (text_width // len(text) + 5)
        color = get_random_color(0, 150)
        draw.text((x, y), char, fill=color, font=font)

    # 添加10-15个随机干扰点
    noise_count = random.randint(10, 15)
    for _ in range(noise_count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        radius = random.randint(2, 4)
        color = get_random_color(50, 200)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)

    return image


def create_level3_captcha(text):
    """
    Level 3: 字符扭曲效果
    每个字符随机旋转15-25度，大幅增加识别难度
    """
    width = CAPTCHA_CONFIG['width']
    height = CAPTCHA_CONFIG['height']

    # 浅灰色背景
    image = Image.new('RGB', (width, height), (220, 220, 220))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", CAPTCHA_CONFIG['font_size'])
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                      CAPTCHA_CONFIG['font_size'])
        except:
            font = ImageFont.load_default()

    # 逐个字符绘制，应用旋转效果
    char_width = width // len(text)
    for i, char in enumerate(text):
        # 创建单字符图像
        char_img = Image.new('RGBA', (50, 50), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)

        color = get_random_color(0, 150)
        char_draw.text((5, 5), char, fill=color, font=font)

        # 随机旋转15-25度
        angle = random.randint(15, 25) * random.choice([-1, 1])
        char_img = char_img.rotate(angle, expand=True, resample=Image.BICUBIC)

        # 粘贴到主图像
        x = i * char_width + 10
        y = random.randint(5, height - 50)
        image.paste(char_img, (x, y), char_img)

    # 添加少量干扰点
    for _ in range(8):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        radius = random.randint(1, 3)
        color = get_random_color(100, 200)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)

    return image


def create_gradient(width, height):
    """创建渐变背景"""
    image = Image.new('RGB', (width, height))
    pixels = image.load()

    # 随机选择渐变方向
    start_color = get_random_color(180, 240)
    end_color = get_random_color(180, 240)

    for y in range(height):
        for x in range(width):
            # 计算渐变比例
            ratio = (x + y) / (width + height)
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            pixels[x, y] = (r, g, b)

    return image


def create_level4_captcha(text):
    """
    Level 4: 最复杂 - 综合渐变背景和随机干扰线
    近似模拟商业系统中常见的验证码复杂度
    """
    width = CAPTCHA_CONFIG['width']
    height = CAPTCHA_CONFIG['height']

    # 渐变背景
    image = create_gradient(width, height)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", CAPTCHA_CONFIG['font_size'])
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                      CAPTCHA_CONFIG['font_size'])
        except:
            font = ImageFont.load_default()

    # 添加3-5条随机干扰线
    line_count = random.randint(3, 5)
    for _ in range(line_count):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = get_random_color(80, 180)
        line_width = random.randint(1, 3)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=line_width)

    # 添加干扰点
    for _ in range(20):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        radius = random.randint(1, 3)
        color = get_random_color(50, 200)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)

    # 绘制扭曲的文字
    char_width = width // len(text)
    for i, char in enumerate(text):
        # 创建单字符图像
        char_img = Image.new('RGBA', (50, 50), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)

        # 使用深色文字，确保在渐变背景上可见
        color = get_random_color(0, 100)
        char_draw.text((5, 5), char, fill=color, font=font)

        # 随机旋转
        angle = random.randint(10, 20) * random.choice([-1, 1])
        char_img = char_img.rotate(angle, expand=True, resample=Image.BICUBIC)

        # 粘贴到主图像
        x = i * char_width + 15
        y = random.randint(5, height - 50)
        image.paste(char_img, (x, y), char_img)

    # 应用轻微的模糊效果
    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

    return image


def image_to_base64(image):
    """将PIL图像转换为base64字符串"""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


def generate_captcha(level, count=1):
    """
    生成指定等级和数量的验证码
    返回: list of {id, text, image_base64}
    """
    results = []

    for _ in range(count):
        text = generate_random_text()
        captcha_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

        # 根据等级选择生成函数
        if level == 1:
            image = create_level1_captcha(text)
        elif level == 2:
            image = create_level2_captcha(text)
        elif level == 3:
            image = create_level3_captcha(text)
        elif level == 4:
            image = create_level4_captcha(text)
        else:
            image = create_level1_captcha(text)

        # 存储验证码信息
        captcha_store[captcha_id] = {
            'text': text,
            'created_at': datetime.now(),
            'level': level
        }

        # 清理过期的验证码
        cleanup_expired_captchas()

        results.append({
            'id': captcha_id,
            'text': text,  # 开发用，生产环境不应返回
            'image': image_to_base64(image)
        })

    return results


def cleanup_expired_captchas():
    """清理过期的验证码"""
    now = datetime.now()
    expired_ids = [
        cid for cid, data in captcha_store.items()
        if (now - data['created_at']).seconds > CAPTCHA_CONFIG['expire_seconds']
    ]
    for cid in expired_ids:
        del captcha_store[cid]


# ==================== 路由 ====================

@app.route('/')
def index():
    """首页 - 重定向到验证码生成器"""
    return render_template('generator.html')


@app.route('/generator')
def generator_page():
    """验证码生成器页面"""
    return render_template('generator.html')


@app.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """
    API: 生成验证码
    参数: {level: int, count: int}
    """
    data = request.get_json()
    level = data.get('level', 1)
    count = data.get('count', 1)

    # 参数验证
    if level not in [1, 2, 3, 4]:
        return jsonify({'error': '无效的验证码等级，支持1-4'}), 400
    if count < 1 or count > 2000:
        return jsonify({'error': '验证码数量范围为1-2000'}), 400

    try:
        results = generate_captcha(level, count)
        return jsonify({
            'success': True,
            'data': results
        })
    except Exception as e:
        return jsonify({'error': f'生成验证码失败: {str(e)}'}), 500


@app.route('/api/get-login-captcha', methods=['GET'])
def api_get_login_captcha():
    """API: 获取登录页面的Level 4验证码"""
    try:
        results = generate_captcha(4, 1)
        return jsonify({
            'success': True,
            'data': results[0]
        })
    except Exception as e:
        return jsonify({'error': f'生成验证码失败: {str(e)}'}), 500


@app.route('/api/login', methods=['POST'])
def api_login():
    """
    API: 登录验证
    参数: {username: str, password: str, captcha_id: str, captcha_code: str}
    """
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    captcha_id = data.get('captcha_id', '')
    captcha_code = data.get('captcha_code', '').upper()

    # 验证码校验
    if captcha_id not in captcha_store:
        return jsonify({'success': False, 'message': '验证码已过期，请刷新验证码'}), 400

    stored_captcha = captcha_store[captcha_id]

    # 检查验证码是否过期
    if (datetime.now() - stored_captcha['created_at']).seconds > CAPTCHA_CONFIG['expire_seconds']:
        del captcha_store[captcha_id]
        return jsonify({'success': False, 'message': '验证码已过期，请刷新验证码'}), 400

    # 验证码文本比较（不区分大小写）
    if captcha_code != stored_captcha['text']:
        # 验证失败后删除验证码，需要重新获取
        del captcha_store[captcha_id]
        return jsonify({'success': False, 'message': '验证码错误'}), 400

    # 验证码正确，删除已使用的验证码
    del captcha_store[captcha_id]

    # 验证用户名和密码
    if username == 'admin' and password == 'admin123':
        return jsonify({
            'success': True,
            'message': '登录成功',
            'status_code': 200
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 400


@app.route('/api/levels', methods=['GET'])
def api_levels():
    """API: 获取验证码等级说明"""
    levels = [
        {
            'level': 1,
            'name': '基础文本',
            'description': '最基础的纯文本验证码，没有任何视觉干扰，主要用于建立基准性能'
        },
        {
            'level': 2,
            'name': '噪点干扰',
            'description': '引入随机噪点干扰，每个验证码图像中添加10-15个随机位置的干扰点，模拟轻度干扰'
        },
        {
            'level': 3,
            'name': '字符扭曲',
            'description': '实现字符扭曲效果，每个字符随机旋转15-25度，大幅增加识别难度'
        },
        {
            'level': 4,
            'name': '综合复杂',
            'description': '综合渐变背景和随机干扰线，近似模拟商业系统中常见的验证码复杂度'
        }
    ]
    return jsonify({'success': True, 'data': levels})


if __name__ == '__main__':
    # 确保templates目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("=" * 50)
    print("CAPTCHA验证码系统")
    print("=" * 50)
    print("访问地址:")
    print("  - 验证码生成器: http://localhost:5000/generator")
    print("  - 登录页面: http://localhost:5000/login")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True)
