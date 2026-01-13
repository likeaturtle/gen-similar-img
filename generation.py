import os
import json
import argparse
import requests
import math
from openai import OpenAI
from datetime import datetime


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


def load_prompt_from_json(json_path):
    """从JSON文件加载prompt内容"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 将JSON对象转换为格式化的字符串
    json_content = json.dumps(data, ensure_ascii=False, indent=2)
    # 在最前面添加说明文字
    prompt = f"根据以下 json 格式内容的描述，生成图片：\n\n{json_content}"
    return prompt


def calculate_size_from_resolution(resolution, aspect_ratio):
    """
    根据总分辨率和宽高比计算具体尺寸
    
    Args:
        resolution: 总分辨率，如 '4K', '2K', '1080P', 或像素数如 '8294400'
        aspect_ratio: 宽高比，如 '16:9', '1:1' 等
    
    Returns:
        计算出的尺寸字符串，如 '3840x2160'
    """
    # 解析分辨率
    resolution_map = {
        '8K': 7680 * 4320,
        '4K': 3840 * 2160,
        '2K': 2560 * 1440,
        '1080P': 1920 * 1080,
        'FHD': 1920 * 1080,
        '720P': 1280 * 720,
        'HD': 1280 * 720,
    }
    
    # 获取总像素数
    resolution_upper = resolution.upper()
    if resolution_upper in resolution_map:
        total_pixels = resolution_map[resolution_upper]
    else:
        try:
            total_pixels = int(resolution)
        except ValueError:
            raise ValueError(f"不支持的分辨率格式: {resolution}")
    
    # 解析宽高比
    try:
        ratio_parts = aspect_ratio.split(':')
        if len(ratio_parts) != 2:
            raise ValueError(f"无效的宽高比格式: {aspect_ratio}")
        width_ratio = float(ratio_parts[0])
        height_ratio = float(ratio_parts[1])
    except (ValueError, IndexError):
        raise ValueError(f"无效的宽高比: {aspect_ratio}")
    
    # 计算宽和高
    # total_pixels = width * height
    # width / height = width_ratio / height_ratio
    # 因此: width = height * (width_ratio / height_ratio)
    # total_pixels = height * (width_ratio / height_ratio) * height
    # height^2 = total_pixels * (height_ratio / width_ratio)
    
    height = math.sqrt(total_pixels * height_ratio / width_ratio)
    width = height * (width_ratio / height_ratio)
    
    # 取整到8的倍数（多数图片生成模型对这个有要求）
    width = round(width / 8) * 8
    height = round(height / 8) * 8
    
    return f"{int(width)}x{int(height)}"


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='从JSON文件生成图片',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用示例:
  # 直接指定尺寸
  python generation.py input.json --size 1024x1024
  
  # 使用宽高比（API原生支持）
  python generation.py input.json --aspect-ratio 16:9
  
  # 使用分辨率+宽高比组合（自动计算尺寸）
  python generation.py input.json --resolution 4K --aspect-ratio 16:9
  python generation.py input.json --resolution 2K --aspect-ratio 1:1
  python generation.py input.json --resolution 8294400 --aspect-ratio 9:16
        """)
    parser.add_argument('json_path', type=str, help='JSON描述文件的路径')
    parser.add_argument('--size', type=str, help='生成图片的尺寸，如 1024x1024, 1440x2560 等')
    parser.add_argument('--aspect-ratio', type=str, dest='aspect_ratio', 
                        help='图片宽高比，如 1:1, 16:9, 9:16, 4:3, 3:4 等')
    parser.add_argument('--resolution', type=str,
                        help='总分辨率，如 4K, 2K, 1080P 或像素数（需配合 --aspect-ratio 使用）')
    parser.add_argument('--watermark', action='store_true', default=True, 
                        help='添加水印 (默认已开启)')
    parser.add_argument('--no-watermark', action='store_false', dest='watermark',
                        help='不添加水印')
    args = parser.parse_args()
    
    # 参数验证和处理
    final_size = None
    use_aspect_ratio_api = False
    
    # 情况1: 使用 resolution + aspect_ratio 组合
    if args.resolution:
        if not args.aspect_ratio:
            print("错误: 使用 --resolution 时必须同时指定 --aspect-ratio")
            return
        try:
            final_size = calculate_size_from_resolution(args.resolution, args.aspect_ratio)
            print(f"根据分辨率 {args.resolution} 和宽高比 {args.aspect_ratio} 计算出尺寸: {final_size}")
        except ValueError as e:
            print(f"错误: {e}")
            return
    
    # 情况2: 单独使用 aspect_ratio（API原生支持）
    elif args.aspect_ratio and not args.size:
        use_aspect_ratio_api = True
        print(f"使用API原生宽高比参数: {args.aspect_ratio}")
    
    # 情况3: 同时指定了 size 和 aspect_ratio
    elif args.size and args.aspect_ratio:
        print("警告: 同时指定了 --size 和 --aspect-ratio，将优先使用 aspect_ratio")
        use_aspect_ratio_api = True
    
    # 情况4: 单独使用 size
    elif args.size:
        final_size = args.size
    
    # 情况5: 什么都没指定，让 API 根据 prompt 自动决定
    else:
        final_size = None
        use_aspect_ratio_api = False
        print(f"未指定输出规格，将根据 prompt 内容自动决定最佳尺寸和比例")
    
    # 检查JSON文件是否存在
    if not os.path.exists(args.json_path):
        print(f"错误: JSON文件不存在: {args.json_path}")
        return
    
    # 从JSON文件加载prompt
    print(f"正在读取JSON文件: {args.json_path}")
    prompt = load_prompt_from_json(args.json_path)
    print(f"Prompt已加载，长度: {len(prompt)} 字符")
    
    # 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中 
    # 初始化Ark客户端，从环境变量中读取您的API Key
    config = load_config()
    api_key = config.get('ARK_API_KEY', os.getenv('ARK_API_KEY'))
    base_url = config.get('ARK_BASE_URL', os.getenv('ARK_BASE_URL'))
    model = config.get('GENERATION_MODEL', os.getenv('GENERATION_MODEL'))
    
    if not api_key:
        print("错误: 未找到 ARK_API_KEY，请在 .config 文件或环境变量中配置")
        return
    if not base_url:
        print("错误: 未找到 ARK_BASE_URL，请在 .config 文件或环境变量中配置")
        return
    if not model:
        print("错误: 未找到 GENERATION_MODEL，请在 .config 文件或环境变量中配置")
        return
    
    client = OpenAI( 
        # 此为默认路径，您可根据业务所在地域进行配置 
        base_url=base_url, 
        # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改 
        api_key=api_key, 
    ) 
    
    # 构建图片生成参数
    generate_params = {
        "model": model,
        "prompt": prompt,
        "response_format": "url",
        "extra_body": {
            "watermark": args.watermark,
        }
    }
    
    # 根据参数设置 size 或 aspect_ratio
    if use_aspect_ratio_api:
        generate_params["extra_body"]["aspect_ratio"] = args.aspect_ratio
        print(f"正在生成图片... (宽高比: {args.aspect_ratio}, 水印: {args.watermark})")
    elif final_size:
        generate_params["size"] = final_size
        print(f"正在生成图片... (尺寸: {final_size}, 水印: {args.watermark})")
    else:
        # 不设置 size 和 aspect_ratio，让 API 根据 prompt 自动决定
        print(f"正在生成图片... (智能分析 prompt 以确定最佳规格, 水印: {args.watermark})")
    
    imagesResponse = client.images.generate(**generate_params) 
    
    # 获取图片URL
    image_url = imagesResponse.data[0].url
    print(f"图片URL: {image_url}")
    
    # 创建 output/img 目录
    output_dir = "output/img"
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成文件名（使用时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_filename = f"generated_image_{timestamp}.png"
    image_path = os.path.join(output_dir, image_filename)
    
    # 下载并保存图片
    print("正在下载图片...")
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(image_path, 'wb') as f:
            f.write(response.content)
        print(f"图片已保存到: {image_path}")
    else:
        print(f"下载图片失败，状态码: {response.status_code}")


if __name__ == "__main__":
    main()