import { useState, useEffect } from 'react'
import { Table, Button, Tag, Card, message, Modal, Descriptions, Spin, Select } from 'antd'
import { DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { getMaterials, deleteMaterial } from '../../utils/api'
import type { Material } from './types'
import { useNavigate } from 'react-router-dom'

export default function MaterialList() {
  const [materials, setMaterials] = useState<Material[]>([])
  const [loading, setLoading] = useState(false)
  const [filterType, setFilterType] = useState<string>('all')
  const [embedModal, setEmbedModal] = useState<{ visible: boolean; data: any; loading: boolean }>({ visible: false, data: null, loading: false })
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

  const showEmbedding = async (id: number) => {
    setEmbedModal({ visible: true, data: null, loading: true })
    try {
      const res = await (await fetch(`/api/v1/materials/${id}/embedding`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })).json()
      setEmbedModal({ visible: true, data: res, loading: false })
    } catch {
      message.error('加载嵌入信息失败')
      setEmbedModal({ visible: false, data: null, loading: false })
    }
  }

  const renderEmbedStatus = (_: any, r: Material) => {
    const hasTags = r.tags && r.tags.length > 0
    return (
      <span>
        <Tag color={hasTags ? 'green' : 'orange'}>{hasTags ? '已完成' : '待处理'}</Tag>
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showEmbedding(r.id)}>查看</Button>
      </span>
    )
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', ellipsis: true, width: 140 },
    { title: '类型', dataIndex: 'material_type', render: (v: string) => <Tag color={v === 'audio' ? 'purple' : v === 'video' ? 'blue' : 'green'}>{v === 'audio' ? '🎵 BGM' : v}</Tag> },
    { title: '分类', render: (_: any, r: Material) => r.category ? <Tag>{r.category}</Tag> : null },
    { title: '标签', dataIndex: 'tags', render: (tags: string[]) => tags?.map(t => <Tag key={t}>{t}</Tag>) },
    { title: '来源', dataIndex: 'source', render: (v: string) => v ? <Tag>{v}</Tag> : null },
    { title: '嵌入状态', render: renderEmbedStatus },
    { title: '预览', dataIndex: 'image_url', render: (url: string, r: Material) => {
      if (!url) return null
      const fullUrl = url.startsWith('http') ? url : `http://114.117.242.17:3000${url}`
      if (r.material_type === 'audio') {
        return <span style={{ fontSize: 28, cursor: 'pointer' }} onClick={() => window.open(fullUrl, '_blank')}>🎵</span>
      }
      if (r.material_type === 'video' || (url && url.match(/\.(mp4|webm|mov)$/i))) {
        return <video src={fullUrl} style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }} onClick={() => window.open(fullUrl, '_blank')} />
      }
      return <img src={url} loading="lazy" alt="" style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }} onClick={() => window.open(fullUrl, '_blank')} />
    } },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString() : '' },
    { title: '操作', render: (_: any, r: Material) => (
      <Button danger icon={<DeleteOutlined />} size="small" onClick={() => handleDelete(r.id)} />
    ) },
  ]

  return (
    <Card title="素材管理" extra={<Button type="primary" onClick={() => navigate('/material/upload')}>上传素材</Button>}>
      <div style={{ marginBottom: 16 }}>
        <Select value={filterType} onChange={setFilterType} style={{ width: 140 }} options={[
          { value: 'all', label: '全部' },
          { value: 'image', label: '🖼 图片' },
          { value: 'video', label: '🎬 视频' },
          { value: 'audio', label: '🎵 音频/BGM' },
        ]} />
      </div>
      <Table dataSource={filterType === 'all' ? materials : materials.filter(m => m.material_type === filterType)} columns={columns} rowKey="id" loading={loading} />

      <Modal title="嵌入信息" open={embedModal.visible} onCancel={() => setEmbedModal({ visible: false, data: null, loading: false })} footer={null} width={700}>
        {embedModal.loading ? <Spin /> : embedModal.data ? (
          embedModal.data.audio_features && Object.keys(embedModal.data.audio_features).length > 0 ? (
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="🎵 风格" span={2}>
                <Tag color={embedModal.data.audio_features.mood === '轻快' ? 'green' : embedModal.data.audio_features.mood === '稳重' ? 'purple' : 'orange'}>
                  {embedModal.data.audio_features.mood === '轻快' ? '⚡ 轻快' : embedModal.data.audio_features.mood === '稳重' ? '🐢 稳重' : '➡ 中性'}
                </Tag>
                <Tag>轻快度: {embedModal.data.audio_features.lightness_score}/100</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="BPM"><Tag color="blue">{embedModal.data.audio_features.bpm}</Tag></Descriptions.Item>
              <Descriptions.Item label="时长">{embedModal.data.audio_features.duration}s</Descriptions.Item>
              <Descriptions.Item label="频谱质心">{embedModal.data.audio_features.spectral_centroid} Hz</Descriptions.Item>
              <Descriptions.Item label="过零率">{embedModal.data.audio_features.zero_crossing_rate}</Descriptions.Item>
              <Descriptions.Item label="频谱滚降点">{embedModal.data.audio_features.spectral_rolloff} Hz</Descriptions.Item>
              <Descriptions.Item label="BPM得分" span={1}>{embedModal.data.audio_features.features?.bpm_score}</Descriptions.Item>
              <Descriptions.Item label="质心得分">{embedModal.data.audio_features.features?.centroid_score}</Descriptions.Item>
              <Descriptions.Item label="过零率得分">{embedModal.data.audio_features.features?.zcr_score}</Descriptions.Item>
              {embedModal.data.audio_features.mfcc_mean && (
                <Descriptions.Item label="MFCC(13维)" span={2}>
                  <div style={{ fontSize: 11, color: '#666', wordBreak: 'break-all' }}>{embedModal.data.audio_features.mfcc_mean.join(', ')}</div>
                </Descriptions.Item>
              )}
            </Descriptions>
          ) : (
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="状态"><Tag color={embedModal.data.status === 'completed' ? 'green' : 'orange'}>{embedModal.data.status}</Tag></Descriptions.Item>
              {embedModal.data.tags?.length > 0 && <Descriptions.Item label="标签">{embedModal.data.tags.map((t: string) => <Tag key={t}>{t}</Tag>)}</Descriptions.Item>}
              {embedModal.data.video_tags?.length > 0 && <Descriptions.Item label="视频标签">{embedModal.data.video_tags.map((t: string) => <Tag key={t}>{t}</Tag>)}</Descriptions.Item>}
              {embedModal.data.scenes?.length > 0 && (
                <Descriptions.Item label="场景">
                  {embedModal.data.scenes.map((s: any, i: number) => (
                    <div key={i} style={{ marginBottom: 8, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
                      <div><b>场景 {s.scene_id}</b> <Tag>{s.time_range}</Tag></div>
                      <div style={{ fontSize: 12, color: '#666' }}>{s.description}</div>
                      {s.script && <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>剧本: {s.script}</div>}
                    </div>
                  ))}
                </Descriptions.Item>
              )}
              {embedModal.data.error && <Descriptions.Item label="错误"><span style={{ color: 'red' }}>{embedModal.data.error}</span></Descriptions.Item>}
            </Descriptions>
          )
        ) : <span>无数据</span>}
      </Modal>
    </Card>
  )
}
