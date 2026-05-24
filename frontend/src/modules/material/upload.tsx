import { Card, Form, Select, Input, Button, message } from 'antd'
import { uploadMaterial } from '../../utils/api'
import { useNavigate } from 'react-router-dom'
export default function MaterialUpload() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const onFinish = async (values: any) => {
    try { await uploadMaterial(values); message.success('上传成功'); navigate('/material') }
    catch { message.error('上传失败') }
  }
  return (
    <Card title="上传素材">
      <Form form={form} onFinish={onFinish} layout="vertical" style={{ maxWidth: 600 }}>
        <Form.Item name="material_type" label="素材类型" rules={[{ required: true }]}>
          <Select options={[{ value: 'image', label: '图片' }, { value: 'video', label: '视频' }, { value: 'text', label: '文本' }]} />
        </Form.Item>
        <Form.Item name="category" label="分类"><Input placeholder="如：美妆、食品、数码" /></Form.Item>
        <Form.Item><Button type="primary" htmlType="submit">提交</Button><Button style={{ marginLeft: 8 }} onClick={() => navigate('/material')}>返回</Button></Form.Item>
      </Form>
    </Card>
  )
}
