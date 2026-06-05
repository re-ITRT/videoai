import { useState, useEffect, useRef } from 'react'
import { Select, Button, Card, Input, Modal, Space, message, List, Collapse, Popconfirm, Slider, Tag, Menu } from 'antd'
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined, VideoCameraOutlined, RobotOutlined, SoundOutlined, CustomerServiceOutlined, AppstoreOutlined, FileTextOutlined } from '@ant-design/icons'
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

  const [state, setState] = useState<any>({
    products: [], selected_product_id: null, threshold: 30,
    selected_material_ids: [], collections: [], selected_template: '',
    clip_collections: [], selected_clip_collection_id: null,
    final_videos: [], scripts: [], selected_script_id: null,
  })
  const stateRef = useRef(state)
  stateRef.current = state

  const [materials, setMaterials] = useState<any[]>([])
    const [localThreshold, setLocalThreshold] = useState(0.5)
  const [productModal, setProductModal] = useState(false)
  const [productTitle, setProductTitle] = useState('')
  const [productContent, setProductContent] = useState('')
  const [templates, setTemplates] = useState<string[]>([])
  const [generating, setGenerating] = useState<string | null>(null)
  const [scriptEditorOpen, setScriptEditorOpen] = useState(false)
  const [aiScriptEditorOpen, setAiScriptEditorOpen] = useState(false)
  const [asrLoadingId, setAsrLoadingId] = useState<number | null>(null)
  const [asrResult, setAsrResult] = useState<any>(null)
  // Keep reference to asrResult for composeVid callback
  void asrResult;
  const [subbedUrl, setSubbedUrl] = useState('')
  const [exporting, setExporting] = useState(false)
  // BGM
  const [bgmMaterials, setBgmMaterials] = useState<any[]>([])
  const [selectedBgmId, setSelectedBgmId] = useState<number | null>(null)
  const [step, setStep] = useState(0)
  const stepIcons = [<PlusOutlined />, <VideoCameraOutlined />, <AppstoreOutlined />, <FileTextOutlined />, <PlayCircleOutlined />, <CustomerServiceOutlined />, <VideoCameraOutlined />]
  const stepLabels = ['产品介绍', '素材选择', '素材集合', '剧本生成', '视频生成', 'BGM选择', '导出']

  // 加载 Session 列表
  useEffect(() => {
    request.get('/agent/sessions').then((r: any) => setSessions(r || [])).catch(() => {})
    request.get('/workflows/prompts').then((r: any) => setTemplates(Object.keys(r?.templates || {}))).catch(() => {})
    loadBgmMaterials()
  }, [])

  // 切换 Session 时加载状态
  useEffect(() => {
    if (!sessionId) return
    request.get(`/studio/state/${sessionId}`).then((r: any) => {
      if (r && typeof r === 'object' && !r.detail) {
        setState((prev: any) => ({ ...prev, ...r }))
        setMaterials(r.cached_materials || [])
      }
    }).catch(() => {})
  }, [sessionId])

  const loadBgmMaterials = async () => {
    try {
      const r: any = await request.get('/materials', { params: { material_type: 'audio' } })
      const list = Array.isArray(r) ? r : r?.items || []
      setBgmMaterials(list)
    } catch {}
  }

  // ========== 以下函数与原来完全一致 ==========

  const saveState = async (patch: any) => {
    const st = { ...stateRef.current, ...patch }
    setState(st)
    if (sessionIdRef.current) {
      try { await request.put(`/studio/state/${sessionIdRef.current}`, st) } catch {}
    }
  }

// @ts-ignore - kept for potential future use
  const loadSession = async (sid: number) => {
    setSessionId(sid)
    try {
      const r: any = await request.get(`/studio/state/${sid}`)
      if (r && typeof r === 'object') {
        setState({ ...state, ...r })
        setMaterials(r.cached_materials || [])
      }
    } catch {}
  }

  const deleteSession = async (sid: number) => {
    try { await request.delete(`/agent/sessions/${sid}`); setSessions(s => s.filter(x => x.id !== sid)); if (sessionId === sid) setSessionId(null) } catch {}
  }

  const createSession = async () => {
    try {
      const r: any = await request.post('/agent/sessions', { title: sessionTitle || '新工作流' })
      setSessions(s => [...s, r]); setSessionId(r.id); setSessionModal(false); setSessionTitle('')
      saveState({ session_name: sessionTitle || '新工作流' })
    } catch { message.error('创建失败') }
  }

  const addProduct = async () => {
    if (!productContent.trim()) return message.warning('请输入产品介绍')
    const products = [...state.products, { id: Date.now(), title: productTitle || productContent.slice(0, 30), content: productContent }]
    saveState({ products }); setProductModal(false); setProductTitle(''); setProductContent('')
  }

  const createCollection = async () => {
    const ids = state.selected_material_ids
    if (!ids.length) return message.warning('请先选择素材')
    const cols = [...(state.collections || [])]
    cols.push({ id: Date.now(), name: `集合 #${cols.length + 1}`, material_ids: ids })
    saveState({ collections: cols })
  }

  const genScript = async () => {
    const prod = state.products.find((p: any) => p.id === state.selected_product_id)
    if (!prod) return message.warning('请选择产品介绍')
    if (!state.selected_template) return message.warning('请选择模板')
    const coll = state.collections.find((c: any) => c.id === state.selected_collection_id)
    if (!coll) return message.warning('请选择素材集合')
    setGenerating('生成剧本')
    try {
      const matDetails = materials.filter((m: any) => coll.material_ids.includes(m.id)).map((m: any) => ({ material_id: m.id, description: m.tags?.join(', ') || '', tags: m.tags || [] }))
      const res: any = await request.post('/studio/generate-script', { product_content: prod.content, template: state.selected_template, materials: matDetails, session_id: sessionId })
      const newScript = { id: Date.now(), name: `${prod.title?.slice(0, 16) || '剧本'} #${(state.scripts?.length || 0) + 1}`, script: res.script || res, created_at: new Date().toISOString() }
      const scripts = [...(state.scripts || []), newScript]
      message.success('剧本已生成')
      saveState({ scripts, selected_script_id: newScript.id })
    } catch { message.error('生成失败') }
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
    } catch { message.error('搜索失败') }
    setGenerating(null)
  }

  const generatingRef = useRef(false)

  const genVideo = async () => {
    if (generatingRef.current) return
    generatingRef.current = true
    const sid = sessionIdRef.current
    if (!sid) { generatingRef.current = false; return }
    const selScript = state.scripts?.find((s: any) => s.id === state.selected_script_id)
    if (!selScript) { generatingRef.current = false; return message.warning('请选择剧本') }
    setGenerating('生成视频')
    try {
      const script_name = `script_${selScript.id}`
      // Save the script to session file
      await request.post('/studio/generate-script', { product_content: '', template: state.selected_template, materials: [], session_id: sid, save_only: true, script: selScript.script }).catch(() => {})
      const submitRes: any = await request.post('/studio/generate-video', { session_id: sid, script_name }, { timeout: 300000 })
      if (!submitRes?.submitted) { generatingRef.current = false; return message.error('提交失败') }
      message.info('视频生成已提交，等待中...')
      let done = false
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 30000))
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
            done = true; break
          } else if (pollRes?.status === 'running') continue
          else { message.error('生成异常'); break }
        } catch { continue }
      }
      if (!done) message.error('生成超时')
    } catch { message.error('生成失败') }
    setGenerating(null)
    generatingRef.current = false
  }

  const loadClips = async () => {
    const sid = sessionIdRef.current
    if (!sid) return
    try {
      const res: any = await request.post('/studio/get-session-clips', { session_id: sid })
      if (res) {
        const fv = res.final_videos || []
        const subbedUrls = res.subbed_videos || []
        saveState({ final_videos: fv })
        if (subbedUrls.length > 0) setSubbedUrl(subbedUrls[0])
      }
    } catch {}
  }

  // 合成视频 → 自动 ASR + 字幕烧录
  const composeVid = async () => {
    const st = stateRef.current
    const coll = (st.clip_collections || []).find((c: any) => c.id === st.selected_clip_collection_id)
    if (!coll || !coll.clips?.length) return message.warning('请先选择视频片段集合')
    setGenerating('合成视频')
    try {
      await request.post('/studio/compose-video', { session_id: sessionIdRef.current, clip_ids: coll.clips.map((c: any) => c.id) })
      message.success('合成完成')
      await loadClips()
      // 合成后自动 ASR + 字幕烧录
      const fv = stateRef.current.final_videos
      if (fv?.length > 0) {
        const vid = fv[0]
        message.info('自动进行语音识别...')
        try {
          const asrRes: any = await request.post('/studio/asr', { video_url: vid.url, session_id: sessionIdRef.current }, { timeout: 600000 })
          if (asrRes?.segments?.length) {
            setAsrResult(asrRes)
            message.info('自动生成字幕...')
            const burnRes: any = await request.post('/studio/burn-subtitles', { video_url: vid.url, segments: asrRes.segments, session_id: sessionIdRef.current }, { timeout: 600000 })
            if (burnRes?.url) {
              setSubbedUrl(burnRes.url)
              message.success('字幕视频已生成')
            }
          }
        } catch { message.warning('ASR 识别失败，可手动重试') }
      }
    } catch { message.error('合成失败') }
    setGenerating(null)
  }

  const deleteCollection = async (id: number) => {
    const cols = (stateRef.current.collections || []).filter((c: any) => c.id !== id)
    const patch: any = { collections: cols }
    if (stateRef.current.selected_collection_id === id) patch.selected_collection_id = null
    try { await saveState(patch) } catch {}
  }

  const deleteScript = (id?: number) => {
    const scripts = (state.scripts || []).filter((s: any) => s.id !== (id || state.selected_script_id))
    const sel = state.selected_script_id === id ? null : state.selected_script_id
    try { saveState({ scripts, selected_script_id: sel || (scripts.length > 0 ? scripts[0].id : null) }) } catch {}
  }

  const deleteClipCollection = async (id: number) => {
    const cols = (stateRef.current.clip_collections || []).filter((c: any) => c.id !== id)
    const patch: any = { clip_collections: cols }
    if (stateRef.current.selected_clip_collection_id === id) patch.selected_clip_collection_id = null
    try { await saveState(patch) } catch {}
  }

  const runAsr = async (id: number, url: string) => {
    setAsrLoadingId(id)
    setAsrResult(null)
    try {
      const res: any = await request.post('/studio/asr', { video_url: url, session_id: sessionId }, { timeout: 600000 })
      if (res.error) { message.error(res.error); return }
      setAsrResult(res)
    } catch { message.error('ASR 请求失败') }
    setAsrLoadingId(null)
  }

  // @ts-ignore
  const doExport = async () => {
    if (!subbedUrl) return
    setExporting(true)
    try {
      const res: any = await request.post('/published/export', { video_url: subbedUrl, title: state.session_name || '导出视频', session_id: sessionId, script_template: state.selected_template || 'default' }, { timeout: 300000 })
      if (res.success) message.success('已导出到已生成视频！')
      else message.error(res.message || '导出失败')
    } catch { message.error('导出请求失败') }
    setExporting(false)
  }

  const GenBtn = ({ label, onClick }: any) => (
    <div style={{ textAlign: 'center', margin: '8px 0' }}>
      <Button type="primary" icon={<PlayCircleOutlined />} loading={generating === label} onClick={onClick} style={{ width: 180 }}>{label}</Button>
    </div>
  )

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

      {/* 工作流步骤 - 侧栏导航 */}
      {sessionId ? (
        <div style={{ display: 'flex', gap: 16, flex: 1, overflow: 'hidden' }}>
          <div style={{ width: 160, flexShrink: 0, borderRight: '1px solid #f0f0f0', paddingRight: 8, paddingTop: 8 }}>
            <Menu mode="inline" selectedKeys={[String(step)]}
              onClick={({ key }) => setStep(Number(key))}
              style={{ border: 'none' }}
              items={stepLabels.map((s, i) => ({ key: String(i), icon: stepIcons[i], label: s }))} />
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '0 8px' }}>
            {step === 0 && (
              <div>
                <Card title="产品介绍" size="small" extra={<Button size="small" icon={<PlusOutlined />} onClick={() => setProductModal(true)} />} style={{ minHeight: 400 }}>
                  <List size="small" dataSource={state.products} renderItem={(p: any) => (
                    <List.Item onClick={() => saveState({ selected_product_id: p.id })}
                      style={{ cursor: 'pointer', background: state.selected_product_id === p.id ? '#e6f4ff' : undefined }}>
                      {p.title || p.content?.slice(0, 30)}
                    </List.Item>
                  )} />
                </Card>
                <GenBtn label="嵌入搜索" onClick={semanticSearch} />
              </div>
            )}
            {step === 1 && (
              <div>
                <Card title="素材选择" size="small" style={{ minHeight: 400 }}>
                  <div style={{ marginBottom: 16 }}>
                    <span>相似度阈值: {localThreshold}</span>
                    <Slider min={0} max={0.95} step={0.05} value={localThreshold} onChange={setLocalThreshold} />
                  </div>
                  <List size="small" dataSource={materials} renderItem={(m: any) => (
                    <List.Item style={{ cursor: 'pointer', background: state.selected_material_ids.includes(m.id) ? '#e6f4ff' : undefined }}
                      onClick={() => saveState({ selected_material_ids: state.selected_material_ids.includes(m.id) ? state.selected_material_ids.filter((x: number) => x !== m.id) : [...state.selected_material_ids, m.id] })}>
                      <Space>{m.image_url && <img src={m.image_url} style={{ width: 36, height: 36, objectFit: 'cover', borderRadius: 4 }} />}<span>{m.id}</span></Space>
                    </List.Item>
                  )} />
                </Card>
                <GenBtn label="生成素材集合" onClick={createCollection} />
              </div>
            )}
            {step === 2 && (
              <div>
                <Card title="素材集合" size="small" style={{ minHeight: 400 }}>
                  <List size="small" dataSource={state.collections} renderItem={(c: any) => (
                    <List.Item onClick={() => saveState({ selected_collection_id: c.id })}
                      style={{ cursor: 'pointer', background: state.selected_collection_id === c.id ? '#e6f4ff' : undefined }}
                      actions={[<span key="del" onClick={e => { e.stopPropagation(); deleteCollection(c.id) }}><DeleteOutlined style={{ color: '#ff4d4f' }} /></span>]}>
                      <span style={{ fontSize: 13 }}>{c.name} ({c.material_ids?.length || 0} 素材)</span>
                    </List.Item>
                  )} />
                  {state.collections.length === 0 && <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>选素材后点击生成</div>}
                </Card>
                <GenBtn label="生成剧本" onClick={genScript} />
              </div>
            )}
            {step === 3 && (
              <div>
                <Card title="剧本生成" size="small" extra={<Select placeholder="模板" size="small" style={{ width: 120 }} value={state.selected_template} onChange={v => saveState({ selected_template: v })} options={templates.map(t => ({ value: t, label: t }))} />} style={{ minHeight: 400 }}>
                  {(state.scripts || []).length === 0 ? (
                    <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>在素材集合步骤生成剧本后在此查看和选择</div>
                  ) : (
                    <List size="small" dataSource={state.scripts} renderItem={(s: any) => (
                      <List.Item onClick={() => saveState({ selected_script_id: s.id })}
                        style={{ cursor: 'pointer', background: state.selected_script_id === s.id ? '#e6f4ff' : undefined }}
                        actions={[
                          <Button key="edit" size="small" type="link" icon={<EditOutlined />} onClick={e => { e.stopPropagation(); setScriptEditorOpen(true) }} />,
                          <Button key="ai" size="small" type="link" icon={<RobotOutlined />} onClick={e => { e.stopPropagation(); setAiScriptEditorOpen(true) }} />,
                          <span key="del" onClick={e => { e.stopPropagation(); deleteScript(s.id) }}><DeleteOutlined style={{ color: '#ff4d4f' }} /></span>
                        ]}>
                        <Space>
                          <span style={{ fontWeight: state.selected_script_id === s.id ? 600 : 400 }}>{s.name}</span>
                          <Tag style={{ fontSize: 10 }}>{s.script?.scenes?.length || 0} 场景</Tag>
                        </Space>
                      </List.Item>
                    )} />
                  )}
                  {state.selected_script_id && (() => {
                    const sel = (state.scripts || []).find((s: any) => s.id === state.selected_script_id)
                    return sel ? (
                      <div style={{ marginTop: 12, padding: 12, background: '#f6ffed', borderRadius: 4 }}>
                        <div style={{ fontWeight: 600 }}>✅ {sel.script?.title || sel.name}</div>
                        <div style={{ color: '#666', fontSize: 12 }}>{sel.script?.scenes?.length || 0} 个场景</div>
                      </div>
                    ) : null
                  })()}
                </Card>
                <GenBtn label="生成视频" onClick={genVideo} />
              </div>
            )}
            {step === 4 && (
              <div>
                <Card title="视频生成" size="small" extra={state.clip_collections?.length > 0 ? <Tag color="green">{state.clip_collections.length} 次运行</Tag> : undefined} style={{ minHeight: 400 }}>
                  {!state.last_script?.script?.title ? <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>生成剧本后点击生成</div> : (
                    <div>
                      <List size="small" dataSource={state.clip_collections} renderItem={(c: any) => (
                        <List.Item onClick={() => saveState({ selected_clip_collection_id: c.id })}
                          style={{ cursor: 'pointer', background: state.selected_clip_collection_id === c.id ? '#e6f4ff' : undefined }}
                          actions={[<span key="del" onClick={e => { e.stopPropagation(); deleteClipCollection(c.id) }}><DeleteOutlined style={{ color: '#ff4d4f' }} /></span>]}>
                          <Space><VideoCameraOutlined /><span>{c.name} ({c.clips?.length || 0} 片段)</span></Space>
                        </List.Item>
                      )} />
                      {(!state.clip_collections || state.clip_collections.length === 0) && <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>点击下方按钮开始生成</div>}
                      {selectedClipColl && <Collapse ghost size="small" items={[{key:'clips',label:<span>查看片段 ({selectedClipColl.clips?.length||0})</span>,children:<div style={{maxHeight:200,overflow:'auto'}}>{selectedClipColl.clips?.map((clip:any)=>(<div key={clip.id} style={{padding:'4px 0',borderBottom:'1px solid #f0f0f0'}}><a href={clip.url} target="_blank" rel="noreferrer">场景 {clip.scene_id}</a></div>))}</div>}]} />}
                    </div>
                  )}
                </Card>
                <Space style={{ marginTop: 8 }}>
                  {selectedClipColl && <GenBtn label="合成视频" onClick={composeVid} />}
                </Space>
              </div>
            )}
            {step === 5 && (
              <div>
                <Card title="BGM 选择" size="small" extra={<Button size="small" icon={<CustomerServiceOutlined />} onClick={loadBgmMaterials}>刷新</Button>} style={{ minHeight: 400 }}>
                  {bgmMaterials.length === 0 ? <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>暂无音频素材</div> : (
                    <List size="small" dataSource={bgmMaterials} renderItem={(m: any) => (
                      <List.Item onClick={() => setSelectedBgmId(selectedBgmId === m.id ? null : m.id)}
                        style={{ cursor: 'pointer', background: selectedBgmId === m.id ? '#fff7e6' : undefined }}>
                        <Space><SoundOutlined style={{ color: '#fa8c16', fontSize: 20 }} />
                          <div><div style={{ fontWeight: 500 }}>{m.name || '未命名'}</div><div style={{ color: '#999', fontSize: 11 }}>{m.tags?.join(', ') || ''}</div>
                          {m.image_url && <audio src={m.image_url} controls style={{ width: 200, height: 28, marginTop: 4 }} />}</div>
                        </Space>
                      </List.Item>
                    )} />
                  )}
                </Card>
                {selectedBgmId && <Tag color="orange" style={{ marginTop: 8 }}>已选 BGM</Tag>}
              </div>
            )}
            {step === 6 && (
              <div>
                <Card title="导出" size="small" style={{ minHeight: 400 }}>
                  {subbedUrl ? <Space direction="vertical" style={{ width: '100%' }}>
                    <div style={{color:'#52c41a',marginBottom:8}}>✅ 字幕视频已就绪</div>
                    <a href={subbedUrl} target="_blank" rel="noreferrer"><Button icon={<PlayCircleOutlined />} block>查看视频</Button></a>
                    <Button type="primary" icon={<VideoCameraOutlined />} loading={exporting} onClick={doExport} block>导出</Button>
                  </Space> : <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>合成视频后自动生成</div>}
                  {state.final_videos?.length > 0 && !subbedUrl && <div style={{marginTop:12}}>
                    <List size="small" dataSource={state.final_videos} renderItem={(v:any)=>(<List.Item actions={[<Button key="asr" size="small" type="link" loading={v.id===asrLoadingId} onClick={()=>runAsr(v.id,v.url)}>ASR</Button>]}><a href={v.url} target="_blank" rel="noreferrer"><PlayCircleOutlined style={{marginRight:4}}/>视频 {v.id}</a></List.Item>)}/></div>}
                </Card>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
              <Button disabled={step === 0} onClick={() => setStep(s => s - 1)}>← 上一步</Button>
              <Button disabled={step === 6} type="primary" onClick={() => setStep(s => s + 1)}>下一步 →</Button>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📋</div>
          <div>请选择或新建一个工作流开始</div>
        </div>
      )}

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
