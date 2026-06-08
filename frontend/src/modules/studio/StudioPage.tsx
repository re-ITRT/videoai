import { useState, useEffect, useRef } from 'react'
import { Select, Button, Card, Input, Modal, Space, message, List, Popconfirm, Slider, Tag, Menu } from 'antd'
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined, VideoCameraOutlined, RobotOutlined, SoundOutlined, CustomerServiceOutlined, AppstoreOutlined, FileTextOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import request from '../../utils/request'
import ScriptEditor from '../agent/ScriptEditor'
import AiScriptEditor from '../agent/AiScriptEditor'

const { TextArea } = Input

function SpeedBar() {
  const [speed, setSpeed] = useState(1)
  const speeds = [0.5, 1, 1.5, 2]
  return (
    <div style={{ display: 'flex', gap: 4, justifyContent: 'center', marginTop: 4 }}>
      {speeds.map(s => (
        <Button key={s} size="small" type={speed === s ? 'primary' : 'default'}
          onClick={() => { setSpeed(s); document.querySelectorAll('video').forEach(v => { try { v.playbackRate = s } catch {} }) }}
          style={{ fontSize: 11, lineHeight: '18px', height: 22, padding: '0 6px' }}>{s}x</Button>
      ))}
    </div>
  )
}

export default function StudioPage() {
  const [sessions, setSessions] = useState<any[]>([])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const sessionIdRef = useRef(sessionId)
  sessionIdRef.current = sessionId
  const [sessionModal, setSessionModal] = useState(false)
  const [sessionTitle, setSessionTitle] = useState('')
  const [sessionTemplate, setSessionTemplate] = useState('default')
  const [sessionBgmStyle, setSessionBgmStyle] = useState<string>('')

  const [state, setState] = useState<any>({
    products: [], selected_product_id: null, threshold: 30,
    selected_material_ids: [], collections: [], selected_template: '',
    clip_collections: [], selected_clip_collection_id: null,
    final_videos: [], scripts: [], selected_script_id: null, exports: [], selected_export_id: null, asrResults: {},
    composed_video: null, subbed_video: null, bgm_mixed_video: null,
  })
  const stateRef = useRef(state)
  stateRef.current = state

  const [materials, setMaterials] = useState<any[]>([])
    const [localThreshold, setLocalThreshold] = useState(0.5)
  const [productModal, setProductModal] = useState(false)
  const [productTitle, setProductTitle] = useState('')
  const [productContent, setProductContent] = useState('')
  const [productEditId, setProductEditId] = useState<number | null>(null)
  const [templates, setTemplates] = useState<string[]>([])
  const [generating, setGenerating] = useState<string | null>(null)
  const [scriptEditorOpen, setScriptEditorOpen] = useState(false)
  const [aiScriptEditorOpen, setAiScriptEditorOpen] = useState(false)
  const [asrLoadingId, setAsrLoadingId] = useState<number | null>(null)
  void asrLoadingId; void setAsrLoadingId;
  const [asrResults, setAsrResults] = useState<Record<number, any>>(state.asrResults || {})
  const [selectedAsrVideo, setSelectedAsrVideo] = useState<number | null>(null)
  const [editedSegments, setEditedSegments] = useState<string[]>([])
  const [burningSub, setBurningSub] = useState(false)
  const [exporting, setExporting] = useState(false)
  void exporting;
  const [subbedUrl, setSubbedUrl] = useState('')
  // BGM
  const [bgmMaterials, setBgmMaterials] = useState<any[]>([])
  const [selectedBgmId, setSelectedBgmId] = useState<number | null>(null)
  const [step, setStep] = useState(0)
  // 分镜剪辑
  const [editingClips, setEditingClips] = useState<any[]>([])
  const [agentLoading, setAgentLoading] = useState(false)
  const stepIcons = [<PlusOutlined />, <VideoCameraOutlined />, <AppstoreOutlined />, <FileTextOutlined />, <PlayCircleOutlined />, <SoundOutlined />, <CustomerServiceOutlined />, <VideoCameraOutlined />]
  const stepLabels = ['产品介绍', '素材选择', '素材集合', '剧本生成', '视频生成', 'ASR校准', 'BGM选择', '导出']

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
        if (r.asrResults) setAsrResults(r.asrResults)
        setMaterials(r.cached_materials || [])
      }
    }).catch(() => {})
    // 加载合成的最终视频和字幕视频
    request.get(`/studio/clips/${sessionId}`).then((r: any) => {
      if (r) {
        const fv = r.final_videos || []
        setState((prev: any) => ({ ...prev, final_videos: fv }))
        // 不自动从服务器重建 clip_collections（用户删了就删了）
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
      setSessions(s => [...s, r]); setSessionId(r.id); setSessionModal(false); setSessionTitle(''); setSessionTemplate('default')
      saveState({ session_name: sessionTitle || '新工作流', selected_template: sessionTemplate, bgm_style: sessionBgmStyle })
    } catch { message.error('创建失败') }
  }

  const addProduct = async () => {
    if (!productContent.trim()) return message.warning('请输入产品介绍')
    let products: any[]
    if (productEditId) {
      products = state.products.map((p: any) => p.id === productEditId ? { ...p, title: productTitle || productContent.slice(0, 30), content: productContent } : p)
    } else {
      products = [...state.products, { id: Date.now(), title: productTitle || productContent.slice(0, 30), content: productContent }]
    }
    saveState({ products }); setProductModal(false); setProductTitle(''); setProductContent(''); setProductEditId(null)
  }

  const deleteProduct = (id: number) => {
    const products = state.products.filter((p: any) => p.id !== id)
    const sel = state.selected_product_id === id ? null : state.selected_product_id
    saveState({ products, selected_product_id: sel })
  }

  const editProduct = (p: any) => {
    setProductTitle(p.title)
    setProductContent(p.content)
    setProductEditId(p.id)
    setProductModal(true)
  }

  const createCollection = async () => {
    const ids = state.selected_material_ids
    if (!ids.length) return message.warning('请先选择素材')
    const cols = [...(state.collections || [])]
    cols.push({ id: Date.now(), name: `集合 #${cols.length + 1}`, material_ids: ids })
    saveState({ collections: cols })
  }

  const runAsr = async (id: number, url: string) => {
    setAsrLoadingId(id)
    try {
      const res: any = await request.post('/studio/asr', { video_url: url, session_id: sessionId }, { timeout: 600000 })
      if (res.error) { message.error(res.error); return }
      const newResults = {...(stateRef.current.asrResults || {}), [id]: res}
      setAsrResults(newResults)
      saveState({ asrResults: newResults })
      setSelectedAsrVideo(id)
      setEditedSegments(res.segments?.map((s: any) => s.text) || [])
    } catch { message.error('ASR 请求失败') }
    setAsrLoadingId(null)
  }

  const deleteExport = (id: number) => {
    const exports = (stateRef.current.exports || []).filter((e: any) => e.id !== id)
    const sel = stateRef.current.selected_export_id === id ? null : stateRef.current.selected_export_id
    try { saveState({ exports, selected_export_id: sel || (exports.length > 0 ? exports[0].id : null) }) } catch {}
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
      const script_name = `script_${sid}`
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

  // 智能剪辑 Agent
  const handleAgentEdit = async () => {
    setAgentLoading(true)
    try {
      const res: any = await request.post('/studio/agent-edit', {
        session_id: sessionIdRef.current,
        clips: editingClips.map((c: any) => ({ id: c.id, url: c.url, scene_id: c.scene_id, duration: c.duration })),
        bgm_style: stateRef.current.bgm_style || '',
      }, { timeout: 120000 })
      if (res && Array.isArray(res.clips)) {
        setEditingClips(res.clips)
        message.success('智能剪辑完成')
      } else {
        message.error('剪辑处理失败')
      }
    } catch { message.error('智能剪辑请求失败') }
    setAgentLoading(false)
  }

  // 合成视频（纯合成，不自动ASR，输出给ASR步骤）
  const composeVid = async (editClips?: any[]) => {
    const clipsToUse = editClips || stateRef.current.clip_collections?.find((c: any) => c.id === stateRef.current.selected_clip_collection_id)?.clips || []
    if (!clipsToUse.length) return message.warning('请先选择视频片段集合')
    setGenerating('合成视频')
    try {
      const res: any = await request.post('/studio/compose-video', { session_id: sessionIdRef.current, clip_ids: clipsToUse.map((c: any) => c.id), transitions: editClips ? editClips.map((c: any) => c.transition || 'cut') : undefined })
      if (res?.videos?.length > 0) {
        const vid = res.videos[0]
        saveState({ composed_video: vid })
        message.success('合成完成，前往 ASR 校准步骤')
      } else {
        message.error('合成失败')
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

  const doExport = async () => {
    const mv = stateRef.current.bgm_mixed_video
    if (!mv) return message.warning('请先在 BGM 步骤合成视频')
    setExporting(true)
    try {
      const bgmId = selectedBgmId
      const bgm = bgmId ? bgmMaterials.find((m: any) => m.id === bgmId) : null
      const payload: any = {
        video_url: mv.url,
        title: state.session_name || '导出视频',
        session_id: sessionId,
        script_template: state.selected_template || 'default',
      }
      if (bgm) {
        payload.bgm_url = bgm.image_url?.startsWith('http') ? bgm.image_url : `http://114.117.242.17:3000${bgm.image_url}`
        payload.bgm_name = bgm.name || ''
      }
      const res: any = await request.post('/published/export', payload, { timeout: 300000 })
      if (res.success) {
        const exp = { id: Date.now(), video_url: subbedUrl, title: state.session_name || '导出视频', bgm_name: bgm?.name || '', script_template: state.selected_template || 'default', created_at: new Date().toISOString() }
        const exports = [...(state.exports || []), exp]
        saveState({ exports, selected_export_id: exp.id })
        setSubbedUrl('')
        message.success('导出成功！')
      } else {
        message.error(res.message || '导出失败')
      }
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
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: '#999' }}>模板:</span>
        <Select size="small" style={{ width: 120 }} value={state.selected_template || 'default'} onChange={v => saveState({ selected_template: v })}
          options={templates.map((t: string) => ({ value: t, label: t }))} />
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
                <Card title="产品介绍" size="small" extra={<Button size="small" icon={<PlusOutlined />} onClick={() => { setProductEditId(null); setProductTitle(''); setProductContent(''); setProductModal(true) }} />} style={{ minHeight: 400 }}>
                  <List size="small" dataSource={state.products} renderItem={(p: any) => (
                    <List.Item onClick={() => saveState({ selected_product_id: p.id })}
                      style={{ cursor: 'pointer', background: state.selected_product_id === p.id ? '#e6f4ff' : undefined }}
                      actions={[
                        <Button key="edit" size="small" type="link" icon={<EditOutlined />} onClick={e => { e.stopPropagation(); editProduct(p) }} />,
                        <span key="del" onClick={e => { e.stopPropagation(); deleteProduct(p.id) }}><DeleteOutlined style={{ color: '#ff4d4f' }} /></span>
                      ]}>
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
                <Card title="剧本生成" size="small" style={{ minHeight: 400 }}>
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
                        <List.Item onClick={() => { saveState({ selected_clip_collection_id: c.id }); setEditingClips(c.clips?.map((clip: any) => ({ ...clip, transition: 'cut' })) || []) }}
                          style={{ cursor: 'pointer', background: state.selected_clip_collection_id === c.id ? '#e6f4ff' : undefined }}
                          actions={[<span key="del" onClick={e => { e.stopPropagation(); deleteClipCollection(c.id) }}><DeleteOutlined style={{ color: '#ff4d4f' }} /></span>]}>
                          <Space><VideoCameraOutlined /><span>{c.name} ({c.clips?.length || 0} 片段)</span></Space>
                        </List.Item>
                      )} />
                      {(!state.clip_collections || state.clip_collections.length === 0) && <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>点击下方按钮开始生成</div>}
                      {/* 分镜剪辑面板 */}
                      {selectedClipColl && editingClips.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>🎬 分镜剪辑 — {selectedClipColl.name}</div>
                          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8 }}>
                            {editingClips.map((clip: any, ci: number) => (
                              <div key={clip.id || ci} style={{ minWidth: 160, maxWidth: 180, background: '#fafafa', borderRadius: 6, border: '1px solid #f0f0f0', padding: 8, position: 'relative' }}>
                                <div style={{ fontSize: 11, color: '#999', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
                                  <span>场景 {clip.scene_id}</span>
                                  <span>{clip.duration || '?'}s</span>
                                </div>
                                <video src={clip.url} controls style={{ width: '100%', height: 80, borderRadius: 4, objectFit: 'cover' }} />
                                <div style={{ display: 'flex', gap: 2, marginTop: 4, justifyContent: 'center' }}>
                                  <Button size="small" icon={<ArrowUpOutlined />} disabled={ci === 0}
                                    onClick={e => { e.stopPropagation(); const arr = [...editingClips]; [arr[ci-1], arr[ci]] = [arr[ci], arr[ci-1]]; setEditingClips(arr) }}
                                    style={{ fontSize: 10, height: 20, padding: '0 3px' }} />
                                  <Button size="small" icon={<ArrowDownOutlined />} disabled={ci === editingClips.length - 1}
                                    onClick={e => { e.stopPropagation(); const arr = [...editingClips]; [arr[ci], arr[ci+1]] = [arr[ci+1], arr[ci]]; setEditingClips(arr) }}
                                    style={{ fontSize: 10, height: 20, padding: '0 3px' }} />
                                  <Select size="small" value={clip.transition || 'cut'} onChange={v => { const arr = [...editingClips]; arr[ci] = { ...arr[ci], transition: v }; setEditingClips(arr) }}
                                    style={{ width: 62, fontSize: 10 }} options={[
                                      { value: 'cut', label: '切' },
                                      { value: 'dissolve', label: '叠化' },
                                      { value: 'fade', label: '渐黑' },
                                    ]} />
                                  <Button size="small" icon={<DeleteOutlined />} danger
                                    onClick={e => { e.stopPropagation(); setEditingClips(editingClips.filter((_: any, i: number) => i !== ci)) }}
                                    style={{ fontSize: 10, height: 20, padding: '0 3px' }} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
                <Space style={{ marginTop: 8 }}>
                  {selectedClipColl && editingClips.length > 0 && (
                    <Button icon={<RobotOutlined />} loading={agentLoading} onClick={handleAgentEdit}>🤖 智能剪辑</Button>
                  )}
                  {selectedClipColl && editingClips.length > 0 && <GenBtn label="合成视频" onClick={() => composeVid(editingClips)} />}
                </Space>
              </div>
            )}
            {step === 5 && (
              <div>
                <Card title="ASR 校准" size="small" style={{ minHeight: 400 }}>
                  {/* 来自步骤4的合成视频 */}
                  {state.composed_video ? (
                    <div style={{ marginBottom: 16, padding: 12, background: '#f6ffed', borderRadius: 4, position: 'relative' }}>
                      <div style={{ fontWeight: 600, marginBottom: 8 }}>📹 来自视频生成的合成视频
                        <DeleteOutlined style={{ position: 'absolute', top: 8, right: 8, color: '#ff4d4f', cursor: 'pointer', fontSize: 14 }}
                          onClick={() => { request.post('/studio/delete-clip', { file_url: stateRef.current.composed_video?.url }).catch(() => {}); saveState({ composed_video: null }) }} />   
                      </div>
                      <video src={state.composed_video.url} controls style={{ width: '100%', maxHeight: 200, borderRadius: 4 }} />
                      <SpeedBar />
                    </div>
                  ) : (
                    <div style={{ color: '#999', marginBottom: 12 }}>先在视频生成步骤合成视频</div>
                  )}
                  {/* ASR 操作 */}
                  {state.composed_video && (
                    <div style={{ marginBottom: 12 }}>
                      <Space>
                        <Button size="small" loading={asrLoadingId === state.composed_video.id}
                          onClick={async () => {
                            await runAsr(state.composed_video.id, state.composed_video.url)
                            setSelectedAsrVideo(state.composed_video.id)
                          }}>🎤 语音识别</Button>
                      </Space>
                    </div>
                  )}
                  {/* ASR 结果编辑 */}
                  {selectedAsrVideo && asrResults[selectedAsrVideo]?.segments?.length > 0 && (
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 8 }}>🎤 ASR 识别结果（点击文本可编辑）</div>
                      <div style={{ maxHeight: 200, overflow: 'auto', fontSize: 12 }}>
                        {asrResults[selectedAsrVideo].segments.map((seg: any, i: number) => (
                          <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                            <Tag style={{ fontSize: 10 }}>{seg.start}-{seg.end}s</Tag>
                            <Input.TextArea value={editedSegments?.[i] ?? seg.text}
                              onChange={e => { const ne = [...(editedSegments || [])]; ne[i] = e.target.value; setEditedSegments(ne) }}
                              rows={1} style={{ fontSize: 12 }} />
                          </div>
                        ))}
                      </div>
                      <Space style={{ marginTop: 12 }}>
                        <Button type="primary" size="small" loading={burningSub} onClick={async () => {
                          const vid = stateRef.current.composed_video
                          if (!vid) return
                          const segments = asrResults[selectedAsrVideo].segments.map((s: any, i: number) => ({ ...s, text: editedSegments?.[i] ?? s.text }))
                          setBurningSub(true)
                          try {
                            const res: any = await request.post('/studio/burn-subtitles', { video_url: vid.url, segments, session_id: sessionIdRef.current }, { timeout: 600000 })
                            if (res?.url) {
                              saveState({ subbed_video: { id: Date.now(), url: res.url } })
                              message.success('字幕已烧录，前往 BGM 步骤')
                            }
                          } catch { message.error('烧录失败') }
                          setBurningSub(false)
                        }}>🔥 烧录字幕 → 传给 BGM</Button>
                        <Button size="small" onClick={() => setEditedSegments(asrResults[selectedAsrVideo]?.segments?.map((s: any) => s.text) || [])}>重置</Button>
                      </Space>
                    </div>
                  )}
                  {/* 预览已烧录的字幕视频 */}
                  {state.subbed_video && (
                    <div style={{ marginTop: 16, padding: 12, background: '#e6f7ff', borderRadius: 4, position: 'relative' }}>
                      <div style={{ fontWeight: 600, marginBottom: 8, color: '#1890ff' }}>✅ 字幕视频已就绪 → 传给 BGM
                        <DeleteOutlined style={{ position: 'absolute', top: 8, right: 8, color: '#ff4d4f', cursor: 'pointer', fontSize: 14 }}
                          onClick={() => { request.post('/studio/delete-clip', { file_url: stateRef.current.subbed_video?.url }).catch(() => {}); saveState({ subbed_video: null }) }} />
                      </div>
                      <video src={state.subbed_video.url} controls style={{ width: '100%', maxHeight: 200, borderRadius: 4 }} />
                      <SpeedBar />
                    </div>
                  )}
                </Card>
              </div>
            )}
            {step === 6 && (
              <div>
                <Card title="BGM 选择" size="small" extra={<Button size="small" icon={<CustomerServiceOutlined />} onClick={loadBgmMaterials}>刷新</Button>} style={{ minHeight: 400 }}>
                  {/* 来自 ASR 的字幕视频 */}
                  {state.subbed_video ? (
                    <div style={{ marginBottom: 16, padding: 12, background: '#e6f7ff', borderRadius: 4 }}>
                      <div style={{ fontWeight: 600, marginBottom: 8, color: '#1890ff' }}>📺 来自 ASR 的字幕视频</div>
                      <video src={state.subbed_video.url} controls style={{ width: '100%', maxHeight: 200, borderRadius: 4 }} />
                      <SpeedBar />
                    </div>
                  ) : (
                    <div style={{ color: '#999', marginBottom: 12 }}>先在 ASR 步骤烧录字幕</div>
                  )}
                  {/* BGM 列表 */}
                  <div style={{ fontWeight: 500, fontSize: 12, marginBottom: 4 }}>选择 BGM：</div>
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
                {selectedBgmId && state.subbed_video && (
                  <div style={{ textAlign: 'center', marginTop: 8 }}>
                    <Button type="primary" icon={<SoundOutlined />} loading={burningSub}                      onClick={async () => {
                      const bgm = bgmMaterials.find((m: any) => m.id === selectedBgmId)
                      if (!bgm) { message.warning('BGM 未找到'); return }
                      if (!stateRef.current.subbed_video) { message.warning('请先在 ASR 步骤烧录字幕'); return }
                      setBurningSub(true)
                      try {
                        // image_url 可能是相对路径，转成完整 URL
                        const bgmUrl = bgm.image_url?.startsWith('http') ? bgm.image_url : `http://114.117.242.17:3000${bgm.image_url}`
                        const res: any = await request.post('/studio/burn-subtitles', {
                          video_url: stateRef.current.subbed_video.url, segments: [],
                          session_id: sessionIdRef.current, bgm_url: bgmUrl
                        }, { timeout: 600000 })
                        if (res?.url) {
                          saveState({ bgm_mixed_video: { id: Date.now(), url: res.url } })
                          message.success('BGM 合成完成！前往导出步骤')
                        }
                      } catch { message.error('合成失败') }
                      setBurningSub(false)
                    }}>🎵 合成 BGM → 传给导出</Button>
                  </div>
                )}
                {/* 预览 BGM 混合结果 */}
                {state.bgm_mixed_video && (
                  <div style={{ marginTop: 16, padding: 12, background: '#f6ffed', borderRadius: 4, position: 'relative' }}>
                    <div style={{ fontWeight: 600, marginBottom: 8, color: '#52c41a' }}>✅ BGM 混合完成 → 前往导出
                      <DeleteOutlined style={{ position: 'absolute', top: 8, right: 8, color: '#ff4d4f', cursor: 'pointer', fontSize: 14 }}
                        onClick={() => { request.post('/studio/delete-clip', { file_url: stateRef.current.bgm_mixed_video?.url }).catch(() => {}); saveState({ bgm_mixed_video: null }) }} />
                    </div>
                    <video src={state.bgm_mixed_video.url} controls style={{ width: '100%', maxHeight: 200, borderRadius: 4 }} />
                      <SpeedBar />
                  </div>
                )}
              </div>
            )}
            {step === 7 && (
              <div>
                <Card title="导出" size="small" style={{ minHeight: 400 }}>
                  {/* 来自 BGM 的混合视频 */}
                  {state.bgm_mixed_video ? (
                    <div style={{ marginBottom: 16, padding: 12, background: '#f6ffed', borderRadius: 4, position: 'relative' }}>
                      <div style={{ fontWeight: 600, marginBottom: 8, color: '#52c41a' }}>✅ 来自 BGM 的最终视频
                        <DeleteOutlined style={{ position: 'absolute', top: 8, right: 8, color: '#ff4d4f', cursor: 'pointer', fontSize: 14 }}
                          onClick={() => { request.post('/studio/delete-clip', { file_url: stateRef.current.bgm_mixed_video?.url }).catch(() => {}); saveState({ bgm_mixed_video: null }) }} />
                      </div>
                      <video src={state.bgm_mixed_video.url} controls style={{ width: '100%', maxHeight: 200, borderRadius: 4 }} />
                      <SpeedBar />
                      <Space direction="vertical" style={{ width: '100%', marginTop: 12 }}>
                        <a href={state.bgm_mixed_video.url} target="_blank" rel="noreferrer">
                          <Button icon={<PlayCircleOutlined />} block>预览视频</Button>
                        </a>
                        <Button type="primary" icon={<VideoCameraOutlined />} loading={exporting} onClick={doExport} block>
                          {selectedBgmId ? '导出（含BGM）' : '导出'}
                        </Button>
                      </Space>
                    </div>
                  ) : (
                    <div style={{ color: '#999', marginBottom: 16, padding: 20, textAlign: 'center' }}>先在 BGM 步骤合成最终视频</div>
                  )}
                  {/* 已导出的列表 */}
                  {(state.exports || []).length > 0 && (
                    <div>
                      <div style={{ fontWeight: 500, marginBottom: 8, fontSize: 13 }}>📦 已导出记录</div>
                      <List size="small" dataSource={state.exports} renderItem={(e: any) => (
                        <List.Item onClick={() => saveState({ selected_export_id: e.id })}
                          style={{ cursor: 'pointer', background: state.selected_export_id === e.id ? '#e6f4ff' : undefined }}
                          actions={[
                            <span key="del" onClick={ev => { ev.stopPropagation(); deleteExport(e.id) }}><DeleteOutlined style={{ color: '#ff4d4f' }} /></span>
                          ]}>
                          <Space>
                            <PlayCircleOutlined />
                            <span style={{ fontWeight: state.selected_export_id === e.id ? 600 : 400 }}>{e.title}</span>
                            {e.bgm_name && <Tag color="orange" style={{ fontSize: 10 }}>🎵 {e.bgm_name}</Tag>}
                            <Tag style={{ fontSize: 10 }}>{e.script_template}</Tag>
                          </Space>
                        </List.Item>
                      )} />
                      {state.selected_export_id && (() => {
                        const sel = (state.exports || []).find((x: any) => x.id === state.selected_export_id)
                        return sel ? (
                          <div style={{ marginTop: 12 }}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <a href={sel.video_url} target="_blank" rel="noreferrer" style={{ width: '100%' }}>
                                <Button icon={<PlayCircleOutlined />} block>查看视频</Button>
                              </a>
                              <Button type="primary" icon={<VideoCameraOutlined />} block onClick={() => window.open(sel.video_url, '_blank')}>下载视频</Button>
                            </Space>
                          </div>
                        ) : null
                      })()}
                    </div>
                  )}
                </Card>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
              <Button disabled={step === 0} onClick={() => setStep(s => s - 1)}>← 上一步</Button>
              <Button disabled={step === 7} type="primary" onClick={() => setStep(s => s + 1)}>下一步 →</Button>
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
        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>名称</div>
        <Input placeholder="工作流名称" value={sessionTitle} onChange={e => setSessionTitle(e.target.value)} onPressEnter={createSession} style={{ marginBottom: 12 }} />
        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>生成模板</div>
        <Select placeholder="选择模板" style={{ width: '100%' }} value={sessionTemplate} onChange={setSessionTemplate} options={templates.map((t: string) => ({ value: t, label: t }))} />
        <div style={{ marginTop: 12, marginBottom: 4, fontSize: 12, color: '#666' }}>BGM 风格偏好（选填，智能剪辑/合成时自动匹配）</div>
        <Select placeholder="不限" allowClear style={{ width: '100%' }} value={sessionBgmStyle} onChange={setSessionBgmStyle} options={[
          { value: '', label: '🎵 不限' },
          { value: '轻快', label: '⚡ 轻快' },
          { value: '中性', label: '➡ 中性' },
          { value: '稳重', label: '🐢 稳重' },
        ]} />
      </Modal>
      <Modal title={productEditId ? '编辑产品介绍' : '添加产品介绍'} open={productModal} onOk={addProduct} onCancel={() => { setProductModal(false); setProductEditId(null); setProductTitle(''); setProductContent('') }} width={600}>
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
