import { useState, useEffect, useRef } from 'react'
import { Select, Button, Card, Input, Slider, Modal, Space, message, List, Collapse, Popconfirm } from 'antd'
import { PlusOutlined, RightOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined, VideoCameraOutlined, RobotOutlined } from '@ant-design/icons'
import request from '../../utils/request'
import ScriptEditor from '../agent/ScriptEditor'
import AiScriptEditor from '../agent/AiScriptEditor'

const { TextArea } = Input

export default function StudioPage() {
  const [sessions, setSessions] = useState<any[]>([])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const sessionIdRef = useRef(sessionId)
  sessionIdRef.current = sessionId
  const [sessionModal, setSessionModal] = useState(false)
  const [sessionTitle, setSessionTitle] = useState('')

  // 所有工作流状态存在 session 文件夹的 workflow_state.json 里
  const [state, setState] = useState<any>({
    products: [], selected_product_id: null, threshold: 30,
    selected_material_ids: [], collections: [], selected_template: '',
    clip_collections: [], selected_clip_collection_id: null,
    final_videos: [],
  })
  const stateRef = useRef(state)
  stateRef.current = state

  const [materials, setMaterials] = useState<any[]>([])
  const [allMaterials, setAllMaterials] = useState<any[]>([])  // 完整搜索结果（含相似度）
  const [localThreshold, setLocalThreshold] = useState(30)
  const [productModal, setProductModal] = useState(false)
  const [productTitle, setProductTitle] = useState('')
  const [productContent, setProductContent] = useState('')
  const [templates, setTemplates] = useState<string[]>([])
  const [generating, setGenerating] = useState<string | null>(null)
  const [scriptEditorOpen, setScriptEditorOpen] = useState(false)
  const [aiScriptEditorOpen, setAiScriptEditorOpen] = useState(false)

  // 加载 Session 列表
  useEffect(() => {
    request.get('/agent/sessions').then((r: any) => setSessions(r || [])).catch(() => {})
    request.get('/workflows/prompts').then((r: any) => setTemplates(Object.keys(r?.templates || {}))).catch(() => {})
  }, [])

  // 切换 Session 时加载状态
  useEffect(() => {
    if (!sessionId) return
    setMaterials([])  // 先清空
    Promise.all([
      request.get(`/studio/state/${sessionId}`),
      request.get(`/studio/clips/${sessionId}`).catch(() => ({ clips: [], final_videos: [] })),
    ]).then(([stateRes, clipsRes]: any[]) => {
      const merged = {
        ...(stateRes || {}),
        clip_collections: stateRes?.clip_collections || [],
        selected_clip_collection_id: stateRes?.selected_clip_collection_id || null,
        final_videos: clipsRes?.final_videos || [],
      }
      setState(merged)
      setLocalThreshold(merged.threshold || 30)
      if (merged.cached_materials?.length) {
        setAllMaterials(merged.cached_materials)
        setMaterials(merged.cached_materials)
      }
      // 持久化到 state 文件
      request.put(`/studio/state/${sessionId}`, merged).catch(() => {})
    }).catch(() => {})
  }, [sessionId])

  // 根据阈值实时筛选素材
  useEffect(() => {
    if (allMaterials.length > 0) {
      const t = localThreshold / 100
      setMaterials(allMaterials.filter((m: any) => (m.similarity || 0) >= t))
    }
  }, [allMaterials, localThreshold])

  // 刷新最终视频（不覆盖 clip_collections）
  const loadClips = async () => {
    const sid = sessionIdRef.current
    if (!sid) return
    try {
      const res: any = await request.get(`/studio/clips/${sid}`)
      saveState({ final_videos: res?.final_videos || [] })
    } catch {}
  }

  // 保存状态到文件（用 ref 避免闭包竞态）
  const saveState = async (patch: any) => {
    const merged = { ...stateRef.current, ...patch }
    setState(merged)
    const sid = sessionIdRef.current
    if (sid) {
      request.put(`/studio/state/${sid}`, merged).catch(() => {})
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
      const matDetails = materials
        .filter((m: any) => coll.material_ids.includes(m.id))
        .map((m: any) => ({ material_id: m.id, description: m.tags?.join(', ') || '', tags: m.tags || [] }))
      const res: any = await request.post('/studio/generate-script', {
        product_content: prod.content,
        template: state.selected_template,
        materials: matDetails,
        session_id: sessionId,
      })
      message.success('剧本已生成')
      saveState({ last_script: res })
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
      setAllMaterials(res?.materials || [])
      saveState({ cached_materials: res?.materials || [] })
      if (res?.total > 0) message.success(`找到 ${res.total} 个相关素材`)
      else message.info('未找到匹配素材')
    } catch { message.error('搜索失败') }
    setGenerating(null)
  }

  // 生成视频 → 异步提交 + 前端轮询
  const generatingRef = useRef(false)
  const genVideo = async () => {
    if (generatingRef.current) return
    generatingRef.current = true
    const sid = sessionIdRef.current
    if (!sid) { generatingRef.current = false; return }
    setGenerating('生成视频')
    try {
      // 提交任务
      const submitRes: any = await request.post('/studio/generate-video', { session_id: sid, script_name: `script_${sid}` }, { timeout: 300000 })
      if (!submitRes?.submitted) { generatingRef.current = false; return message.error('提交失败') }

      message.info('视频生成已提交，等待中...')

      // 轮询等待完成
      let done = false
      for (let i = 0; i < 60; i++) {  // 最多 60 次（30 分钟）
        await new Promise(r => setTimeout(r, 30000))  // 每 30 秒
        try {
          const pollRes: any = await request.post(`/studio/poll-generate/${sid}`)
          if (pollRes?.status === 'completed') {
            const newClips = pollRes.clips || []
            if (newClips.length > 0) {
              const cols = [...(stateRef.current.clip_collections || [])]
              const col = { id: Date.now(), name: `视频运行 #${cols.length + 1}`, clips: newClips, created_at: new Date().toISOString() }
              cols.push(col)
              saveState({ clip_collections: cols, selected_clip_collection_id: col.id })
            }
            message.success(`生成完成，${pollRes.saved || 0} 个片段`)
            done = true
            break
          } else if (pollRes?.status === 'running') {
            // 继续等
          } else {
            // unknown / no_task — 可能还得等
          }
        } catch { /* 继续轮询 */ }
      }
      if (!done) message.warning('生成超时，可稍后刷新查看')
      loadClips()
    } catch { message.error('生成失败') }
    generatingRef.current = false
    setGenerating(null)
  }

  // 合成视频 → 用选中集合的 clip_ids
  const composeVid = async () => {
    const st = stateRef.current
    const coll = (st.clip_collections || []).find((c: any) => c.id === st.selected_clip_collection_id)
    if (!coll || !coll.clips?.length) return message.warning('请先选择视频片段集合')
    setGenerating('合成视频')
    try {
      await request.post('/studio/compose-video', { session_id: sessionIdRef.current, clip_ids: coll.clips.map((c: any) => c.id) })
      message.success('合成完成')
      loadClips()
    } catch { message.error('合成失败') }
    setGenerating(null)
  }

  const deleteCollection = async (id: number) => {
    const cols = (stateRef.current.collections || []).filter((c: any) => c.id !== id)
    const patch: any = { collections: cols }
    if (stateRef.current.selected_collection_id === id) patch.selected_collection_id = null
    try { await saveState(patch) } catch { message.error('删除失败') }
  }

  const deleteScript = () => {
    try { saveState({ last_script: null }) } catch {}
  }

  const deleteClipCollection = async (id: number) => {
    const cols = (stateRef.current.clip_collections || []).filter((c: any) => c.id !== id)
    const patch: any = { clip_collections: cols }
    if (stateRef.current.selected_clip_collection_id === id) patch.selected_clip_collection_id = null
    try { await saveState(patch) } catch { message.error('删除失败') }
  }

  const deleteFinalVideo = async (id: number) => {
    try {
      await request.post('/studio/delete-clip', { clip_id: id })
    } catch { return message.error('删除失败') }
    const videos = (stateRef.current.final_videos || []).filter((v: any) => v.id !== id)
    saveState({ final_videos: videos })
  }

  const clearFinalVideos = async () => {
    const ids = (stateRef.current.final_videos || []).map((v: any) => v.id)
    for (const id of ids) {
      try { await request.post('/studio/delete-clip', { clip_id: id }) } catch {}
    }
    saveState({ final_videos: [] })
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

  // 当前选中的 clip 集合
  const selectedClipColl = (state.clip_collections || []).find((c: any) => c.id === state.selected_clip_collection_id)

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
          <StepBox title="素材选择">
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12 }}>相似度: {localThreshold}%</span>
              <Slider min={0} max={100} step={1} value={localThreshold} style={{ width: 140, margin: 0 }}
                onChange={v => { setLocalThreshold(v); saveState({ threshold: v }) }} />
            </div>
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
                style={{ cursor: 'pointer', background: state.selected_collection_id === c.id ? '#e6f4ff' : undefined }}
                actions={[
                  <span key="del" onClick={e => { e.stopPropagation(); deleteCollection(c.id) }}>
                    <DeleteOutlined style={{ color: '#ff4d4f' }} />
                  </span>
                ]}>
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
            <div style={{ fontSize: 12, color: '#999' }}>选产品+素材集合+模板后点击生成</div>
            {state.last_script?.script?.title && (
              <div style={{ marginTop: 8, padding: 8, background: '#f6ffed', borderRadius: 4, fontSize: 13 }}>
                ✅ 剧本: <strong>{state.last_script.script.title}</strong>
                <br /><span style={{ color: '#666' }}>{state.last_script.script.scenes?.length || 0} 个场景</span>
                <Button size="small" type="link" icon={<EditOutlined />} onClick={() => setScriptEditorOpen(true)} style={{ padding: 0, marginLeft: 8 }}>编辑</Button>
                <Button size="small" type="link" icon={<RobotOutlined />} onClick={() => setAiScriptEditorOpen(true)} style={{ padding: 0, marginLeft: 4 }}>AI编辑</Button>
                <Button size="small" type="link" danger icon={<DeleteOutlined />} onClick={e => { e.stopPropagation(); deleteScript() }} style={{ padding: 0, marginLeft: 4 }} />
              </div>
            )}
          </StepBox>
          <GenBtn label="生成剧本" onClick={genScript} />
        </div>
        <Arrow />

        {/* 4. 结果视频 */}
        <div>
          <StepBox title="结果视频" extra={state.clip_collections?.length > 0 ? <span style={{ fontSize: 12, color: '#52c41a' }}>{state.clip_collections.length} 次运行</span> : undefined}>
            {!state.last_script?.script?.title ? (
              <div style={{ color: '#999', fontSize: 12, textAlign: 'center', padding: 20 }}>生成剧本后点击生成</div>
            ) : (
              <>
                {/* 视频运行集合列表 */}
                <List size="small" dataSource={state.clip_collections} renderItem={(c: any) => (
                  <List.Item onClick={() => saveState({ selected_clip_collection_id: c.id })}
                    style={{ cursor: 'pointer', background: state.selected_clip_collection_id === c.id ? '#e6f4ff' : undefined }}
                    actions={[
                      <span key="del" onClick={e => { e.stopPropagation(); deleteClipCollection(c.id) }}>
                        <DeleteOutlined style={{ color: '#ff4d4f' }} />
                      </span>
                    ]}>
                    <Space>
                      <VideoCameraOutlined />
                      <span style={{ fontSize: 12 }}>{c.name} ({c.clips?.length || 0} 片段)</span>
                    </Space>
                  </List.Item>
                )} />
                {(!state.clip_collections || state.clip_collections.length === 0) && (
                  <div style={{ color: '#999', fontSize: 12, textAlign: 'center', padding: 20 }}>点击下方按钮开始生成</div>
                )}

                {/* 选中集合的片段详情 */}
                {selectedClipColl && (
                  <Collapse ghost size="small" items={[{
                    key: 'clips',
                    label: <span style={{ fontSize: 12 }}>查看片段 ({selectedClipColl.clips?.length || 0})</span>,
                    children: (
                      <div style={{ maxHeight: 200, overflow: 'auto' }}>
                        {selectedClipColl.clips?.map((clip: any) => (
                          <div key={clip.id} style={{ fontSize: 12, padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                            <a href={clip.url} target="_blank" rel="noreferrer">场景 {clip.scene_id}</a>
                          </div>
                        ))}
                      </div>
                    ),
                  }]} />
                )}
              </>
            )}
          </StepBox>
          {state.last_script?.script?.title && <GenBtn label="生成视频" onClick={genVideo} />}
        </div>
        <Arrow />

        {/* 5. 视频合成 */}
        <div>
          <StepBox title="视频合成">
            {!selectedClipColl ? (
              <div style={{ color: '#999', fontSize: 12, textAlign: 'center', padding: 20 }}>选一个视频片段集合后点击合成</div>
            ) : (
              <div style={{ marginBottom: 8, fontSize: 12, color: '#666' }}>素材: {selectedClipColl.name} ({selectedClipColl.clips?.length} 片段)</div>
            )}

            {/* 最终视频列表 */}
            {state.final_videos?.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 4, color: '#52c41a' }}>
                  ✅ 最终视频
                  <Button size="small" type="link" danger style={{ fontSize: 11, padding: 0, marginLeft: 8 }}
                    onClick={clearFinalVideos}>清空全部</Button>
                </div>
                <List size="small" dataSource={state.final_videos} renderItem={(v: any) => (
                  <List.Item actions={[
                    <span key="del" onClick={e => { e.stopPropagation(); deleteFinalVideo(v.id) }}>
                      <DeleteOutlined style={{ color: '#ff4d4f', fontSize: 11 }} />
                    </span>
                  ]}>
                    <a href={v.url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                      <PlayCircleOutlined style={{ marginRight: 4 }} />视频 {v.id}
                    </a>
                  </List.Item>
                )} />
              </div>
            )}
          </StepBox>
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

      <ScriptEditor sessionId={sessionId || 0} visible={scriptEditorOpen} onClose={() => setScriptEditorOpen(false)} />
      <AiScriptEditor sessionId={sessionId || 0} scriptName={`script_${sessionId}`}
        visible={aiScriptEditorOpen}
        onClose={() => setAiScriptEditorOpen(false)}
        onScriptUpdated={(script) => saveState({ last_script: { script } })}
        template={state.selected_template}
      />
    </div>
  )
}
