import { useState, useEffect } from 'react'
import { Card, Descriptions, Spin, Empty } from 'antd'
import { useParams } from 'react-router-dom'
import { getScript } from '../../utils/api'
import type { Script } from './types'
export default function ScriptDetail() {
  const { id } = useParams()
  const [script, setScript] = useState<Script | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => { if (id) getScript(Number(id)).then((res: any) => setScript(res)).catch(() => {}).finally(() => setLoading(false)) }, [id])
  if (loading) return <Spin />
  if (!script) return <Empty description="剧本不存在" />
  return (
    <Card title={`剧本 #${script.id}`}>
      <Descriptions column={2}>
        <Descriptions.Item label="模式">{script.mode}</Descriptions.Item>
        <Descriptions.Item label="风格">{script.video_style}</Descriptions.Item>
        <Descriptions.Item label="时长">{script.total_duration}s</Descriptions.Item>
        <Descriptions.Item label="创建时间">{new Date(script.created_at).toLocaleString()}</Descriptions.Item>
      </Descriptions>
      <h3 style={{ marginTop: 16 }}>分镜列表</h3>
      {script.scenes?.length ? <pre>{JSON.stringify(script.scenes, null, 2)}</pre> : <Empty description="暂无分镜数据" />}
    </Card>
  )
}
