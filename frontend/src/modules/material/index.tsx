import { useState, useEffect } from 'react'
import { Table, Button, Tag, Slider, Card, message } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'
import { getMaterials, deleteMaterial } from '../../utils/api'
import type { Material } from './types'
import { useNavigate } from 'react-router-dom'

export default function MaterialList() {
  const [materials, setMaterials] = useState<Material[]>([])
  const [loading, setLoading] = useState(false)
  const [threshold, setThreshold] = useState(0.6)
  const navigate = useNavigate()
  const loadMaterials = async () => {
    setLoading(true)
    try { const res: any = await getMaterials(); setMaterials(res.items || res || []) }
    catch { message.error('加载素材失败') }
    setLoading(false)
  }
  useEffect(() => { loadMaterials() }, [])
  const handleDelete = async (id: number) => {
    try { await deleteMaterial(id); message.success('删除成功'); loadMaterials() }
    catch { message.error('删除失败') }
  }
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '类型', dataIndex: 'material_type', render: (v: string) => <Tag color={v === 'video' ? 'blue' : v === 'image' ? 'green' : 'orange'}>{v}</Tag> },
    { title: '标签', dataIndex: 'tags', render: (tags: string[]) => tags?.map(t => <Tag key={t}>{t}</Tag>) },
    { title: '来源', dataIndex: 'source', render: (v: string) => v ? <Tag>{v}</Tag> : null },
    { title: '预览', dataIndex: 'image_url', render: (url: string) => url ? <img src={url} loading="lazy" alt="" style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 4 }} /> : null },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString() : '' },
    { title: '操作', render: (_: any, r: Material) => <Button danger icon={<DeleteOutlined />} size="small" onClick={() => handleDelete(r.id)} /> },
  ]
  return (
    <Card title="素材管理" extra={<Button type="primary" onClick={() => navigate('/material/upload')}>上传素材</Button>}>
      <div style={{ marginBottom: 16 }}>
        <span>相似度阈值: {threshold}</span>
        <Slider min={0.3} max={0.95} step={0.05} value={threshold} onChange={setThreshold} style={{ width: 300 }} />
      </div>
      <Table dataSource={materials} columns={columns} rowKey="id" loading={loading} />
    </Card>
  )
}
