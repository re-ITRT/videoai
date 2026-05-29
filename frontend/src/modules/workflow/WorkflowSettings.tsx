import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Spin, message, Tag, Space, Tabs, Modal } from 'antd'
import {
  getWorkflowConfigs, updateWorkflowConfig, getAvailableWorkflows,
} from '../../utils/api'
import request from '../../utils/request'

const { TextArea } = Input

interface WorkflowField {
  key: string
  label: string
  type: string
  placeholder?: string
}

function PromptEditor({ workflowName, visible, onClose }: { workflowName: string; visible: boolean; onClose: () => void }) {
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
    } catch {
      message.error('保存失败')
    }
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

export default function WorkflowSettings() {
  const [configs, setConfigs] = useState<Record<string, any>>({})
  const [availMeta, setAvailMeta] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [promptWorkflow, setPromptWorkflow] = useState<string | null>(null)

  const load = async () => {
    try {
      const [cfgRes, availRes] = await Promise.all([
        getWorkflowConfigs(),
        getAvailableWorkflows(),
      ])
      const cfgs: Record<string, any> = {}
      for (const c of (cfgRes as any)) cfgs[c.workflow_name] = c
      setConfigs(cfgs)
      setAvailMeta((availRes as any).workflows || {})
    } catch { message.error('加载工作流配置失败') }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleSave = async (name: string, values: any) => {
    setSaving(name)
    try {
      const current = configs[name]?.config || {}
      await updateWorkflowConfig(name, { config: { ...current, ...values } })
      message.success(`${name} 配置已保存`)
    } catch { message.error('保存失败') }
    setSaving(null)
  }

  if (loading) return <Spin />

  const names = Object.keys(availMeta)
  if (names.length === 0) return <div style={{ color: '#999' }}>暂无可用工作流</div>

  return (
    <div>
      {names.map((name) => {
        const meta = availMeta[name]
        const cfg = configs[name]?.config || {}
        return (
          <Card
            key={name}
            title={
              <Space>
                <span>{meta.name}</span>
                <Tag color={configs[name]?.enabled ? 'green' : 'default'}>
                  {configs[name]?.enabled ? '本地' : 'Coze'}
                </Tag>
              </Space>
            }
            size="small"
            style={{ marginBottom: 12 }}
            extra={<Button size="small" onClick={() => setPromptWorkflow(name)}>编辑 Prompt</Button>}
          >
            <p style={{ color: '#666', fontSize: 13, marginBottom: 12 }}>{meta.description}</p>
            <Form
              layout="vertical"
              initialValues={cfg}
              onFinish={(values) => handleSave(name, values)}
            >
              {(meta.fields || []).map((f: any) => (
                <Form.Item key={f.key} name={f.key} label={f.label}>
                  {f.type === 'password' ? (
                    <Input.Password placeholder={f.placeholder} />
                  ) : (
                    <Input placeholder={f.placeholder} />
                  )}
                </Form.Item>
              ))}
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving === name}>
                  保存配置
                </Button>
              </Form.Item>
            </Form>
          </Card>
        )
      })}
      {promptWorkflow && (
        <PromptEditor workflowName={promptWorkflow} visible={!!promptWorkflow} onClose={() => setPromptWorkflow(null)} />
      )}
    </div>
  )
}
