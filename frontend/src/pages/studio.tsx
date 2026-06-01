import { useState, useEffect } from 'react'
import { Button, Card, Input, Select, Slider, Modal, Tag, Space, message, Spin, List, Descriptions } from 'antd'
import { PlusOutlined, RightOutlined, PlayCircleOutlined } from '@ant-design/icons'
import request from '../utils/request'

const { TextArea } = Input

export default function StudioPage() {
  const [sessionId, setSessionId] = useState<number>(0)
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
  const [scripts, setScripts] = useState<any[]>([])
  const [selectedScript, setSelectedScript] = useState('')

  const [videoCollections, setVideoCollections] = useState<any[]>([])
  const [selectedVideoCol, setSelectedVideoCol] = useState<number | null>(null)
  const [_fv, _sfv] = useState<any[]>([])

  const [generating, setGenerating] = useState<string | null>(null)

  // 初始化 session
  useEffect(() => {
    const sid = Date.now()
    setSessionId(sid)
    loadTemplates()
    loadMaterials()
  }, [])

  const loadTemplates = async () => {
    try {
      const res: any = await request.get('/workflows/prompts')
      setTemplates(Object.keys(res?.templates || {}))
    } catch {}
  }

  const loadMaterials = async () => {
    try {
      const res: any = await request.post('/studio/materials/search', { threshold: 30, tags: [] })
      setMaterials(res?.materials || [])
    } catch {}
  }

  const loadCollections = async () => {
    if (!sessionId) return
    try {
      const res: any = await request.get(`/studio/material-collections?session_id=${sessionId}`)
      setCollections(res || [])
    } catch {}
  }

  // ── 产品 ──
  const addProduct = async () => {
    if (!productContent.trim()) return
      await request.post('/studio/products', { session_id: sessionId, title: productTitle || '未命名', content: productContent })
    message.success('产品已添加')
    setProductModal(false)
    setProductTitle('')
    setProductContent('')
    loadProducts()
  }

  const loadProducts = async () => {
    if (!sessionId) return
    try {
      const res: any = await request.get(`/studio/products?session_id=${sessionId}`)
      setProducts(res || [])
    } catch {}
  }

  // ── 素材搜索 ──
  // const searchMaterials = async () => {
    try {
      const res: any = await request.post('/studio/materials/search', { threshold, tags: [] })
      setMaterials(res?.materials || [])
    } catch {}
  }

  // ── 素材集合 ──
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

  // ── 剧本生成 ──
  const generateScript = async () => {
    if (!selectedProduct) return message.warning('请先选择产品介绍')
    if (!selectedTemplate) return message.warning('请选择剧本模板')
    setGenerating('script')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, {
        message: `根据以下产品信息生成剧本：${selectedProduct.content}`,
        auto_mode: false,
      })
      message.success('剧本已生成')
      // 重新加载脚本列表
      setSelectedScript(`script_${sessionId}`)
    } catch { message.error('生成失败') }
    setGenerating(null)
  }

  // ── 视频生成 ──
  const generateVideo = async () => {
    if (!selectedScript) return message.warning('请选择剧本')
    setGenerating('video')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, {
        message: `用剧本 ${selectedScript} 生成视频`,
        auto_mode: false,
      })
      message.success('视频生成中...')
    } catch { message.error('生成失败') }
    setGenerating(null)
  }

  // ── 视频合成 ──
  const composeVideo = async () => {
    setGenerating('compose')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, {
        message: '合成最终视频',
        auto_mode: false,
      })
      message.success('合成完成')
    } catch { message.error('合成失败') }
    setGenerating(null)
  }

  // ── Step 组件 ──
  const StepBox = ({ title, extra, children, width = 280 }: any) => (
    <Card title={title} size="small" extra={extra} style={{ width, flexShrink: 0, minHeight: 400 }}>
      {children}
    </Card>
  )

  const Arrow = () => (
    <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px' }}>
      <RightOutlined style={{ fontSize: 24, color: '#1677ff' }} />
    </div>
  )

  const GenButton = ({ label, loading, onClick }: any) => (
    <div style={{ textAlign: 'center', margin: '8px 0' }}>
      <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={onClick} style={{ width: 180 }}>
        {label}
      </Button>
    </div>
  )

  return (
    <div style={{ padding: 16 }}>
      {/* 横向步骤 */}
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
          <GenButton label="生成素材" loading={generating === 'collection'} onClick={createCollection} />
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
              <List.Item
                style={{ cursor: 'pointer', background: selectedMaterials.includes(m.id) ? '#e6f4ff' : undefined }}
                onClick={() => setSelectedMaterials(prev => prev.includes(m.id) ? prev.filter(x => x !== m.id) : [...prev, m.id])}
              >
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
            {scripts.length > 0 && <div style={{ marginTop: 8 }}><Tag color="green">已有 {scripts.length} 个剧本</Tag></div>}
          </StepBox>
          <GenButton label="生成剧本" loading={generating === 'script'} onClick={generateScript} />
        </div>

        <Arrow />

        {/* 4. 视频生成 */}
        <div>
          <StepBox title="视频生成">
            <div style={{ fontSize: 12, color: '#666' }}>选择剧本后点击生成</div>
          </StepBox>
          <GenButton label="生成视频" loading={generating === 'video'} onClick={generateVideo} />
        </div>

        <Arrow />

        {/* 5. 视频合成 */}
        <div>
          <StepBox title="视频合成">
            <div style={{ fontSize: 12, color: '#666' }}>视频片段就绪后可合成最终视频</div>
          </StepBox>
          <GenButton label="合成视频" loading={generating === 'compose'} onClick={composeVideo} />
        </div>

      </div>

      {/* 产品编辑弹窗 */}
      <Modal title="添加产品介绍" open={productModal} onOk={addProduct} onCancel={() => setProductModal(false)} width={600}>
        <Input placeholder="产品名称（选填）" value={productTitle} onChange={e => setProductTitle(e.target.value)} style={{ marginBottom: 8 }} />
        <TextArea rows={12} placeholder="粘贴完整的产品介绍文案..." value={productContent} onChange={e => setProductContent(e.target.value)} />
      </Modal>
    </div>
  )
}
