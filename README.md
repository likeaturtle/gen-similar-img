# 图像描述与生成工具

一个基于豆包 AI 模型的相似图片生成工具。通过 **doubao-seed-1.6** 解读原图并生成结构化 JSON 描述，再使用火山引擎 **doubao-seedream-4.5** 基于 JSON 文件生成相似图片。

本工具适配 **Skill 能力**，可在 Claude、OpenCode 等客户端内通过技能调用，实现完整的工作流程：

**图片理解** → **描述生成** → **多轮对话优化描述** → **图片生成** → **进一步多轮优化** → **重新生成图片**

## 功能特性

- **图像描述生成**：上传图片（本地或 URL），自动生成结构化 JSON 描述
- **精细化描述**：覆盖画面比例、分辨率、主体内容、艺术风格、构图、镜头语言等多维度信息
- **图片生成**：根据 JSON 描述文件生成相似风格的图片
- **灵活的尺寸控制**：支持固定尺寸、宽高比、分辨率+宽高比组合等多种方式
- **智能规格识别**：可根据描述内容自动选择最佳图片尺寸和比例

## 环境要求

- Python >= 3.13
- 依赖包：
  - openai >= 1.0.0
  - requests >= 2.31.0
  - volcengine-python-sdk[ark] >= 1.0.0

## 安装

```bash
# 克隆项目
git clone <repository_url>
cd gen_similar_img

# 安装依赖（使用 pip）
pip install -r requirements.txt

# 或使用 uv
uv sync
```

## 配置

### 1. 创建配置文件

项目使用 `.config` 文件管理 API 配置和模型参数。首次使用需要创建配置文件：

```bash
# 复制配置模板
cp .config.example .config
```

### 2. 编辑配置文件

打开 `.config` 文件，填写您的 API 配置信息：

```ini
# API配置文件
# 请将您的API Key和Base URL填写在此处

# 豆包方舟API Key
ARK_API_KEY=YOUR_API_KEY

# 豆包方舟API Base URL
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 模型配置
# 图像描述模型（用于 description.py）
DESCRIPTION_MODEL=doubao-seed-1-6-251015

# 图像生成模型（用于 generation.py）
GENERATION_MODEL=doubao-seedream-4-5-251128
```

### 3. 配置说明

- **ARK_API_KEY**：您的豆包方舟 API 密钥（必填）
- **ARK_BASE_URL**：API 端点地址，默认为北京地域（必填）
- **DESCRIPTION_MODEL**：图像描述模型名称（必填）
- **GENERATION_MODEL**：图像生成模型名称（必填）

### 4. 环境变量支持

除了 `.config` 文件，也可以通过环境变量配置：

```bash
export ARK_API_KEY="your_api_key"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
export DESCRIPTION_MODEL="doubao-seed-1-6-251015"
export GENERATION_MODEL="doubao-seedream-4-5-251128"
```

**优先级**：`.config` 文件 > 环境变量

### 5. 安全提示

- ⚠️ **`.config` 文件已被 `.gitignore` 排除**，不会被提交到版本控制系统
- ⚠️ **请勿将 API Key 硬编码到代码中**
- ⚠️ **请勿将 `.config` 文件上传到公开仓库**

## 使用方法

### 1. 图像描述生成（description.py）

从图片生成详细的 JSON 描述文件。

#### 基本用法

```bash
# 使用远程 URL
python description.py --image https://example.com/image.jpg

# 使用本地文件
python description.py --image /path/to/image.png

# 自定义提示词
python description.py --image image.png --prompt "请详细描述这张图片的内容和风格"
```

#### 命令行参数

- `--image, -i`：图片来源，可以是 URL 或本地文件路径（必填）
- `--prompt, -p`：自定义提示文本（可选，默认使用内置的精细化描述模板）

#### 默认 Prompt 说明

内置的默认 prompt 采用**精细化结构化描述模板**，确保 AI 从多维度全面解析图片，生成的 JSON 描述包含以下 5 大类别：

1. **基础元数据**（`basic_meta`）
   - 画面比例（16:9、4:3、1:1 等）
   - 估算分辨率（4K、1080P 等）
   - 画质特征（8K超高清、胶片颗粒质感等）

2. **画面主体内容**（`main_content`）
   - 核心主体（人物/物体/场景的主要描述）
   - 主体细节（人物：五官、发型、服饰；物体：形状、材质、纹理；场景：空间结构、环境细节）
   - 背景元素、前景元素、互动关系

3. **艺术风格与氛围**（`art_style`）
   - 核心艺术风格（日系二次元、新中式水墨、赛博朋克等）
   - 色彩方案（高饱和撞色、莫兰迪色调等）
   - 光影效果（光源类型、光照方向、光影强度）
   - 画面氛围（温馨治愈、冷峻压抑等）
   - 笔触/质感（细腻平滑、粗犷油画笔触等）

4. **构图、视角与镜头语言**（`composition_lens`）
   - 拍摄视角（平视、俯视、仰视等）
   - 构图方式（居中对称、三分法、对角线构图等）
   - 焦点区域
   - 景别（特写 CT、近景 CU、中景 MS、全景 LS 等）
   - 画面焦段（超广角 24mm、标准 50mm、长焦 200mm 等）
   - 景深效果（浅景深背景虚化、深景深全画面清晰等）

5. **AI 绘图适配补充**（`ai_prompt_supplement`）
   - 正向关键词（高清细节、光影层次丰富等）
   - 反向关键词（模糊、比例失调、噪点过多等）

该模板确保描述达到**最小粒度拆分**，所有细节 100% 贴合图片实际，生成的 JSON 可直接用于 AI 绘图工具。

#### 输出

生成的 JSON 文件保存在 `output/des/` 目录下，文件名格式为 `description_<timestamp>.json`。

JSON 结构包含以下字段：
- `basic_meta`：基础元数据（画面比例、分辨率、画质特征）
- `main_content`：主体内容（核心主体、细节、背景/前景元素、互动关系）
- `art_style`：艺术风格（风格类型、色彩方案、光影效果、氛围、质感）
- `composition_lens`：构图与镜头（拍摄视角、构图方式、焦点区域、景别、焦段、景深）
- `ai_prompt_supplement`：AI 绘图补充（正向/反向关键词）

### 2. 图片生成（generation.py）

根据 JSON 描述文件生成图片。

#### 基本用法

```bash
# 直接指定尺寸
python generation.py input.json --size 1024x1024

# 使用宽高比（API 原生支持）
python generation.py input.json --aspect-ratio 16:9

# 使用分辨率+宽高比组合（自动计算精确尺寸）
python generation.py input.json --resolution 4K --aspect-ratio 16:9
python generation.py input.json --resolution 2K --aspect-ratio 1:1
python generation.py input.json --resolution 8294400 --aspect-ratio 9:16

# 智能模式（根据描述自动选择最佳规格）
python generation.py input.json

# 禁用水印
python generation.py input.json --size 1024x1024 --no-watermark
```

#### 命令行参数

- `json_path`：JSON 描述文件路径（位置参数，必填）
- `--size`：生成图片的尺寸，如 `1024x1024`、`1440x2560` 等
- `--aspect-ratio`：图片宽高比，如 `1:1`、`16:9`、`9:16`、`4:3`、`3:4` 等
- `--resolution`：总分辨率，如 `4K`、`2K`、`1080P` 或像素数（需配合 `--aspect-ratio` 使用）
- `--watermark`：添加水印（默认开启）
- `--no-watermark`：不添加水印

#### 输出

生成的图片保存在 `output/img/` 目录下，文件名格式为 `generated_image_<timestamp>.png`。

## 完整工作流程示例

```bash
# 步骤 1：从图片生成描述
python description.py --image https://example.com/photo.jpg

# 步骤 2：查看生成的 JSON 文件路径（输出会显示保存位置）
# 例如：output/des/description_20260113_223045.json

# 步骤 3：根据描述生成新图片
python generation.py output/des/description_20260113_223045.json --resolution 4K --aspect-ratio 16:9
```

## 项目结构

```
gen_similar_img/
├── description.py      # 图像描述生成模块
├── generation.py       # 图片生成模块
├── main.py            # 主入口（当前为示例）
├── requirements.txt   # 依赖列表
├── pyproject.toml     # 项目配置
├── uv.lock           # uv 锁定文件
└── output/           # 输出目录
    ├── des/          # JSON 描述文件
    └── img/          # 生成的图片
```

## 技术说明

### 描述生成

- **支持格式**：URL 图片使用同步 OpenAI 客户端，本地文件使用异步 AsyncArk 客户端
- **默认模型**：`doubao-seed-1-6-251015`（可通过 `.config` 文件配置）
- **描述维度**：包含基础元数据、主体内容、艺术风格、构图镜头语言等 5 大类别
- **输出格式**：结构化 JSON，可直接用于 AI 绘图工具
- **配置加载**：优先从 `.config` 文件读取，其次从环境变量读取

### 图片生成

- **默认模型**：`doubao-seedream-4-5-251128`（可通过 `.config` 文件配置）
- **尺寸适配**：自动计算并取整到 8 的倍数（符合生成模型要求）
- **支持的分辨率**：8K、4K、2K、1080P、720P 等标准分辨率
- **输出格式**：PNG 图片文件
- **配置加载**：优先从 `.config` 文件读取，其次从环境变量读取

## API 配置

项目使用火山引擎豆包 API，配置信息通过 `.config` 文件或环境变量设置。

### 配置项

| 配置项 | 说明 | 默认值 |
|------|------|--------|
| `ARK_API_KEY` | 豆包方舟 API 密钥 | 无（必填） |
| `ARK_BASE_URL` | API 端点地址 | `https://ark.cn-beijing.volces.com/api/v3` |
| `DESCRIPTION_MODEL` | 图像描述模型 | `doubao-seed-1-6-251015` |
| `GENERATION_MODEL` | 图像生成模型 | `doubao-seedream-4-5-251128` |

### 配置方式

1. **推荐：使用 `.config` 文件**
   - 创建 `.config` 文件并填写配置信息
   - 文件已被 `.gitignore` 排除，安全可靠

2. **备选：使用环境变量**
   - 适合 CI/CD 环境或服务器部署
   - 通过 `export` 命令设置环境变量

### 加载逻辑

两个 Python 模块都使用相同的配置加载逻辑：

1. 优先读取 `.config` 文件
2. 如果 `.config` 中未找到，则从环境变量读取
3. 如果两者都未找到，则报错并退出

### 获取 API Key

访问 [火山引擎控制台](https://console.volcengine.com/ark) 获取您的 API Key。

## 注意事项

1. **首次使用前必须配置** `.config` 文件或环境变量
2. 确保有稳定的网络连接以访问 API 服务
3. 生成高分辨率图片可能需要较长时间
4. JSON 描述越详细，生成的图片与原图相似度越高
5. 建议先生成描述并查看 JSON 内容，确认无误后再生成图片
6. **不要将** `.config` **文件提交到版本控制系统**

## 许可证

请根据项目实际情况添加许可证信息。

## 联系方式

如有问题或建议，请提交 Issue。
