import { useState, useEffect } from 'react'
import { Table, Button, Card, Tag, message, Space } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { getScripts, deleteScript } from '../../utils/api'
import type { Script } from './types'
import { useNavigate } from 'react-router-dom'
export default function ScriptList() {
  const [scripts, setScripts] = useState<Script[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const load = async () => {
    setLoading(true)
    try { const res: any = await getScripts(); setScripts(res.items || res || []) }
    catch { message.error('加载失败') }
    setLoading(false)
  }
  useEffect(() => { load() }, [])
  const handleDelete = async (id: number) => {
    try { await deleteScript(id); message.success('删除成功'); load() }
    catch { message.error('删除失败') }
  }
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '模式', dataIndex: 'mode', render: (v: string) => <Tag>{v}</Tag> },
    { title: '风格', dataIndex: 'video_style' },
    { title: '时长(s)', dataIndex: 'total_duration' },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() },
    { title: '操作', render: (_: any, r: Script) => (<Space><Button size="small" onClick={() => navigate(`/script/${r.id}`)}>查看</Button><Button danger icon={<DeleteOutlined />} size="small" onClick={() => handleDelete(r.id)} /></Space>)},
  ]
  return (<Card title="剧本中心" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/script/generate')}>生成剧本</Button>}><Table dataSource={scripts} columns={columns} rowKey="id" loading={loading} /></Card>)
}
