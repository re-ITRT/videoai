import { useState, useEffect } from 'react'
import { Table, Button, Card, Tag, message } from 'antd'
import { getTasks } from '../../utils/api'
import type { VideoTask } from './types'
import { useNavigate } from 'react-router-dom'
const stateColor: Record<string, string> = { pending: 'default', processing: 'processing', completed: 'success', failed: 'error' }
const stateLabel: Record<string, string> = { pending: '等待中', processing: '生成中', completed: '已完成', failed: '失败' }
export default function CreationList() {
  const [tasks, setTasks] = useState<VideoTask[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const load = async () => { setLoading(true); try { const res: any = await getTasks(); setTasks(res.items || res || []) } catch { message.error('加载失败') }; setLoading(false) }
  useEffect(() => { load() }, [])
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '状态', dataIndex: 'state', render: (v: string) => <Tag color={stateColor[v]}>{stateLabel[v] || v}</Tag> },
    { title: '进度', render: (_: any, r: VideoTask) => `${r.current_step}/${r.total_steps}` },
    { title: '比例', dataIndex: 'aspect_ratio' },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() },
    { title: '操作', render: (_: any, r: VideoTask) => <Button size="small" onClick={() => navigate(`/creation/${r.id}`)}>详情</Button> },
  ]
  return (<Card title="视频创作"><Table dataSource={tasks} columns={columns} rowKey="id" loading={loading} /></Card>)
}
