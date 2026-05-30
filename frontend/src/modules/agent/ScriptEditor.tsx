import { useState, useEffect } from 'react'
import { Modal, Input, Button, message, Spin } from 'antd'
import { getSessionScript, updateSessionScript } from '../../utils/api'

const { TextArea } = Input

export default function ScriptEditor({ sessionId, visible, onClose }: {
  sessionId: number; visible: boolean; onClose: () => void
}) {
  const [script, setScript] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!visible || !sessionId) return
    setLoading(true)
    getSessionScript(sessionId).then((res: any) => {
      setScript(JSON.stringify(res?.script || res, null, 2))
    }).catch(() => message.error('加载剧本失败')).finally(() => setLoading(false))
  }, [visible, sessionId])

  const handleSave = async () => {
    setSaving(true)
    try {
      const parsed = JSON.parse(script)
      await updateSessionScript(sessionId, { script: parsed })
      message.success('剧本已保存')
    } catch (e: any) {
      message.error('JSON 格式错误: ' + e.message)
    }
    setSaving(false)
  }

  return (
    <Modal title={`剧本编辑 - Session #${sessionId}`} open={visible} onCancel={onClose}
      width={800} footer={null} destroyOnClose>
      {loading ? <Spin /> : (
        <div>
          <TextArea rows={25} value={script} onChange={e => setScript(e.target.value)}
            style={{ fontFamily: 'monospace', fontSize: 13 }} />
          <Button type="primary" style={{ marginTop: 8 }} onClick={handleSave} loading={saving}>
            保存
          </Button>
        </div>
      )}
    </Modal>
  )
}
