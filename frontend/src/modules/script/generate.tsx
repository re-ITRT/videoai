import { Card, Form, Select, InputNumber, Button, Radio, message } from 'antd'
import { generateScript } from '../../utils/api'
import { useNavigate } from 'react-router-dom'
export default function ScriptGenerate() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const onFinish = async (values: any) => {
    try { const res: any = await generateScript(values); message.success('剧本生成成功'); navigate(`/script/${res.id}`) }
    catch { message.error('生成失败') }
  }
  return (
    <Card title="生成剧本">
      <Form form={form} onFinish={onFinish} layout="vertical" style={{ maxWidth: 600 }}>
        <Form.Item name="mode" label="生成模式" rules={[{ required: true }]}>
          <Radio.Group><Radio value="auto">全自动</Radio><Radio value="semi">半自动</Radio><Radio value="manual">手动编排</Radio><Radio value="reference">参考视频</Radio></Radio.Group>
        </Form.Item>
        <Form.Item name="video_style" label="视频风格">
          <Select options={[{ value: 'professional', label: '专业评测' },{ value: 'lifestyle', label: '生活场景' },{ value: 'trending', label: '爆款节奏' },{ value: 'story', label: '故事叙述' }]} />
        </Form.Item>
        <Form.Item name="total_duration" label="目标时长(秒)" initialValue={15}><InputNumber min={5} max={60} /></Form.Item>
        <Form.Item><Button type="primary" htmlType="submit">生成剧本</Button><Button style={{ marginLeft: 8 }} onClick={() => navigate('/script')}>返回</Button></Form.Item>
      </Form>
    </Card>
  )
}
