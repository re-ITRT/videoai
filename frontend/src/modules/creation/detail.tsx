import { useState, useEffect } from 'react'
import { Card, Descriptions, Button, Spin, Empty, Progress } from 'antd'
import { useParams, useNavigate } from 'react-router-dom'
import { getTask, exportVideo } from '../../utils/api'
import type { VideoTask } from './types'
export default function CreationDetail() {
  const { id } = useParams(); const navigate = useNavigate()
  const [task, setTask] = useState<VideoTask | null>(null); const [loading, setLoading] = useState(true)
  useEffect(() => { if (id) getTask(Number(id)).then((res: any) => setTask(res)).catch(() => {}).finally(() => setLoading(false)) }, [id])
  if (loading) return <Spin />
  if (!task) return <Empty description="任务不存在" />
  const progress = task.total_steps > 0 ? Math.round((task.current_step / task.total_steps) * 100) : 0
  return (
    <Card title={`任务 #${task.id}`} extra={<Button onClick={() => navigate('/creation')}>返回</Button>}>
      <Descriptions column={2}>
        <Descriptions.Item label="状态">{task.state}</Descriptions.Item>
        <Descriptions.Item label="比例">{task.aspect_ratio}</Descriptions.Item>
        <Descriptions.Item label="重试次数">{task.retry_count}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{new Date(task.created_at).toLocaleString()}</Descriptions.Item>
      </Descriptions>
      <Progress percent={progress} style={{ margin: '16px 0' }} />
      {task.error_message && <div style={{ color: 'red' }}>错误: {task.error_message}</div>}
      {task.video_url && (<div style={{ marginTop: 16 }}><video src={task.video_url} controls style={{ maxWidth: '100%' }} /><Button type="primary" style={{ marginTop: 8 }} onClick={() => exportVideo(task!.id)}>导出视频</Button></div>)}
    </Card>
  )
}
