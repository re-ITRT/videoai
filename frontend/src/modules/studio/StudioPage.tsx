import { useState, useEffect } from 'react'
import { Select, Button, Card, Input, Slider, Modal, Space, message, List, Popconfirm } from 'antd'
import { PlusOutlined, RightOutlined, PlayCircleOutlined, DeleteOutlined } from '@ant-design/icons'
import request from '../../utils/request'

const { TextArea } = Input

export default function StudioPage() {
  const [sessions, setSessions] = useState<any[]>([])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessionModal, setSessionModal] = useState(false)
  const [sessionTitle, setSessionTitle] = useState('')

  // 所有工作流状态存在 session 文件夹的 workflow_state.json 里
  const [state, setState] = useState<any>({ products: [], selected_product_id: null, threshold: 30, selected_material_ids: [], collections: [], selected_template: '' })

  const [materials, setMaterials] = useState<any[]>([])
  const [productModal, setProductModal] = useState(false)
  const [productTitle, setProductTitle] = useState('')
  const [productContent, setProductContent] = useState('')
  const [templates, setTemplates] = useState<string[]>([])
  const [generating, setGenerating] = useState<string | null>(null)

  // 加载 Session 列表
  useEffect(() => {
    request.get('/agent/sessions').then((r: any) => setSessions(r || [])).catch(() => {})
    request.get('/workflows/prompts').then((r: any) => setTemplates(Object.keys(r?.templates || {}))).catch(() => {})
  }, [])

  // 切换 Session 时加载状态
  useEffect(() => {
    if (!sessionId) return
    request.get(`/studio/state/${sessionId}`).then((r: any) => {
      setState(r || {})
      setMaterials(r?.cached_materials || [])
    }).catch(() => {})
    request.post('/studio/materials/search', { threshold: 30, tags: [] }).then((r: any) => setMaterials(r?.materials || [])).catch(() => {})
  }, [sessionId])

  // 保存状态到文件
  const saveState = async (patch: any) => {
    const merged = { ...state, ...patch }
    setState(merged)
    if (sessionId) {
      request.put(`/studio/state/${sessionId}`, merged).catch(() => {})
    }
  }

  const createSession = async () => {
    const res: any = await request.post('/agent/sessions', { title: sessionTitle || '新工作流' })
    setSessions([res, ...sessions])
    setSessionId(res.id)
    setSessionModal(false)
    setSessionTitle('')
  }

  const deleteSession = async (sid: number) => {
    try {
      await request.delete(`/agent/sessions/${sid}`)
      setSessions(sessions.filter((s: any) => s.id !== sid))
      if (sessionId === sid) setSessionId(null)
    } catch { message.error('删除失败') }
  }

  const addProduct = async () => {
    if (!productContent.trim()) return
    const pid = Date.now()
    const newProduct = { id: pid, title: productTitle || '未命名', content: productContent }
    saveState({ products: [...state.products, newProduct], selected_product_id: pid })
    setProductModal(false)
    setProductTitle('')
    setProductContent('')
    message.success('产品已添加')
  }

  const createCollection = async () => {
    if (state.selected_material_ids.length === 0) return message.warning('请先选择素材')
    setGenerating('collection')
    saveState({
      collections: [...state.collections, {
        id: Date.now(),
        name: `素材集合_${state.collections.length + 1}`,
        material_ids: state.selected_material_ids,
        threshold: state.threshold,
      }]
    })
    message.success('素材集合已创建')
    setGenerating(null)
  }

  const genScript = async () => {
    const prod = state.products.find((p: any) => p.id === state.selected_product_id)
    if (!prod) return message.warning('请选择产品介绍')
    if (!state.selected_template) return message.warning('请选择模板')
    const coll = state.collections.find((c: any) => c.id === state.selected_collection_id)
    if (!coll) return message.warning('请选择素材集合')
    setGenerating('生成剧本')
    try {
      // 获取素材详情（ID+描述+标签）
      const matDetails = materials
        .filter((m: any) => coll.material_ids.includes(m.id))
        .map((m: any) => ({ id: m.id, description: m.tags?.join(', ') || '', tags: m.tags || [] }))
      const res: any = await request.post('/studio/generate-script', {
        product_content: prod.content,
        template: state.selected_template,
        materials: matDetails,
      })
      message.success('剧本已生成')
      console.log('剧本结果:', res)
    } catch {
      message.error('生成失败')
    }
    setGenerating(null)
  }

  const semanticSearch = async () => {
    const prod = state.products.find((p: any) => p.id === state.selected_product_id)
    if (!prod) return message.warning('请先选择产品介绍')
    setGenerating('嵌入搜索')
    try {
      const res: any = await request.post('/studio/semantic-search', { product_info: { title: prod.title, content: prod.content }, threshold: state.threshold })
      setMaterials(res?.materials || [])
      saveState({ cached_materials: res?.materials || [] })
      if (res?.total > 0) message.success(`找到 ${res.total} 个相关素材`)
      else message.info('未找到匹配素材')
    } catch { message.error('搜索失败') }
    setGenerating(null)
  }

  const genVideo = async () => {
    setGenerating('video')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, { message: `用剧本 script_${sessionId}.json 生成视频`, auto_mode: false })
      message.success('视频生成中...')
    } catch { message.error('生成失败') }
    setGenerating(null)
  }

  const composeVid = async () => {
    setGenerating('compose')
    try {
      await request.post(`/agent/sessions/${sessionId}/chat`, { message: '合成最终视频', auto_mode: false })
      message.success('合成完成')
    } catch { message.error('合成失败') }
    setGenerating(null)
  }

  const StepBox = ({ title, extra, children }: any) => (
    <Card title={title} size="small" extra={extra} style={{ width: 280, flexShrink: 0, minHeight: 380 }}>{children}</Card>
  )
  const Arrow = () => <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px' }}><RightOutlined style={{ fontSize: 24, color: '#1677ff' }} /></div>
  const GenBtn = ({ label, onClick }: any) => (
    <div style={{ textAlign: 'center', margin: '8px 0' }}>
      <Button type="primary" icon={<PlayCircleOutlined />} loading={generating === label} onClick={onClick} style={{ width: 180 }}>{label}</Button>
    </div>
  )

  return (
    <div style={{ padding: 0, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 180px)' }}>
      {/* Session 切换栏 */}
      <div style={{ display: 'flex', gap: 8, padding: '8px 12px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', alignItems: 'center' }}>
        <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setSessionModal(true)}>新建</Button>
        <Select placeholder="选择工作流" style={{ width: 220 }} size="small" value={sessionId} onChange={setSessionId}
          options={sessions.map((s: any) => ({ value: s.id, label: s.title }))} />
        {sessionId && (
          <Popconfirm title="确定删除？" onConfirm={() => deleteSession(sessionId)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        )}
      </div>

      {/* 5步流程 */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
      <div style={{ display: 'flex', overflow: 'auto', gap: 0, paddingBottom: 16 }}>
        {/* 1. 产品介绍 */}
        <div>
          <StepBox title="产品介绍" extra={<Button size="small" icon={<PlusOutlined />} onClick={() => setProductModal(true)} />}>
            <List size="small" dataSource={state.products} renderItem={(p: any) => (
              <List.Item onClick={() => saveState({ selected_product_id: p.id })}
                style={{ cursor: 'pointer', background: state.selected_product_id === p.id ? '#e6f4ff' : undefined }}>
                {p.title || p.content?.slice(0, 30)}
              </List.Item>
            )} />
          </StepBox>
          <GenBtn label="嵌入搜索" onClick={semanticSearch} />
        </div>
        <Arrow />

        {/* 2. 素材选择 */}
        <div>
          <StepBox title="素材选择" extra={
            <Space><span style={{ fontSize: 12 }}>相似度</span>
              <Slider style={{ width: 80 }} min={0} max={100} value={state.threshold} onChange={v => saveState({ threshold: v })} />
              <span style={{ fontSize: 12 }}>{state.threshold}%</span></Space>
          }>
            <List size="small" dataSource={materials} renderItem={(m: any) => (
              <List.Item style={{ cursor: 'pointer', background: state.selected_material_ids.includes(m.id) ? '#e6f4ff' : undefined }}
                onClick={() => saveState({
                  selected_material_ids: state.selected_material_ids.includes(m.id)
                    ? state.selected_material_ids.filter((x: number) => x !== m.id) : [...state.selected_material_ids, m.id]
                })}>
                <Space>
                  {m.image_url && <img src={m.image_url} style={{ width: 36, height: 36, objectFit: 'cover', borderRadius: 4 }} />}
                  <span style={{ fontSize: 12 }}>{m.id}</span>
                </Space>
              </List.Item>
            )} />
          </StepBox>
          <GenBtn label="生成素材集合" onClick={createCollection} />
        </div>
        <Arrow />

        {/* 2.5 素材集合 */}
        <div>
          <StepBox title="素材集合">
            <List size="small" dataSource={state.collections} renderItem={(c: any) => (
              <List.Item onClick={() => saveState({ selected_collection_id: c.id })}
                style={{ cursor: 'pointer', background: state.selected_collection_id === c.id ? '#e6f4ff' : undefined }}>
                <span style={{ fontSize: 12 }}>{c.name} ({c.material_ids?.length || 0} 素材)</span>
              </List.Item>
            )} />
            {state.collections.length === 0 && <div style={{ color: '#999', fontSize: 12, textAlign: 'center', padding: 20 }}>选素材后点击生成</div>}
          </StepBox>
        </div>
        <Arrow />

        {/* 3. 剧本生成 */}
        <div>
          <StepBox title="剧本生成" extra={
            <Select placeholder="模板" size="small" style={{ width: 100 }} value={state.selected_template}
              onChange={v => saveState({ selected_template: v })}
              options={templates.map(t => ({ value: t, label: t }))} />
          }>
            <div style={{ fontSize: 12, color: '#999' }}>选产品+模板后点击生成</div>
          </StepBox>
          <GenBtn label="生成剧本" onClick={genScript} />
        </div>
        <Arrow />

        {/* 4. 视频生成 */}
        <div>
          <StepBox title="视频生成" />
          <GenBtn label="生成视频" onClick={genVideo} />
        </div>
        <Arrow />

        {/* 5. 视频合成 */}
        <div>
          <StepBox title="视频合成" />
          <GenBtn label="合成视频" onClick={composeVid} />
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
