import { useState } from 'react'
import { Card, Form, Select, Input, Button, Upload, message } from 'antd'
import { UploadOutlined, InboxOutlined } from '@ant-design/icons'
import { uploadMaterial } from '../../utils/api'
import { useNavigate } from 'react-router-dom'
import type { UploadFile } from 'antd'

export default function MaterialUpload() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])

  const onFinish = async (values: any) => {
    const fd = new FormData()
    fd.append('material_type', values.material_type || 'product')
    fd.append('input_type', values.material_type || 'image')
    if (values.category) fd.append('category', values.category)
    if (fileList.length > 0) fd.append('file', fileList[0].originFileObj as Blob)

    try {
      // API 会从文件内容自动生成 image_url
      await uploadMaterial(fd)
      message.success('上传成功')
      navigate('/material')
    } catch {
      message.error('上传失败')
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
          <Upload.Dragger
            fileList={fileList}
            beforeUpload={(file) => { setFileList([file]); return false }}
            onRemove={() => setFileList([])}
            maxCount={1}
            accept="image/*,video/*"
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          </Upload.Dragger>
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">提交</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate('/material')}>返回</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
