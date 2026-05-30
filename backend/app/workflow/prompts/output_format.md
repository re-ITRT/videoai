# 输出格式
仅返回如下格式的JSON，不要包含任何其他文本：
{
  "title": "剧本标题（不超过10字）",
  "style": "风格",
  "duration": 总时长,
  "scenes": [
    {
      "scene_id": 1,
      "duration": 10,
      "type": "product/scene/closing",
      "visual_desc": "画面描述（包含镜头语言、主体动作、环境）",
      "materials": [1, 3],
      "lines": [
        {
          "speaker": "旁白",
          "text": "想喝奶茶又怕长肉？",
          "tone": "亲切",
          "start_sec": 0,
          "end_sec": 3
        },
        {
          "speaker": "女生",
          "text": "哇这个也太好喝了吧！",
          "tone": "惊喜",
          "start_sec": 4,
          "end_sec": 6
        }
      ]
    }
  ]
}

## 字段说明
- title: 剧本标题（简洁有力，不超过10个字）
- style: 风格（与输入一致）
- duration: 总时长（与输入一致）
- scenes: 分镜列表
  - scene_id: 场景ID（从1开始递增）
  - duration: 场景时长（秒）
  - type: product（产品展示）/ scene（场景氛围）/ closing（结尾收束）
  - visual_desc: 画面描述（具体的镜头语言、主体动作、环境）
  - materials: 用到的素材ID数组（可为空）
  - lines: 台词时间轴列表（可为空）
    - speaker: 说话人（"旁白"或角色名）
    - text: 台词内容
    - tone: 语气语调
    - start_sec: 在该场景中开始秒数（从0开始）
    - end_sec: 在该场景中结束秒数（≤ duration - 0.5）
