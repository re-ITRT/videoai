import { useState, useEffect } from 'react'
import { List, Button, Card, Input, Select, Slider, Modal, Space, message, Tag } from 'antd'
import { PlusOutlined, RightOutlined, PlayCircleOutlined } from '@ant-design/icons'
import request from '../../utils/request'

const { TextArea } = Input

export default function StudioPage() {
  const [sessions, setSessions] = useState<any[]>([])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessionModal, setSessionModal] = useState(false)
  const [sessionTitle, setSessionTitle] = useState('')

  const [products, setProducts] = useState<any[]>([])
  const [selectedProduct, setSelectedProduct] = useState<any>(null)
  const [productModal, setProductModal] = useState(false)
  const [productTitle, setProductTitle] = useState('')
  const [productContent, setProductContent] = useState('')

  const [materials, setMaterials] = useState<any[]>([])
  const [threshold, setThreshold] = useState(30)
  const [selectedMaterials, setSelectedMaterials] = useState<number[]>([])
  const [collections, setCollections] = useState<any[]>([])

  const [templates, setTemplates] = useState<string[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [selectedScript, setSelectedScript] = useState('')

  const [generating, setGenerating] = useState<string | null>(null)

  // 加载/创建 Session（复用 agent_sessions 表）
  const loadSessions = async () => {
    try { setSessions((await request.get('/agent/sessions')) || []) } catch {}
  }

  const createSession = async () => {
    const res: any = await request.post('/agent/sessions', { title: sessionTitle || '新工作流' })
    setSessions([res, ...sessions])
    setSessionId(res.id)
    setSessionModal(false)
    setSessionTitle('')
    setProducts([])
    setCollections([])
  }

  const deleteSession = async (sid: number) => {
    try {
      await request.delete(`/agent/sessions/${sid}`)
      setSessions(sessions.filter((s: any) => s.id !== sid))
      if (sessionId === sid) setSessionId(null)
    } catch { message.error('删除失败') }
  }

  useEffect(() => { loadSessions() }, [])

  useEffect(() => {
    request.get('/workflows/prompts').then((r: any) => setTemplates(Object.keys(r?.templates || {}))).catch(() => {})
    request.post('/studio/materials/search', { threshold: 30, tags: [] }).then((r: any) => setMaterials(r?.materials || [])).catch(() => {})
  }, [])

  const loadCollections = async () => {
    if (!sessionId) return
    try { setCollections((await request.get(`/studio/material-collections?session_id=${sessionId}`)) || []) } catch {}
  }

  const addProduct = async () => {
    if (!productContent.trim()) return
    await request.post('/studio/products', { session_id: sessionId, title: productTitle || '未命名', content: productContent })
    message.success('产品已添加')
    setProductModal(false)
    setProductTitle('')
    setProductContent('')
    searchProducts()
  }

  const searchProducts = async () => {
    if (!sessionId) return
    try { setProducts((await request.get(`/studio/products?session_id=${sessionId}`)) || []) } catch {}
  }

  const createCollection = async () => {
    if (selectedMaterials.length === 0) return message.warning('请先选择素材')
    setGenerating('collection')
    try {
      await request.post('/studio/material-collections', { session_id: sessionId, material_ids: selectedMaterials, threshold })
      message.success('素材集合已创建')
      loadCollections()
    } catch { message.error('创建失败') }
    setGenerating(null)
  }

  const generateScript = async () => {
    if (!selectedProduct) return message.warning('请先选择产品介绍')
    if (!selectedTemplate) return message.warning('请选择剧本模板')
    setGenerating('script')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, { message: `根据以下产品信息生成剧本：${selectedProduct.content}`, auto_mode: false })
      message.success('剧本已生成')
      setSelectedScript(`script_${sessionId}`)
    } catch { message.error('生成失败') }
    setGenerating(null)
  }

  const generateVideo = async () => {
    if (!selectedScript) return message.warning('请选择剧本')
    setGenerating('video')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, { message: `用剧本 ${selectedScript} 生成视频`, auto_mode: false })
      message.success('视频生成中...')
    } catch { message.error('生成失败') }
    setGenerating(null)
  }

  const composeVideo = async () => {
    setGenerating('compose')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, { message: '合成最终视频', auto_mode: false })
      message.success('合成完成')
    } catch { message.error('合成失败') }
    setGenerating(null)
  }

  const StepBox = ({ title, extra, children }: any) => (
    <Card title={title} size="small" extra={extra} style={{ width: 280, flexShrink: 0, minHeight: 400 }}>{children}</Card>
  )

  const Arrow = () => (
    <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px' }}>
      <RightOutlined style={{ fontSize: 24, color: '#1677ff' }} />
    </div>
  )

  const GenButton = ({ label, loading, onClick }: any) => (
    <div style={{ textAlign: 'center', margin: '8px 0' }}>
      <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={onClick} style={{ width: 180 }}>{label}</Button>
    </div>
  )

  return (
    <div style={{ padding: 0, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 180px)' }}>
      {/* Session 选择栏 */}
      <div style={{ display: 'flex', gap: 6, padding: '8px 12px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', alignItems: 'center', overflow: 'auto' }}>
        <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setSessionModal(true)}>新建</Button>
        {sessions.map((s: any) => (
          <Tag key={s.id} color={sessionId === s.id ? 'blue' : 'default'}
            style={{ cursor: 'pointer', margin: 0 }}
            onClick={() => { setSessionId(s.id); setProducts([]); setCollections([]) }}
            closable onClose={() => deleteSession(s.id)}
          >{s.title}</Tag>
        ))}
        {!sessionId && <span style={{ color: '#999', fontSize: 12 }}>选择或新建一个工作流</span>}
      </div>

      {/* 5步流程 */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
      <div style={{ display: 'flex', overflow: 'auto', gap: 0, paddingBottom: 16 }}>
        {/* 1. 产品介绍 */}
        <div>
          <StepBox title="产品介绍" extra={<Button size="small" icon={<PlusOutlined />} onClick={() => setProductModal(true)} />}>
            <List size="small" dataSource={products} renderItem={(p: any) => (
              <List.Item onClick={() => setSelectedProduct(p)} style={{ cursor: 'pointer', background: selectedProduct?.id === p.id ? '#e6f4ff' : undefined }}>
                {p.title || p.content?.slice(0, 30)}
              </List.Item>
            )} />
          </StepBox>
          <GenButton label="生成素材集合" loading={generating === 'collection'} onClick={createCollection} />
        </div>

        <Arrow />

        {/* 2. 素材选择 */}
        <div>
          <StepBox title="素材选择" extra={
            <Space>
              <span style={{ fontSize: 12 }}>相似度</span>
              <Slider style={{ width: 80 }} min={0} max={100} value={threshold} onChange={setThreshold} />
              <span style={{ fontSize: 12 }}>{threshold}%</span>
            </Space>
          }>
            <List size="small" dataSource={materials} renderItem={(m: any) => (
              <List.Item style={{ cursor: 'pointer', background: selectedMaterials.includes(m.id) ? '#e6f4ff' : undefined }}
                onClick={() => setSelectedMaterials(p => p.includes(m.id) ? p.filter(x => x !== m.id) : [...p, m.id])}>
                <Space>
                  {m.image_url && <img src={m.image_url} style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 4 }} />}
                  <span style={{ fontSize: 12 }}>{(m.tags || []).join(', ') || `素材 #${m.id}`}</span>
                </Space>
              </List.Item>
            )} />
          </StepBox>
          <GenButton label="生成素材集合" loading={generating === 'collection'} onClick={createCollection} />
        </div>

        <Arrow />

        {/* 3. 剧本生成 */}
        <div>
          <StepBox title="剧本生成" extra={
            <Select placeholder="模板" size="small" style={{ width: 100 }} value={selectedTemplate} onChange={setSelectedTemplate}
              options={templates.map(t => ({ value: t, label: t }))} />
          }>
            <List size="small" dataSource={collections} renderItem={(c: any) => (
              <List.Item style={{ fontSize: 12 }}>{c.name} ({c.material_ids?.length || 0} 素材)</List.Item>
            )} />
          </StepBox>
          <GenButton label="生成剧本" loading={generating === 'script'} onClick={generateScript} />
        </div>

        <Arrow />

        {/* 4. 视频生成 */}
        <div>
          <StepBox title="视频生成" />
          <GenButton label="生成视频" loading={generating === 'video'} onClick={generateVideo} />
        </div>

        <Arrow />

        {/* 5. 视频合成 */}
        <div>
          <StepBox title="视频合成" />
          <GenButton label="合成视频" loading={generating === 'compose'} onClick={composeVideo} />
        </div>
      </div>
      </div>

      <Modal title="新建工作流" open={sessionModal} onOk={createSession} onCancel={() => setSessionModal(false)}>
        <Input placeholder="工作流名称" value={sessionTitle} onChange={e => setSessionTitle(e.target.value)} onPressEnter={createSession} />
      </Modal>

      <Modal title="添加产品介绍" open={productModal} onOk={addProduct} onCancel={() => setProductModal(false)} width={600}>
        <Input placeholder="产品名称（选填）" value={productTitle} onChange={e => setProductTitle(e.target.value)} style={{ marginBottom: 8 }} />
        <TextArea rows={12} placeholder="粘贴完整的产品介绍文案..." value={productContent} onChange={e => setProductContent(e.target.value)} />
      </Modal>
    </div>
  )
}
