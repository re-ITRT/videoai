import { useState, useRef, useEffect } from 'react'
import { Modal, Input, Button, Space, Spin, message, List } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons'
import request from '../../utils/request'

interface Props {
  sessionId: number
  scriptName: string
  visible: boolean
  onClose: () => void
  onScriptUpdated?: (script: any) => void
}

export default function AiScriptEditor({ sessionId, scriptName, visible, onClose, onScriptUpdated }: Props) {
  const [messages, setMessages] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (visible) {
      setMessages([])
      setInput('')
    }
  }, [visible])

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const userMsg = { role: 'user', content: input }
    const newMsgs = [...messages, userMsg]
    setMessages(newMsgs)
    setInput('')
    setLoading(true)
    try {
      const res: any = await request.post('/studio/ai-edit', {
        session_id: sessionId,
        script_name: scriptName,
        messages: newMsgs,
      })
      if (res.error) {
        message.error(res.error)
        setMessages(newMsgs)
        return
      }
      setMessages(res.messages || [])
      if (res.script && onScriptUpdated) {
        onScriptUpdated(res.script)
      }
    } catch {
      message.error('请求失败')
    }
    setLoading(false)
  }

  return (
    <Modal title="AI 编辑剧本" open={visible} onCancel={onClose}
      width={600} footer={null} destroyOnClose>
      <div ref={listRef} style={{ maxHeight: 400, overflow: 'auto', marginBottom: 12 }}>
        {messages.filter(m => m.role !== 'system').map((m, i) => (
          <div key={i} style={{
            display: 'flex', gap: 8, marginBottom: 8,
            flexDirection: m.role === 'user' ? 'row-reverse' : 'row',
          }}>
            <div style={{
              background: m.role === 'user' ? '#1677ff' : '#f0f0f0',
              color: m.role === 'user' ? '#fff' : '#000',
              padding: '6px 12px', borderRadius: 8, maxWidth: '80%',
              fontSize: 13, whiteSpace: 'pre-wrap',
            }}>
              {m.role === 'user' ? m.content : (
                <>
                  {m.tool_calls?.length > 0 && (
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                      🔧 调用了 {m.tool_calls.map((t: any) => t.function.name).join(', ')}
                    </div>
                  )}
                  {m.content}
                </>
              )}
            </div>
          </div>
        ))}
        {loading && <Spin size="small" style={{ display: 'block', margin: '0 auto' }} />}
      </div>
      <Space.Compact style={{ width: '100%' }}>
        <Input value={input} onChange={e => setInput(e.target.value)}
          onPressEnter={send} placeholder="输入需求，如：把场景2时长改为8秒..." disabled={loading} />
        <Button type="primary" icon={<SendOutlined />} onClick={send} loading={loading}>发送</Button>
      </Space.Compact>
    </Modal>
  )
}
