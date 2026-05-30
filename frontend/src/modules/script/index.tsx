import { useState, useEffect } from 'react'
import { Table, Button, Card, message, Space, Modal, Input, Tabs, Form } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import request from '../../utils/request'

const { TextArea } = Input

/** 把 system.md 按 # 标题拆成 { "角色定义": "...", "任务目标": "..." } */
function parseSections(text: string): Record<string, string> {
  const sections: Record<string, string> = {}
  const lines = text.split('\n')
  let key = ''
  let buf: string[] = []
  for (const line of lines) {
    if (line.startsWith('# ')) {
      if (key && buf.length) sections[key] = buf.join('\n').trim()
      key = line.replace('# ', '').trim()
      buf = []
    } else {
      buf.push(line)
    }
  }
  if (key && buf.length) sections[key] = buf.join('\n').trim()
  return sections
}

/** 把 sections 重新组装回 system.md */
function buildSystemMd(sections: Record<string, string>): string {
  return Object.entries(sections)
    .filter(([, v]) => v)
    .map(([k, v]) => `# ${k}\n${v}`)
    .join('\n\n')
}

export default function ScriptTemplates() {
  const [templates, setTemplates] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [editVisible, setEditVisible] = useState(false)
  const [editName, setEditName] = useState('')
  const [sysSections, setSysSections] = useState<Record<string, string>>({})
  const [userPrompt, setUserPrompt] = useState('')
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/workflows/prompts')
      const list = Object.entries(res?.templates || {}).map(([name, info]: any) => ({ name, ...info }))
      setTemplates(list)
    } catch { message.error('加载模板失败') }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const openEdit = async (name: string) => {
    setEditName(name)
    setEditVisible(true)
    try {
      const res: any = await request.get(`/workflows/prompts/${name}`)
      const sys = res.files?.['system.md'] || ''
      setSysSections(parseSections(sys))
      setUserPrompt(res.files?.['user.md.j2'] || '')
    } catch { message.error('加载模板失败') }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await request.put(`/workflows/prompts/${editName}/system.md`, { content: buildSystemMd(sysSections) })
      if (userPrompt) {
        await request.put(`/workflows/prompts/${editName}/user.md.j2`, { content: userPrompt })
      }
      message.success('模板已保存')
    } catch { message.error('保存失败') }
    setSaving(false)
  }

  const columns = [
    { title: '模板名称', dataIndex: 'name', render: (v: string, r: any) => <a onClick={() => openEdit(v)}>{r.display_name || v}</a> },
    { title: '描述', dataIndex: 'description' },
    { title: 'Prompt 预览', dataIndex: 'prompt_preview', ellipsis: true },
    { title: '操作', render: (_: any, r: any) => (
      <Space><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r.name)}>编辑</Button></Space>
    )},
  ]

  const sectionKeys = Object.keys(sysSections)

  return (
    <Card title="剧本模板" extra={<Button type="primary" icon={<PlusOutlined />}>新建模板</Button>}>
      <Table dataSource={templates} columns={columns} rowKey="name" loading={loading} />

      <Modal title={`编辑模板 - ${editName}`} open={editVisible} onCancel={() => setEditVisible(false)}
        width={700} footer={null} destroyOnClose>
        <Tabs defaultActiveKey="role" items={[
          ...sectionKeys.map(k => ({
            key: k,
            label: k,
            children: (
              <TextArea rows={8} value={sysSections[k] || ''}
                onChange={e => setSysSections({ ...sysSections, [k]: e.target.value })}
                style={{ fontSize: 14 }} />
            ),
          })),
          {
            key: 'user_prompt',
            label: '用户 Prompt',
            children: (
              <TextArea rows={8} value={userPrompt}
                onChange={e => setUserPrompt(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: 13 }} />
            ),
          },
        ]} />
        <Button type="primary" style={{ marginTop: 12 }} onClick={handleSave} loading={saving}>保存模板</Button>
      </Modal>
    </Card>
  )
}
