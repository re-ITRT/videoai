import { useState, useEffect } from 'react'
import { Modal, Tabs, Input, Button, message } from 'antd'
import request from '../../utils/request'

const { TextArea } = Input

export default function PromptEditor({ workflowName, visible, onClose }: {
  workflowName: string; visible: boolean; onClose: () => void
}) {
  const [files, setFiles] = useState<Record<string, string>>({})
  const [activeTab, setActiveTab] = useState<string>('')

  useEffect(() => {
    if (!visible) return
    request.get(`/workflows/prompts/${workflowName}`).then((res: any) => {
      setFiles(res.files || {})
      const keys = Object.keys(res.files || {})
      if (keys.length > 0) setActiveTab(keys[0])
    }).catch(() => message.error('加载prompt失败'))
  }, [visible, workflowName])

  const handleSave = async (filename: string) => {
    try {
      await request.put(`/workflows/prompts/${workflowName}/${filename}`, { content: files[filename] })
      message.success(`${filename} 已保存`)
    } catch { message.error('保存失败') }
  }

  const keys = Object.keys(files)
  if (keys.length === 0) return null

  return (
    <Modal title={`Prompt 编辑器 - ${workflowName}`} open={visible} onCancel={onClose} width={800} footer={null}>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={keys.map(k => ({
        key: k,
        label: k,
        children: (
          <div>
            <TextArea rows={20} value={files[k]} onChange={e => setFiles({ ...files, [k]: e.target.value })} />
            <Button type="primary" style={{ marginTop: 8 }} onClick={() => handleSave(k)}>保存 {k}</Button>
          </div>
        ),
      }))} />
    </Modal>
  )
}
