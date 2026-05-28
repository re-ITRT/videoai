import { useState } from 'react'
import { Card, Form, Select, Input, Button, message } from 'antd'
import { uploadMaterial } from '../../utils/api'
import { useNavigate } from 'react-router-dom'

export default function MaterialUpload() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [file, setFile] = useState<File | null>(null)

  const onFinish = async (values: any) => {
    const fd = new FormData()
    fd.append('material_type', values.material_type || 'product')
    fd.append('input_type', values.material_type || 'image')
    if (file) fd.append('file', file)

    try {
      await uploadMaterial(fd)
      message.success('上传成功')
      navigate('/material')
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '上传失败'
      message.error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
  }

  return (
    <Card title="上传素材">
      <Form form={form} onFinish={onFinish} layout="vertical" style={{ maxWidth: 600 }}>
        <Form.Item name="material_type" label="素材类型" rules={[{ required: true }]}>
          <Select options={[{ value: 'image', label: '图片' }, { value: 'video', label: '视频' }, { value: 'text', label: '文本' }]} />
        </Form.Item>
        <Form.Item name="category" label="分类"><Input placeholder="如：美妆、食品、数码" /></Form.Item>
        <Form.Item label="选择文件">
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} accept="image/*,video/*" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">提交</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate('/material')}>返回</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
