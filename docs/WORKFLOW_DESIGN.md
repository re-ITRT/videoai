# 工作流设计文档

## 已有工作流（7个）
详见 PROJECT_ALIGNMENT.md

## 新增工作流

### 8. image-generate（文生图）
- **功能**：根据文本描述生成商品图片
- **输入**：
  - `prompt` (string, 必填)：图片描述
  - `style` (string, 可选)：风格（产品照/生活方式/创意合成）
  - `width` (integer, 默认1024)
  - `height` (integer, 默认1024)
  - `product_id` (integer, 可选)：关联产品
- **输出**：
  - `image_url` (string)：生成图片URL（临时签名）
  - `width` (integer)
  - `height` (integer)
- **模型**：扣子内置文生图模型 或 火山引擎文生图API
- **用途**：素材不足时AI生成补充素材，如产品场景图、背景图

### 9. image-to-video（图生视频）
- **功能**：根据图片+描述生成短视频片段
- **输入**：
  - `image_url` (string, 必填)：源图片URL
  - `prompt` (string, 必填)：画面描述+运动指令
  - `duration` (float, 默认5.0)：视频时长(秒)
  - `has_speaking` (boolean, 默认false)
- **输出**：
  - `video_url` (string)：生成视频URL（临时签名）
  - `duration` (float)
- **模型**：Seedance-1.5-pro（支持图生视频模式）
- **用途**：将产品图片转化为动态视频片段，比纯文生视频更贴合商品

## 工作流调用顺序（更新）

完整pipeline：
①material-embed → ②query-generate → ③material-search → ④script-generate → ⑤tts-generate → ⑥video-generate → ⑦video-compose

补充工作流（按需调用）：
- image-generate：素材不足时在①②之间插入
- image-to-video：创作时替代⑥video-generate，用商品图直接生视频

## video-analyze（视频分析，用于爆款拆解）
- **功能**：分析视频结构，输出拆解报告
- **输入**：
  - `video_url` (string, 必填)：视频URL
  - `analysis_type` (string, 默认"full")：full/quick
- **输出**：
  - `hook_method` (string)：Hook手法
  - `selling_points` (array)：卖点列表
  - `storyboard` (array)：分镜拆解（每段含time_range/description/camera_movement）
  - `style` (string)：风格标签
  - `bgm_type` (string)：BGM类型
  - `overall_rating` (string)：整体评价
- **模型**：Seed-2.0-pro（视频理解）
- **用途**：爆款视频库的结构化分析，方法论提炼的数据来源
