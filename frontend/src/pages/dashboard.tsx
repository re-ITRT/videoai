import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Skeleton, Tabs, Tag, Empty, Spin, Button, message, Modal, Space, Typography, Divider, InputNumber } from 'antd'
import { VideoCameraOutlined, FileTextOutlined, ThunderboltOutlined, AppstoreOutlined, PlayCircleOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import request from '../utils/request'
import { getMaterials, getTasks } from '../utils/api'
import StudioPage from '../modules/studio/StudioPage'

const { Title, Text } = Typography

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ materials: 0, scripts: 0, tasks: 0 })
  const [videos, setVideos] = useState<any[]>([])
  const [videosLoading, setVideosLoading] = useState(false)

  // 详情弹窗
  const [detailVisible, setDetailVisible] = useState(false)
  const [detailVideo, setDetailVideo] = useState<any>(null)
  const [editingPlay, setEditingPlay] = useState(false)
  const [editPlayVal, setEditPlayVal] = useState(2000)

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

  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/published/${id}`)
      message.success('已删除')
      loadVideos()
    } catch { message.error('删除失败') }
  }

  const handlePlay = (v: any) => {
    window.open(v.video_url, '_blank')
    request.post(`/published/${v.id}/view`).catch(() => {})
  }

  const openDetail = (v: any) => {
    setDetailVideo(v)
    setEditPlayVal(v.play_count ?? 2000)
    setEditingPlay(false)
    setDetailVisible(true)
  }

  const savePlayCount = async (val: number) => {
    if (!detailVideo) return
    try {
      await request.put(`/published/${detailVideo.id}/play-count`, { play_count: val })
      setDetailVideo({ ...detailVideo, play_count: val })
      setEditingPlay(false)
      loadVideos()
    } catch { message.error('保存失败') }
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

              <Card title={<span><PlayCircleOutlined /> 已生成视频 ({videos.length})</span>} size="small" extra={
                <Button size="small" onClick={loadVideos}>刷新</Button>
              }>
                <Spin spinning={videosLoading}>
                  {videos.length === 0 ? (
                    <Empty description="暂无已生成视频，在工作流中完成字幕生成后点击「导出」" />
                  ) : (
                    <Row gutter={[12, 12]}>
                      {videos.map((v: any) => (
                        <Col xs={24} sm={12} md={8} lg={6} key={v.id}>
                          <Card
                            hoverable
                            size="small"
                            style={{ height: '100%' }}
                            cover={
                              <div style={{ position: 'relative', background: '#000', height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                                onClick={() => openDetail(v)}>
                                <video src={v.video_url} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                <PlayCircleOutlined style={{ position: 'absolute', fontSize: 40, color: 'rgba(255,255,255,0.8)' }} />
                              </div>
                            }
                            actions={[
                              <EyeOutlined key="play" onClick={() => handlePlay(v)} />,
                              <DeleteOutlined key="del" onClick={() => handleDelete(v.id)} />,
                            ]}
                          >
                            <Card.Meta
                              title={<span style={{ fontSize: 13 }}>{v.title}</span>}
                              description={
                                <div style={{ fontSize: 11, color: '#999' }}>
                                  {v.style && <Tag color="green" style={{ fontSize: 10 }}>{v.style}</Tag>}
                                  {v.hook_method && <Tag color="geekblue" style={{ fontSize: 10 }}>🎣 {v.hook_method}</Tag>}
                                </div>
                              }
                            />
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  )}
                </Spin>
              </Card>

              {/* 详情弹窗 */}
              <Modal title="视频详情" open={detailVisible} onCancel={() => setDetailVisible(false)} footer={null} width={700}>
                {detailVideo && (
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <Title level={4} style={{ margin: 0 }}>{detailVideo.title}</Title>
                    <Space>
                      {detailVideo.style && <Tag color="green">{detailVideo.style}</Tag>}
                      {detailVideo.hook_method && <Tag color="geekblue">🎣 {detailVideo.hook_method}</Tag>}
                    </Space>

                    {/* 播放量编辑 */}
                    <div style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <EyeOutlined /> 播放量：
                      {editingPlay ? (
                        <InputNumber size="small" min={0} value={editPlayVal}
                          onChange={(v) => setEditPlayVal(v || 0)}
                          onPressEnter={() => savePlayCount(editPlayVal)}
                          onBlur={() => savePlayCount(editPlayVal)}
                          autoFocus style={{ width: 80 }} />
                      ) : (
                        <span style={{ cursor: 'pointer', fontWeight: 600, color: '#1677ff' }}
                          onClick={() => { setEditPlayVal(detailVideo.play_count ?? 2000); setEditingPlay(true) }}>
                          {detailVideo.play_count ?? 2000}
                        </span>
                      )}
                    </div>

                    <Divider style={{ margin: '8px 0' }} />

                    {/* 视频播放器 */}
                    <video src={detailVideo.video_url} controls style={{ width: '100%', maxHeight: 400, background: '#000', borderRadius: 4 }} />

                    {detailVideo.analysis_report && Object.keys(detailVideo.analysis_report).length > 0 && (
                      <>
                        <Divider style={{ margin: '8px 0' }} />
                        <Text strong style={{ fontSize: 13 }}>分析报告</Text>
                        {Object.entries(detailVideo.analysis_report).filter(([k]) => !['run_id', 'tags', 'storyboard'].includes(k)).map(([key, val]: [string, any]) => {
                          const label: any = {
                            hook_quality: '📊 Hook质量', pacing_score: '⏱ 节奏评分',
                            engagement_strength: '🔥 互动强度', cta_clarity: '🎯 CTA清晰度',
                            improvement_suggestions: '💡 优化建议', overall_score: '⭐ 综合评分',
                            formula: '📐 公式',
                          }
                          return (
                            <div key={key} style={{ marginTop: 4, fontSize: 12 }}>
                              {typeof val === 'number' ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <span style={{ width: 80, flexShrink: 0 }}>{label[key] || key}</span>
                                  <div style={{ flex: 1, height: 8, background: '#f0f0f0', borderRadius: 4 }}>
                                    <div style={{ width: `${Math.min(val, 100)}%`, height: 8, background: val >= 70 ? '#52c41a' : val >= 40 ? '#faad14' : '#ff4d4f', borderRadius: 4 }} />
                                  </div>
                                  <span style={{ fontWeight: 600 }}>{val}</span>
                                </div>
                              ) : typeof val === 'string' ? (
                                <div>{label[key] || key}：{val}</div>
                              ) : null}
                            </div>
                          )
                        })}
                      </>
                    )}
                  </Space>
                )}
              </Modal>
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
