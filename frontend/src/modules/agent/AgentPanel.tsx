import { useState, useEffect, useRef } from 'react'
import { Card, Button, Input, List, Typography, Tag, Spin, Space, Drawer } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined, FolderOpenOutlined } from '@ant-design/icons'

const { Text } = Typography

interface Session {
  id: number
  title: string
  message_count: number
  created_at: string
}

interface ChatMsg {
  id: number
  role: string
  content?: string
  tool_calls?: any[]
}

interface SessionFile {
  id: number
  file_type: string
  filename?: string
  file_url?: string
  description?: string
}

const API = '/api/v1/agent'

function getToken() {
  return localStorage.getItem('token') || ''
}

async function api(path: string, options?: any) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`,
      ...options?.headers,
    },
  })
  if (!res.ok) throw new Error((await res.json()).detail || '请求失败')
  return res.json()
}

export default function AgentPanel() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSession, setCurrentSession] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [files, setFiles] = useState<SessionFile[]>([])
  const [fileDrawer, setFileDrawer] = useState(false)
  const msgEnd = useRef<HTMLDivElement>(null)

  const loadSessions = async () => {
    try { setSessions(await api('/sessions')) } catch {}
  }

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

  useEffect(() => {
    if (currentSession) loadMessages(currentSession)
  }, [currentSession])

  useEffect(() => {
    msgEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const newSession = async () => {
    const s = await api('/sessions', { method: 'POST', body: JSON.stringify({}) })
    setSessions([s, ...sessions])
    setCurrentSession(s.id)
    setMessages([])
    setFiles([])
  }

  const sendMessage = async () => {
    if (!input.trim() || !currentSession || loading) return
    setLoading(true)
    const userMsg: ChatMsg = { id: Date.now(), role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    try {
      const data = await api(`/sessions/${currentSession}/chat`, {
        method: 'POST',
        body: JSON.stringify({ message: userMsg.content }),
      })
      const aiMsg: ChatMsg = {
        id: data.message.id,
        role: data.message.role,
        content: data.message.content,
        tool_calls: data.message.tool_calls,
      }
      setMessages(prev => [...prev, aiMsg])
      // 刷新文件
      try { setFiles(await api(`/sessions/${currentSession}/files`)) } catch {}
    } catch (e: any) {
      setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: `❌ ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  const ToolCallTag = ({ tc }: { tc: any }) => (
    <Tag color="purple" style={{ marginBottom: 4 }}>
      🔧 {tc.function?.name}(
      {tc.function?.arguments && JSON.stringify(JSON.parse(tc.function.arguments)).slice(0, 60)})
    </Tag>
  )

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 180px)' }}>
      {/* 左侧 Session 列表 */}
      <Card title="对话" size="small" style={{ width: 220, flexShrink: 0 }}>
        <Button type="primary" size="small" block onClick={newSession} style={{ marginBottom: 8 }}>
          + 新对话
        </Button>
        <List
          size="small"
          dataSource={sessions}
          renderItem={(s) => (
            <List.Item
              onClick={() => setCurrentSession(s.id)}
              style={{ cursor: 'pointer', background: currentSession === s.id ? '#e6f4ff' : undefined, padding: '4px 8px' }}
            >
              <Text ellipsis style={{ maxWidth: 160 }}>{s.title}</Text>
            </List.Item>
          )}
        />
      </Card>

      {/* 中间聊天区 */}
      <Card
        title={currentSession ? `对话 #${currentSession}` : '选择或创建对话'}
        size="small"
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        extra={
          currentSession ? (
            <Button size="small" icon={<FolderOpenOutlined />} onClick={() => setFileDrawer(true)}>
              文件
            </Button>
          ) : null
        }
      >
        <div style={{ flex: 1, overflow: 'auto', marginBottom: 12 }}>
          {messages.map((m) => (
            <div key={m.id} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                {m.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                <Text strong type={m.role === 'user' ? 'secondary' : 'success'}>
                  {m.role === 'user' ? '你' : 'AI'}
                </Text>
              </div>
              {m.tool_calls?.map((tc, i) => <ToolCallTag key={i} tc={tc} />)}
              {m.content && <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, paddingLeft: 22 }}>{m.content}</div>}
            </div>
          ))}
          {loading && <Spin style={{ display: 'block', margin: '12px auto' }} />}
          <div ref={msgEnd} />
        </div>

        <Space.Compact style={{ width: '100%' }}>
          <Input.TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); sendMessage() } }}
            placeholder="输入消息..."
            rows={2}
            disabled={!currentSession || loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={sendMessage}
            loading={loading}
            disabled={!currentSession}
          />
        </Space.Compact>
      </Card>

      {/* 右侧文件抽屉 */}
      <Drawer
        title="Session 文件"
        placement="right"
        onClose={() => setFileDrawer(false)}
        open={fileDrawer}
        width={350}
      >
        {['tts', 'video_clips', 'final_videos', 'materials', 'scripts'].map((type) => {
          const typeFiles = files.filter(f => f.file_type === type)
          if (typeFiles.length === 0) return null
          return (
            <div key={type} style={{ marginBottom: 16 }}>
              <Text strong style={{ fontSize: 13 }}>{{
                tts: '🎤 语音', video_clips: '🎬 视频片段',
                final_videos: '🎥 成品视频', materials: '📦 素材',
                scripts: '📝 剧本',
              }[type]}</Text>
              {typeFiles.map(f => (
                <Card key={f.id} size="small" style={{ marginTop: 8 }}>
                  <Text ellipsis>{f.filename || f.description || f.file_url?.slice(0, 40)}</Text>
                  {f.file_url && (
                    <div style={{ marginTop: 4 }}>
                      {f.file_type === 'final_videos' || f.file_type === 'video_clips'
                        ? <video src={f.file_url} controls style={{ width: '100%', maxHeight: 200 }} />
                        : f.file_type === 'tts'
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
