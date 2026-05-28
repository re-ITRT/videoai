import { useState } from 'react'
import { Card, Form, Select, Input, Button, Upload, message } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { uploadMaterial } from '../../utils/api'
import { useNavigate } from 'react-router-dom'
import type { UploadFile } from 'antd'

export default function MaterialUpload() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)

  const onFinish = async (values: any) => {
    if (fileList.length === 0) { message.warning('请选择文件'); return }
    if (uploading) return

    setUploading(true)
    const fd = new FormData()
    fd.append('material_type', values.material_type || 'product')
    fd.append('input_type', values.material_type || 'image')
    fd.append('file', fileList[0].originFileObj as Blob)

    try {
      await uploadMaterial(fd)
      message.success('上传成功')
      navigate('/creation')  // 跳转到任务队列页
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '上传失败'
      message.error(typeof detail === 'string' ? detail : '上传失败')
    } finally {
      setUploading(false)
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
            beforeUpload={(f) => { setFileList([f]); return false }}
            onRemove={() => setFileList([])}
            maxCount={1}
            accept="image/*,video/*"
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          </Upload.Dragger>
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={uploading} disabled={uploading}>
            {uploading ? '上传中...' : '提交'}
          </Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate('/material')}>返回</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
