import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Skeleton, Tabs, List, Tag, Empty, Spin, Button, message } from 'antd'
import { VideoCameraOutlined, FileTextOutlined, ThunderboltOutlined, AppstoreOutlined, PlayCircleOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import request from '../utils/request'
import { getMaterials, getTasks } from '../utils/api'
import StudioPage from '../modules/studio/StudioPage'

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ materials: 0, scripts: 0, tasks: 0 })
  const [videos, setVideos] = useState<any[]>([])
  const [videosLoading, setVideosLoading] = useState(false)

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

  const loadVideos = async () => {
    setVideosLoading(true)
    try {
      const res: any = await request.get('/published/videos', { params: { limit: 50 } })
      setVideos(res?.items || [])
    } catch { /* ignore */ }
    setVideosLoading(false)
  }

  useEffect(() => { loadVideos() }, [])

  // 播放量 +1
  const handlePlay = async (v: any) => {
    window.open(v.video_url, '_blank')
    try {
      await request.post(`/published/${v.id}/view`)
      loadVideos()
    } catch { /* */ }
  }

  // 删除
  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/published/${id}`)
      message.success('已删除')
      loadVideos()
    } catch { message.error('删除失败') }
  }

  const cards = [
    { title: '素材总数', value: stats.materials, icon: <VideoCameraOutlined /> },
    { title: '剧本总数', value: stats.scripts, icon: <FileTextOutlined /> },
    { title: '视频任务', value: stats.tasks, icon: <ThunderboltOutlined /> },
  ]

  return (
    <Tabs
      defaultActiveKey="stats"
      items={[
        {
          key: 'stats',
          label: '工作台',
          children: (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                {cards.map((c, i) => (
                  <Col span={8} key={i}>
                    <Card>
                      {loading ? <Skeleton active paragraph={{ rows: 1 }} /> : <Statistic title={c.title} value={c.value} prefix={c.icon} />}
                    </Card>
                  </Col>
                ))}
              </Row>

              {/* 已生成视频 */}
              <Card title={<span><PlayCircleOutlined /> 已生成视频</span>} size="small" extra={
                <Button size="small" onClick={loadVideos}>刷新</Button>
              }>
                <Spin spinning={videosLoading}>
                  {videos.length === 0 ? (
                    <Empty description="暂无已生成视频，在工作流中完成字幕生成后点击「导出」" />
                  ) : (
                    <List
                      size="small"
                      dataSource={videos}
                      renderItem={(v: any) => (
                        <List.Item actions={[
                          <Button key="play" type="link" size="small" icon={<EyeOutlined />}
                            onClick={() => handlePlay(v)}>
                            {v.play_count || 0}
                          </Button>,
                          <Button key="del" type="link" size="small" danger icon={<DeleteOutlined />}
                            onClick={() => handleDelete(v.id)} />
                        ]}>
                          <List.Item.Meta
                            title={<span style={{ fontSize: 13 }}>{v.title}</span>}
                            description={
                              <div style={{ fontSize: 11, color: '#999' }}>
                                {v.style && <Tag color="green" style={{ fontSize: 10 }}>{v.style}</Tag>}
                                {v.hook_method && <Tag color="geekblue" style={{ fontSize: 10 }}>🎣 {v.hook_method}</Tag>}
                                {v.tags?.slice(0, 3).map((t: string, i: number) =>
                                  <Tag key={i} style={{ fontSize: 10 }}>{t}</Tag>
                                )}
                                <div style={{ marginTop: 2 }}>{new Date(v.created_at).toLocaleString('zh-CN')}</div>
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  )}
                </Spin>
              </Card>
            </>
          ),
        },
        {
          key: 'agent',
          label: <span><AppstoreOutlined /> 工作流</span>,
          children: <StudioPage />,
        },
      ]}
    />
  )
}
