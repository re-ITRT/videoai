import { useState } from 'react'
import { Card, Form, Select, Input, Button, Upload, message, Tag } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { uploadMaterial } from '../../utils/api'
import { useNavigate } from 'react-router-dom'
import type { UploadFile } from 'antd'

const CATEGORIES = ['产品', '场景', '人物', '动物', '美食', '科技', '其他']

export default function MaterialUpload() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [mtype, setMtype] = useState<string>('image')
  const [category, setCategory] = useState<string>('其他')
  const [detectedType, setDetectedType] = useState<string>('')

  // 根据文件后缀自动检测类型
  const detectType = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase() || ''
    if (['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac'].includes(ext)) return 'audio'
    if (['mp4', 'webm', 'mov', 'avi', 'mkv'].includes(ext)) return 'video'
    return 'image'
  }

  const onFinish = async (values: any) => {
    if (fileList.length === 0) { message.warning('请选择文件'); return }
    if (uploading) return

    setUploading(true)
    const fileObj = (fileList[0] as any).originFileObj || fileList[0]
    const autoType = detectType(fileObj.name || '')
    const fd = new FormData()
    fd.append('material_type', autoType)
    fd.append('input_type', autoType)
    fd.append('category', values.category || '其他')
    if (values.brief_description) fd.append('text_content', values.brief_description)
    if (values.product_name && values.product_name.trim()) fd.append('product_name', values.product_name)
    fd.append('file', fileObj)

    try {
      await uploadMaterial(fd)
      message.success('上传成功')
      navigate('/material')
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
        <Form.Item name="material_type" label="素材类型" initialValue="image">
          <Select onChange={(v) => setMtype(v)} options={[
            { value: 'image', label: '图片' },
            { value: 'video', label: '视频' },
            { value: 'audio', label: 'BGM/音频' },
          ]} />
          <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
            自动检测：{detectedType ? <Tag color={detectedType === 'audio' ? 'purple' : detectedType === 'video' ? 'blue' : 'green'}>{detectedType === 'audio' ? '🎵 BGM' : detectedType}</Tag> : '选择文件后自动识别'}
          </div>
        </Form.Item>

        <Form.Item name="category" label="分类" rules={[{ required: true }]} initialValue="其他">
          <Select onChange={(v) => setCategory(v)} options={CATEGORIES.map(c => ({ value: c, label: c }))} />
        </Form.Item>

        {category === '产品' && (
          <Form.Item name="product_name" label="产品名称" rules={[{ required: true, message: '请填写产品名称' }]}>
            <Input placeholder="请输入产品名称" />
          </Form.Item>
        )}

        {mtype === 'image' && (
          <Form.Item name="brief_description" label="描述（可选）">
            <Input.TextArea rows={3} placeholder="如：白色运动鞋 透气网面" />
          </Form.Item>
        )}

        <Form.Item label="选择文件">
          <Upload.Dragger
            fileList={fileList}
            beforeUpload={(f) => { setFileList([f]); setDetectedType(detectType(f.name)); return false }}
            onRemove={() => setFileList([])}
            maxCount={1}
            accept={mtype === 'image' ? 'image/*' : mtype === 'video' ? 'video/*' : 'audio/*'}
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
