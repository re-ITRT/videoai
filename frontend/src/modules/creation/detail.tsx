import { useState, useEffect } from 'react'
import { Card, Descriptions, Button, Spin, Empty, Steps, Tag, Space } from 'antd'
import { useParams, useNavigate } from 'react-router-dom'
import { getTask, getTaskLogs, retryTask } from '../../utils/api'
import type { VideoTask, TaskLog } from './types'

const WORKFLOW_STEPS = [
  { title: '素材', status: 'wait' },
  { title: '关键词', status: 'wait' },
  { title: '检索', status: 'wait' },
  { title: '剧本', status: 'wait' },
  { title: '配音', status: 'wait' },
  { title: '视频', status: 'wait' },
  { title: '合成', status: 'wait' },
]

function mapStateToStep(state: string): { current: number; status: 'process' | 'finish' | 'wait' | 'error' } {
  const states = [
    'CREATED', 'MATERIAL_EMBED', 'MATERIAL_EMBED_DONE',
    'QUERY_GENERATE', 'QUERY_GENERATE_DONE',
    'MATERIAL_SEARCH', 'MATERIAL_SEARCH_DONE',
    'SCRIPT_GENERATE', 'SCRIPT_GENERATE_DONE',
    'TTS_GENERATE', 'TTS_GENERATE_DONE',
    'VIDEO_GENERATE', 'VIDEO_GENERATE_DONE',
    'VIDEO_COMPOSE', 'VIDEO_COMPOSE_DONE',
    'EXPORTED',
  ]
  const idx = states.indexOf(state)
  if (state === 'FAILED') return { current: -1, status: 'error' }
  if (idx < 0) return { current: 0, status: 'process' }
  // Every 2 states = 1 step (running + done)
  const current = Math.min(Math.floor(idx / 2), 6)
  const status = idx % 2 === 1 ? 'finish' : 'process'
  return { current, status }
}

export default function CreationDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [task, setTask] = useState<VideoTask | null>(null)
  const [logs, setLogs] = useState<TaskLog[]>([])
  const [loading, setLoading] = useState(true)
  const [retrying, setRetrying] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [t, l] = await Promise.all([
        getTask(Number(id)).catch(() => null),
        getTaskLogs(Number(id)).catch(() => []),
      ])
      setTask(t as any)
      setLogs(l as any)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const handleRetry = async () => {
    if (!id) return
    setRetrying(true)
    try {
      await retryTask(Number(id))
      await load()
    } finally {
      setRetrying(false)
    }
  }

  if (loading) return <Card loading><Spin /></Card>
  if (!task) return <Empty description="任务不存在" />

  const stepInfo = mapStateToStep(task.state || task.status || 'CREATED')

  return (
    <Card
      title={`任务 #${task.id}`}
      extra={<Button onClick={() => navigate('/creation')}>返回</Button>}
    >
      <Steps
        current={stepInfo.current}
        status={stepInfo.status}
        size="small"
        style={{ marginBottom: 24 }}
        items={WORKFLOW_STEPS.map((s, i) => ({
          title: s.title,
          status: i < stepInfo.current ? 'finish' : i === stepInfo.current ? stepInfo.status : 'wait' as any,
        }))}
      />

      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="状态"><Tag color={stepInfo.status === 'error' ? 'red' : 'blue'}>{task.state || task.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="画幅">{task.aspect_ratio || '9:16'}</Descriptions.Item>
        <Descriptions.Item label="模式">{task.auto_mode ? '自动' : '手动'}</Descriptions.Item>
        <Descriptions.Item label="重试">{task.retry_count || 0} 次</Descriptions.Item>
        <Descriptions.Item label="创建时间">{task.created_at ? new Date(task.created_at).toLocaleString() : '-'}</Descriptions.Item>
      </Descriptions>

      {stepInfo.status === 'error' && (
        <Space style={{ marginTop: 16 }}>
          <span style={{ color: 'red' }}>错误: {task.error_msg || task.error_message || '未知错误'}</span>
          <Button type="primary" danger loading={retrying} onClick={handleRetry}>重试</Button>
        </Space>
      )}

      {task.output_url && (
        <div style={{ marginTop: 16 }}>
          <video src={task.output_url} controls style={{ maxWidth: '100%' }} />
        </div>
      )}

      {logs.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h4>执行日志</h4>
          {logs.map((log: any) => (
            <div key={log.id} style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>
              [{log.step}] {log.status} — {log.model_used && `模型: ${log.model_used}`} {log.duration_ms ? `耗时: ${log.duration_ms}ms` : ''}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
