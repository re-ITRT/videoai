import { useState, useEffect } from 'react'
import { Table, Button, Card, Tag, message, Space, Modal, Input, Tabs } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import request from '../../utils/request'

const { TextArea } = Input

export default function ScriptTemplates() {
  const [templates, setTemplates] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [editVisible, setEditVisible] = useState(false)
  const [editName, setEditName] = useState('')
  const [editFiles, setEditFiles] = useState<Record<string, string>>({})
  const [editTab, setEditTab] = useState('')
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/workflows/prompts')
      const list = Object.entries(res?.templates || {}).map(([name, info]: any) => ({
        name,
        ...info,
      }))
      setTemplates(list)
    } catch { message.error('加载模板失败') }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const openEdit = async (name: string) => {
    setEditName(name)
    setEditVisible(true)
    setEditTab('')
    try {
      const res: any = await request.get(`/workflows/prompts/${name}`)
      setEditFiles(res.files || {})
      const keys = Object.keys(res.files || {})
      if (keys.length > 0) setEditTab(keys[0])
    } catch { message.error('加载模板文件失败') }
  }

  const handleSave = async (filename: string) => {
    setSaving(true)
    try {
      await request.put(`/workflows/prompts/${editName}/${filename}`, { content: editFiles[filename] })
      message.success(`${filename} 已保存`)
    } catch { message.error('保存失败') }
    setSaving(false)
  }

  const columns = [
    { title: '模板名称', dataIndex: 'name', render: (v: string, r: any) => <a onClick={() => openEdit(v)}>{r.display_name || v}</a> },
    { title: '描述', dataIndex: 'description' },
    { title: 'Prompt 预览', dataIndex: 'prompt_preview', ellipsis: true },
    { title: '操作', render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r.name)}>编辑</Button>
      </Space>
    )},
  ]

  return (
    <Card title="剧本模板" extra={<Button type="primary" icon={<PlusOutlined />}>新建模板</Button>}>
      <Table dataSource={templates} columns={columns} rowKey="name" loading={loading} />

      <Modal title={`编辑模板 - ${editName}`} open={editVisible} onCancel={() => setEditVisible(false)} width={800} footer={null} destroyOnClose>
        {Object.keys(editFiles).length > 0 && (
          <Tabs activeKey={editTab} onChange={setEditTab} items={Object.keys(editFiles).map(k => ({
            key: k,
            label: k,
            children: (
              <div>
                <TextArea rows={20} value={editFiles[k]} onChange={e => setEditFiles({ ...editFiles, [k]: e.target.value })} style={{ fontFamily: 'monospace', fontSize: 13 }} />
                <Button type="primary" style={{ marginTop: 8 }} onClick={() => handleSave(k)} loading={saving}>保存 {k}</Button>
              </div>
            ),
          }))} />
        )}
      </Modal>
    </Card>
  )
}

