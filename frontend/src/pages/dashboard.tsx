import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Skeleton } from 'antd'
import { VideoCameraOutlined, FileTextOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { getMaterials, getTasks } from '../utils/api'

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ materials: 0, scripts: 0, tasks: 0 })

  useEffect(() => {
    Promise.all([
      getMaterials().catch(() => []),
      getTasks().catch(() => []),
    ]).then(([mats, tasks]: any[]) => {
      setStats({
        materials: Array.isArray(mats) ? mats.length : mats?.items?.length || 0,
        scripts: 0,
        tasks: Array.isArray(tasks) ? tasks.length : 0,
      })
    }).finally(() => setLoading(false))
  }, [])

  const cards = [
    { title: '素材总数', value: stats.materials, icon: <VideoCameraOutlined /> },
    { title: '剧本总数', value: stats.scripts, icon: <FileTextOutlined /> },
    { title: '视频任务', value: stats.tasks, icon: <ThunderboltOutlined /> },
  ]

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>工作台</h2>
      <Row gutter={16}>
        {cards.map((c, i) => (
          <Col span={8} key={i}>
            <Card>
              {loading ? <Skeleton active paragraph={{ rows: 1 }} /> : <Statistic title={c.title} value={c.value} prefix={c.icon} />}
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
