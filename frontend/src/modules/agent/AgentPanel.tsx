import { useState, useEffect, useRef } from 'react'
import { Button, Input, List, Typography, Tag, Spin, Drawer, Modal, message, Card } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined, FolderOpenOutlined, DeleteOutlined, PlusOutlined, LoadingOutlined } from '@ant-design/icons'

const { Text } = Typography
const { TextArea } = Input

interface Session { id: number; title: string; message_count: number; created_at: string }
interface ChatMsg { id: number; role: string; content?: string; tool_calls?: any[]; tool_name?: string }
interface SessionFile { id: number; file_type: string; filename?: string; file_url?: string; description?: string }

const API = '/api/v1/agent'

function getToken() { return localStorage.getItem('token') || '' }

async function api(path: string, options?: any) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}`, ...options?.headers },
  })
  if (!res.ok) throw new Error((await res.json()).detail || '请求失败')
  return res.json()
}

const fileIcons: Record<string, string> = {
  tts: '🎤', video_clip: '🎬', final_video: '🎥', material: '📦', script: '📝',
}

export default function AgentPanel() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSession, setCurrentSession] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [toolStatus, setToolStatus] = useState<string | null>(null)
  const [files, setFiles] = useState<SessionFile[]>([])
  const [fileDrawer, setFileDrawer] = useState(false)
  const [newModal, setNewModal] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const msgEnd = useRef<HTMLDivElement>(null)

  const loadSessions = async () => { try { setSessions(await api('/sessions')) } catch {} }
  const loadMessages = async (sid: number) => {
    try {
      const [msgs, f] = await Promise.all([
        api(`/sessions/${sid}/messages`),
        api(`/sessions/${sid}/files`),
      ])
      setMessages(msgs)
      setFiles(f)
    } catch {}
  }

  useEffect(() => { loadSessions() }, [])
  useEffect(() => { if (currentSession) loadMessages(currentSession) }, [currentSession])
  useEffect(() => { msgEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const toolNameLabel: Record<string, string> = {
    query_generate: '🔍 生成搜索关键词',
    material_search: '📂 搜索素材',
    generate_script: '📝 生成剧本',
    generate_tts: '🎤 生成语音',
    generate_video: '🎬 生成视频片段',
    compose_video: '🎥 合成最终视频',
  }

  const newSession = async () => { setNewModal(true) }
  const confirmNewSession = async () => {
    const s = await api('/sessions', { method: 'POST', body: JSON.stringify({ title: newTitle || '新对话' }) })
    setSessions([s, ...sessions])
    setCurrentSession(s.id)
    setMessages([])
    setFiles([])
    setNewModal(false)
    setNewTitle('')
  }

  const deleteSession = async (sid: number) => {
    if (!confirm('确定删除该对话？')) return
    try {
      await api(`/sessions/${sid}`, { method: 'DELETE' })
      setSessions(sessions.filter(s => s.id !== sid))
      if (currentSession === sid) { setCurrentSession(null); setMessages([]); setFiles([]) }
    } catch { message.error('删除失败') }
  }

  const sendMessage = async () => {
    if (!input.trim() || !currentSession || loading) return
    setLoading(true)
    const userMsg: ChatMsg = { id: Date.now(), role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setToolStatus('🤖 AI思考中...')

    try {
      await api(`/sessions/${currentSession}/chat`, {
        method: 'POST',
        body: JSON.stringify({ message: userMsg.content }),
      })
      // Reload all messages to capture tool calls + final response
      const [msgs, f] = await Promise.all([
        api(`/sessions/${currentSession}/messages`),
        api(`/sessions/${currentSession}/files`),
      ])
      setMessages(msgs.filter((m: ChatMsg) => m.role !== 'tool'))
      setFiles(f)
    } catch (e: any) {
      setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: `❌ ${e.message}` }])
    } finally {
      setLoading(false)
      setToolStatus(null)
    }
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 120px)' }}>
      {/* 左侧 Session 列表 */}
      <div style={{ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', background: '#fafafa', borderRadius: 8, border: '1px solid #f0f0f0' }}>
        <div style={{ padding: '10px 12px', borderBottom: '1px solid #f0f0f0' }}>
          <Button type="primary" size="small" block icon={<PlusOutlined />} onClick={newSession}>新对话</Button>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <List
            size="small"
            dataSource={sessions}
            renderItem={(s) => (
              <List.Item
                onClick={() => setCurrentSession(s.id)}
                style={{
                  cursor: 'pointer', padding: '8px 12px',
                  background: currentSession === s.id ? '#e6f4ff' : undefined,
                  borderBottom: '1px solid #f5f5f5',
                }}
                actions={[<Button key="del" type="text" size="small" danger icon={<DeleteOutlined />}
                  onClick={(e) => { e.stopPropagation(); deleteSession(s.id) }} />]}
              >
                <Text ellipsis style={{ maxWidth: 110, fontSize: 13 }}>{s.title}</Text>
              </List.Item>
            )}
          />
        </div>
      </div>

      {/* 中间聊天区 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f5f5f5', borderRadius: 8, overflow: 'hidden' }}>
        {/* 顶部标题栏 */}
        <div style={{
          padding: '10px 16px', background: '#fff', borderBottom: '1px solid #e8e8e8',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <Text strong>{currentSession ? `对话 #${currentSession}` : '选择或创建对话'}</Text>
          {currentSession && (
            <Button size="small" icon={<FolderOpenOutlined />} onClick={() => setFileDrawer(true)}>文件</Button>
          )}
        </div>

        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
          {messages.map((m) => (
            <div key={m.id} style={{
              display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
              marginBottom: 16,
            }}>
              {m.role !== 'user' && (
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#1677ff', display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 8, flexShrink: 0 }}>
                  <RobotOutlined style={{ color: '#fff', fontSize: 16 }} />
                </div>
              )}
              <div style={{ maxWidth: '70%' }}>
                {/* 工具调用标签 */}
                {m.tool_calls?.map((tc, i) => (
                  <div key={i} style={{ marginBottom: 4 }}>
                    <Tag color="purple" style={{ fontSize: 12, borderRadius: 4 }}>
                      🔧 {toolNameLabel[tc.function?.name] || tc.function?.name}
                    </Tag>
                  </div>
                ))}
                {/* 消息气泡 */}
                {m.content && (
                  <div style={{
                    padding: '10px 14px',
                    borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                    background: m.role === 'user' ? '#1677ff' : '#fff',
                    color: m.role === 'user' ? '#fff' : '#333',
                    fontSize: 14,
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
                  }}>
                    {m.content}
                  </div>
                )}
              </div>
              {m.role === 'user' && (
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#52c41a', display: 'flex', alignItems: 'center', justifyContent: 'center', marginLeft: 8, flexShrink: 0 }}>
                  <UserOutlined style={{ color: '#fff', fontSize: 16 }} />
                </div>
              )}
            </div>
          ))}

          {/* 工具执行中指示器 */}
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#1677ff', display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 8 }}>
                <RobotOutlined style={{ color: '#fff', fontSize: 16 }} />
              </div>
              <div style={{ background: '#fff', borderRadius: 16, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.06)' }}>
                <Spin indicator={<LoadingOutlined style={{ fontSize: 18 }} spin />} />
                <Text type="secondary" style={{ fontSize: 13 }}>{toolStatus || '🤖 思考中...'}</Text>
              </div>
            </div>
          )}
          <div ref={msgEnd} />
        </div>

        {/* 底部输入框 */}
        <div style={{ padding: '12px 16px', background: '#fff', borderTop: '1px solid #e8e8e8' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); sendMessage() } }}
              placeholder="输入消息... (Shift+Enter 换行)"
              rows={2}
              disabled={!currentSession || loading}
              style={{ borderRadius: 8, resize: 'none' }}
            />
            <Button
              type="primary"
              icon={loading ? <LoadingOutlined /> : <SendOutlined />}
              onClick={sendMessage}
              loading={loading}
              disabled={!currentSession}
              style={{ height: 44, width: 44, borderRadius: 8 }}
            />
          </div>
        </div>
      </div>

      <Modal title="新建对话" open={newModal} onOk={confirmNewSession} onCancel={() => setNewModal(false)}>
        <Input placeholder="输入对话名称" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} onPressEnter={confirmNewSession} />
      </Modal>

      <Drawer title="Session 文件" placement="right" onClose={() => setFileDrawer(false)} open={fileDrawer} width={350}>
        {['tts', 'video_clip', 'final_video', 'material', 'script'].map((type) => {
          const typeFiles = files.filter(f => f.file_type === type)
          if (typeFiles.length === 0) return null
          return (
            <div key={type} style={{ marginBottom: 16 }}>
              <Text strong style={{ fontSize: 13 }}>{fileIcons[type]} {{
                tts: '语音', video_clip: '视频片段', final_video: '成品视频', material: '素材', script: '剧本',
              }[type]}</Text>
              {typeFiles.map(f => (
                <Card key={f.id} size="small" style={{ marginTop: 8 }}>
                  <Text ellipsis>{f.filename || f.description || f.file_url?.slice(0, 40)}</Text>
                  {f.file_url && (
                    <div style={{ marginTop: 4 }}>
                      {type === 'final_video' || type === 'video_clip'
                        ? <video src={f.file_url} controls style={{ width: '100%', maxHeight: 200 }} />
                        : type === 'tts'
                        ? <audio src={f.file_url} controls style={{ width: '100%' }} />
                        : <a href={f.file_url} target="_blank">查看</a>
                      }
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )
        })}
        {files.length === 0 && <Text type="secondary">暂无文件</Text>}
      </Drawer>
    </div>
  )
}
