import os
import json
import argparse
import asyncio
from datetime import datetime
from openai import OpenAI
from volcenginesdkarkruntime import AsyncArk

def load_config():
    """从 .config 文件加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), '.config')
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

def extract_json_from_response(response):
    """从 API 响应中提取 JSON 内容"""
    json_contents = []
    
    # 遍历 response.output 中的所有项
    for output_item in response.output:
        # 检查是否是 ResponseOutputMessage 类型
        if hasattr(output_item, 'type') and output_item.type == 'message':
            # 检查是否有 content 列表
            if hasattr(output_item, 'content') and output_item.content:
                for content_item in output_item.content:
                    # 检查是否是 ResponseOutputText 类型
                    if hasattr(content_item, 'type') and content_item.type == 'output_text':
                        # 获取 text 内容
                        if hasattr(content_item, 'text') and content_item.text:
                            text = content_item.text.strip()
                            # 检查是否是 JSON 格式（以 { 开头）
                            if text.startswith('{'):
                                try:
                                    json_obj = json.loads(text)
                                    json_contents.append(json_obj)
                                    print(f"✓ 成功解析 JSON 对象")
                                except json.JSONDecodeError as e:
                                    print(f"警告: JSON 解析失败 - {e}")
    
    return json_contents

def save_json_to_file(json_data, output_path):
    """将 JSON 数据保存到文件"""
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ JSON 文件已保存到: {output_path}")

def process_image_description(image_source, prompt_text=None):
    """
    处理图片描述任务
    
    Args:
        image_source: 图片来源，可以是 URL 或本地文件路径
        prompt_text: 提示文本，如果为 None 则使用默认提示
    
    Returns:
        保存的 JSON 文件路径
    """
    # 默认提示文本
    if prompt_text is None:
        # prompt_text = "根据上传的图片，倒推出完整、全面描述图片的中文json代码，要求全面覆盖对图片内容、风格、画面比例、分辨率等的描述，生成的json代码满足AI生成图片的需要。"
        prompt_text = """
# 生成要求
请根据上传的图片，生成结构化中文JSON描述文件，需按以下精细化字段拆分，覆盖图片所有维度（含镜头语言），无任何细节遗漏：
## 1. 基础元数据（必填字段：`basic_meta`）
- `image_ratio`：画面比例，精确到具体数值（如 16:9 / 4:3 / 1:1 / 9:16 / 2.35:1 电影宽屏 / 1.85:1 院线画幅）
- `estimated_resolution`：估算分辨率，标注像素值（如 1920×1080 / 512×512 / 3840×2160 4K / 7680×4320 8K）
- `file_quality`：画质特征（如 8K超高清 / 1080P高清 / 胶片颗粒质感 / 无噪点 / 轻微复古模糊 / HDR高动态范围 / 低动态范围LDR）
## 2. 画面主体内容（必填字段：`main_content`，拆分为最小描述单元）
- `core_subject`：核心主体（如 一名穿JK制服的少女 / 一只橘猫 / 一座复古蒸汽朋克工厂 / 一片星空下的湖泊）
- `subject_details`：主体细节，逐条罗列        
  - 人物类：五官特征、发型发色、服饰款式/颜色/材质、姿态动作、表情神态、配饰（如眼镜/项链/腰带）、皮肤质感（如细腻光滑 / 带轻微雀斑）
  - 物体类：形状、颜色、材质纹理（如 木质粗糙纹理 / 金属反光质感 / 玻璃透明磨砂）、磨损程度（如 全新无划痕 / 轻微掉漆 / 重度锈蚀）、摆放位置
  - 场景类：空间结构（如 室内客厅/loft复式 / 户外森林/沙漠戈壁 / 科幻太空舱/赛博朋克街头）、核心建筑/景观位置、环境细节（如 地面材质 / 墙面装饰）
- `background_elements`：背景元素，逐条罗列（如 远处的山脉/云层 / 墙上的复古海报/挂钟 / 漂浮的太空陨石/星云 / 地面的落叶/积水倒影）
- `foreground_elements`：前景元素，逐条罗列（如 画面下方的一杯咖啡/绿植 / 窗前的白色窗帘/纱幔 / 脚下的石板路/草坪）
- `interaction_relation`：主体与环境的互动关系（如 少女坐在窗边看书/阳光洒在发丝上 / 橘猫趴在沙发上晒太阳/爪子搭在抱枕上 / 工厂烟囱冒出黑烟/与天空雾霾融合）
## 3. 艺术风格与氛围（必填字段：`art_style`，细分到具体流派和表现手法）
- `style_type`：核心艺术风格（如 日系二次元赛璐璐 / 新中式水墨写实 / 梵高印象派油画 / 赛博朋克像素风 / 美式3D卡通渲染 / 写实主义摄影风 / 复古胶片风）
- `color_scheme`：色彩方案（如 高饱和撞色 / 低饱和莫兰迪色调 / 暖黄色复古色调 / 冷蓝色科技色调 / 黑白灰单色 / 马卡龙浅色系 / 暗调低明度色系）
- `light_effect`：光影效果，逐条拆分
  - 光源类型（如 自然光/太阳光 / 室内暖光灯/台灯 / 霓虹灯/LED灯 / 月光/星光）
  - 光照方向（如 左侧侧光 / 顶光 / 逆光/轮廓光 / 漫射光/无明显方向 / 45°斜前方顺光）
  - 光影强度（如 硬阴影对比强烈 / 柔和阴影无明显边界 / 高光过曝效果 / 低光暗部细节丰富）
- `atmosphere`：画面氛围（如 温馨治愈 / 冷峻压抑 / 未来科技感 / 复古怀旧 / 梦幻唯美 / 悬疑紧张 / 宁静祥和）
- `brush_texture`：笔触/质感（如 细腻平滑无笔触 / 粗犷油画笔触 / 水彩晕染质感 / 像素块颗粒感 / 胶片颗粒感 / 数码渲染光滑质感）
## 4. 构图、视角与镜头语言（必填字段：`composition_lens`）
- `shooting_angle`：拍摄视角（如 平视 / 俯视/鸟瞰 / 仰视/虫眼 / 45°斜角 / 广角鱼眼 / 微距视角 / 长焦压缩视角）
- `composition_type`：构图方式（如 居中对称构图 / 三分法构图 / 对角线构图 / 框架式构图 / 留白构图 / 引导线构图 / 三角形构图）
- `focus_area`：焦点区域（如 主体人物面部/眼睛 / 物体的中心位置 / 画面左侧的红色建筑 / 前景的绿植叶片）
- `shot_type`：景别（严格对应镜头语言规范，如 特写（CT）/大特写（EXT） / 近景（CU） / 中近景（MCU） / 中景（MS） / 全景（LS） / 远景（ELS） / 大远景（XLS））
- `focal_length`：画面焦段（估算对应相机焦段，如 超广角24mm以下 / 广角24-35mm / 标准50mm / 中长焦85-135mm / 长焦200mm以上 / 微距100mm）
- `depth_of_field`：景深效果（如 浅景深/背景虚化明显 / 深景深/全画面清晰 / 中等景深/主体与近景清晰、远景微虚）
## 5. AI绘图适配补充（必填字段：`ai_prompt_supplement`）
- `positive_keywords`：正向关键词，提炼核心特征（如 高清细节 / 细腻皮肤质感 / 光影层次丰富 / 色彩鲜明 / 边缘锐利 / 材质还原精准 / 镜头感十足）
- `negative_keywords`：反向关键词，规避负面效果（如 模糊 / 比例失调 / 色彩溢出 / 噪点过多 / 细节缺失 / 边缘模糊 / 光影混乱 / 焦段不符）
# 输出要求
1. JSON格式严格合规，字段层级清晰，无语法错误，可直接复制到AI绘图工具中使用；
2. 所有描述100%贴合图片实际，不添加主观臆造内容，最小粒度拆分细节（如主体细节、光影效果需逐条罗列，不笼统概括）；
3. 语言简洁精准，符合AI绘图关键词表达习惯，避免模糊表述（如用“24mm超广角视角，浅景深背景虚化”而非“视角广，背景模糊”）；
4. 景别、焦段描述需严格对应画面实际呈现效果，无偏差（如人物仅露出面部为特写，全身入镜且环境完整为全景）。
        """

    # 判断是 URL 还是本地文件
    if image_source.startswith('http://') or image_source.startswith('https://'):
        # URL 格式 - 使用同步 OpenAI 客户端
        print(f"使用图片 URL: {image_source}")
        return _process_with_openai(image_source, prompt_text)
    else:
        # 本地文件格式 - 使用异步 AsyncArk 客户端
        if not os.path.exists(image_source):
            raise FileNotFoundError(f"本地文件不存在: {image_source}")
        abs_path = os.path.abspath(image_source)
        print(f"使用本地文件: {abs_path}")
        return asyncio.run(_process_with_asyncark(abs_path, prompt_text))

def _process_with_openai(image_url, prompt_text):
    """
    使用 OpenAI 客户端处理 URL 图片
    """
    # 初始化 OpenAI 客户端
    print("正在初始化 OpenAI 客户端...")
    config = load_config()
    api_key = config.get('ARK_API_KEY', os.getenv('ARK_API_KEY'))
    base_url = config.get('ARK_BASE_URL', os.getenv('ARK_BASE_URL'))
    model = config.get('DESCRIPTION_MODEL', os.getenv('DESCRIPTION_MODEL'))
    
    if not api_key:
        raise ValueError("未找到 ARK_API_KEY，请在 .config 文件或环境变量中配置")
    if not base_url:
        raise ValueError("未找到 ARK_BASE_URL，请在 .config 文件或环境变量中配置")
    if not model:
        raise ValueError("未找到 DESCRIPTION_MODEL，请在 .config 文件或环境变量中配置")
    
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    
    # 发送请求
    print("正在发送 API 请求...")
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": image_url
                    },
                    {
                        "type": "input_text",
                        "text": prompt_text
                    },
                ],
            }
        ]
    )
    
    print("✓ API 请求成功")
    return _save_response(response)

async def _process_with_asyncark(local_path, prompt_text):
    """
    使用 AsyncArk 客户端处理本地文件
    """
    # 初始化 AsyncArk 客户端
    print("正在初始化 AsyncArk 客户端...")
    config = load_config()
    api_key = config.get('ARK_API_KEY', os.getenv('ARK_API_KEY'))
    base_url = config.get('ARK_BASE_URL', os.getenv('ARK_BASE_URL'))
    model = config.get('DESCRIPTION_MODEL', os.getenv('DESCRIPTION_MODEL'))
    
    if not api_key:
        raise ValueError("未找到 ARK_API_KEY，请在 .config 文件或环境变量中配置")
    if not base_url:
        raise ValueError("未找到 ARK_BASE_URL，请在 .config 文件或环境变量中配置")
    if not model:
        raise ValueError("未找到 DESCRIPTION_MODEL，请在 .config 文件或环境变量中配置")
    
    client = AsyncArk(
        base_url=base_url,
        api_key=api_key
    )
    
    # 发送请求
    print("正在发送 API 请求...")
    response = await client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"file://{local_path}"
                    },
                    {
                        "type": "input_text",
                        "text": prompt_text
                    }
                ]
            }
        ]
    )
    
    print("✓ API 请求成功")
    return _save_response(response)

def _save_response(response):
    # 提取 JSON 内容
    print("正在提取 JSON 内容...")
    json_contents = extract_json_from_response(response)
    
    if not json_contents:
        print("错误: 未找到有效的 JSON 内容")
        print("\n完整响应内容:")
        print(response)
        return
    
    print(f"✓ 找到 {len(json_contents)} 个 JSON 对象")
    
    # 如果有多个 JSON 对象，保存最后一个（通常是最终输出）
    final_json = json_contents[-1] if json_contents else {}
    
    # 设置输出路径（带时间戳）
    output_dir = 'output/des'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'description_{timestamp}.json'
    output_file = os.path.join(output_dir, output_filename)
    
    # 保存到文件
    save_json_to_file(final_json, output_file)
    
    print(f"\n✓ 处理完成！")
    print(f"  - 输出文件: {output_file}")
    print(f"  - JSON 对象包含 {len(final_json)} 个字段")
    
    return output_file

def main():
    """
    主函数 - 通过命令行参数接收图片源
    """
    parser = argparse.ArgumentParser(
        description='处理图片并生成描述的 JSON 文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 使用远程 URL
  python description.py --image https://example.com/image.jpg
  
  # 使用本地文件
  python description.py --image /path/to/local/image.png
  
  # 自定义提示文本
  python description.py --image image.png --prompt "请详细描述这张图片的内容和风格"
        ''')
    
    parser.add_argument(
        '--image', '-i',
        required=True,
        help='图片来源，可以是 URL 或本地文件路径'
    )
    
    parser.add_argument(
        '--prompt', '-p',
        default=None,
        help='自定义提示文本（可选）'
    )
    
    args = parser.parse_args()
    
    # 调用处理函数
    process_image_description(args.image, args.prompt)

if __name__ == '__main__':
    main()