import { useState, useEffect, useRef } from 'react'
import { Spin } from 'antd'
import request from '../../utils/request'

function VideoProxy({ url }: { url: string }) {
  const [proxySrc, setProxySrc] = useState('')
  useEffect(() => {
    if (!url) return
    const idx = url.indexOf('/uploads/')
    const path = idx >= 0 ? url.substring(idx) : url
    setProxySrc(`/api/v1/studio/video-proxy?path=${encodeURIComponent(path)}`)
  }, [url])
  if (!proxySrc) return <div style={{ width: '100%', height: '100%', background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#ccc' }}>加载中</div>
  return <video src={proxySrc} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
}
import { Card, Row, Col, Statistic, Skeleton, Tabs, Tag, Empty, Spin, Button, message, Modal, Space, Typography, Divider, Descriptions } from 'antd'
import { VideoCameraOutlined, FileTextOutlined, ThunderboltOutlined, AppstoreOutlined, PlayCircleOutlined, EyeOutlined, DeleteOutlined, RiseOutlined } from '@ant-design/icons'
import request from '../utils/request'
import { getMaterials, getTasks } from '../utils/api'
import StudioPage from '../modules/studio/StudioPage'

const { Title, Text } = Typography

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ materials: 0, scripts: 0, tasks: 0 })
  const [videos, setVideos] = useState<any[]>([])
  const [videosLoading, setVideosLoading] = useState(false)

  const [detailVisible, setDetailVisible] = useState(false)
  const [detailVideo, setDetailVideo] = useState<any>(null)
  const [audioModalVisible, setAudioModalVisible] = useState(false)
  const [audioData, setAudioData] = useState<any>(null)

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
      const items = (res?.items || []).map((v: any) => ({ ...v, _video_url: v.video_url }))
      setVideos(items)
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

  const openDetail = (v: any) => {
    setDetailVideo(v)
    setDetailVisible(true)
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
                                onClick={async () => { try { const sr: any = await request.post('/studio/sign-url', { path: v._video_url || v.video_url }); window.open(sr?.url || v.video_url, '_blank') } catch { window.open(v.video_url, '_blank') } }}>
                                <VideoProxy url={v._video_url || v.video_url} />
                                <PlayCircleOutlined style={{ position: 'absolute', fontSize: 40, color: 'rgba(255,255,255,0.8)' }} />
                              </div>
                            }
            actions={[
              <EyeOutlined key="play" onClick={() => openDetail(v)} />,
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

              <Modal title="视频详情" open={detailVisible} onCancel={() => setDetailVisible(false)} footer={null} width={800}>
                {detailVideo && (
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <div>
                      <Title level={4} style={{ margin: 0 }}>{detailVideo.title || '未命名视频'}</Title>
                      <Space wrap style={{ marginTop: 4 }}>
                        {detailVideo.style && <Tag color="green">{detailVideo.style}</Tag>}
                        {detailVideo.rhythm ? <Tag color="orange">{detailVideo.rhythm <= 2 ? '⚡快' : detailVideo.rhythm <= 5 ? '~中' : '🐢慢'}</Tag> : null}
                      </Space>
                      {detailVideo.tags && detailVideo.tags.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          <Space wrap size={[4, 4]}>
                            {detailVideo.tags.map((t: string, i: number) => <Tag key={i}>{t}</Tag>)}
                          </Space>
                        </div>
                      )}
                      {/* 播放量（回归预测） */}
                      <div style={{ marginTop: 6, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <RiseOutlined /> 预测播放量：
                        <span style={{ fontWeight: 700, fontSize: 16, color: '#1677ff' }}>
                          {detailVideo.predicted_play_count?.toLocaleString() ?? '计算中...'}
                        </span>
                        <Tag color="blue" style={{ fontSize: 10 }}>AI预测</Tag>
                      </div>
                      {/* 剧本模板信息 */}
                      {detailVideo.script_template && (
                        <div style={{ marginTop: 4, fontSize: 12 }}>
                          <FileTextOutlined /> 使用模板：<Tag color="cyan">{detailVideo.script_template}</Tag>
                        </div>
                      )}
                    </div>

                    {detailVideo.hook_method && (
                      <Tag color="geekblue" style={{ fontSize: 12 }}>🎣 {detailVideo.hook_method}</Tag>
                    )}

                    {detailVideo.selling_points && detailVideo.selling_points.length > 0 && (
                      <Space wrap size={[4, 4]}>
                        {detailVideo.selling_points.map((p: string, i: number) => (
                          <Tag key={i} color="volcano">{p}</Tag>
                        ))}
                      </Space>
                    )}

                    {detailVideo.video_url && (
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>来源：</Text>
                        <a href={detailVideo.video_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12 }}>{detailVideo.video_url}</a>
                      </div>
                    )}

                    <Divider style={{ margin: '8px 0' }} />

                    {detailVideo.scenes && detailVideo.scenes.length > 0 && (
                      <div>
                        <Text strong style={{ fontSize: 13 }}>🎬 分镜（{detailVideo.scenes.length} 景）</Text>
                        {detailVideo.scenes.map((scene: any, i: number) => (
                          <div key={i} style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4, fontSize: 12 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                              <Tag color="default" style={{ fontSize: 10, margin: 0 }}>#{(i+1).toString().padStart(2,'0')}</Tag>
                              <span style={{ color: '#666' }}>{scene.time_range}</span>
                              {scene.script && <span style={{ color: '#1677ff' }}>🎙 {scene.script}</span>}
                            </div>
                            <div style={{ color: '#333' }}>{scene.description}</div>
                          </div>
                        ))}
                      </div>
                    )}
                    {/* fallback: 从 analysis_report.storyboard 渲染 */}
                    {(!detailVideo.scenes || detailVideo.scenes.length === 0) && detailVideo.analysis_report?.storyboard?.length > 0 && (
                      <div>
                        <Text strong style={{ fontSize: 13 }}>🎬 分镜（{detailVideo.analysis_report.storyboard.length} 景）</Text>
                        {detailVideo.analysis_report.storyboard.map((s: any, i: number) => (
                          <div key={i} style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4, fontSize: 12 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                              <Tag color="default" style={{ fontSize: 10, margin: 0 }}>#{(i+1).toString().padStart(2,'0')}</Tag>
                              <span style={{ color: '#666' }}>{s.time_range}</span>
                              {s.narration && <span style={{ color: '#1677ff' }}>🎙 {s.narration}</span>}
                            </div>
                            <div style={{ color: '#333' }}>{s.visual}</div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* analysis_report */}
                    {detailVideo.analysis_report && Object.keys(detailVideo.analysis_report).length > 0 && (
                      <div>
                        <Text strong style={{ fontSize: 13 }}>分析报告</Text>
                        {Object.entries(detailVideo.analysis_report).filter(([k]) => !['run_id', 'analysis_report', 'rhythm', 'tags', 'hook_method', 'selling_points', 'storyboard'].includes(k)).map(([key, val]: [string, any]) => {
                          const label = ({
                            hook_quality: '📊 Hook质量',
                            pacing_score: '⏱ 节奏评分',
                            engagement_strength: '🔥 互动强度',
                            cta_clarity: '🎯 CTA清晰度',
                            improvement_suggestions: '💡 优化建议',
                            overall_score: '⭐ 综合评分',
                            formula: '📐 公式',
                            style: '🎨 风格',
                          } as any)[key];
                          if (!label) return null;
                          return (
                            <div key={key} style={{ marginTop: 6 }}>
                              {typeof val === 'number' ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                                  <span style={{ width: 80, flexShrink: 0 }}>{label}</span>
                                  <div style={{ flex: 1, height: 8, background: '#f0f0f0', borderRadius: 4 }}>
                                    <div style={{ width: `${Math.min(val, 100)}%`, height: 8, background: val >= 70 ? '#52c41a' : val >= 40 ? '#faad14' : '#ff4d4f', borderRadius: 4 }} />
                                  </div>
                                  <span style={{ fontWeight: 600 }}>{val}</span>
                                </div>
                              ) : typeof val === 'string' && key === 'formula' ? (
                                <Tag color="purple">{label.replace(/^[^\s]+\s/, '')}: {val}</Tag>
                              ) : typeof val === 'string' && key === 'improvement_suggestions' ? (
                                <div style={{ fontSize: 12, marginTop: 2 }}>{val}</div>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* 🎵 BGM 分析 */}
                    {detailVideo.audio_features?.bpm && (
                      <div style={{ marginTop: 8 }}>
                        <Button size="small" type="default"
                          onClick={() => {
                            setAudioData(detailVideo.audio_features)
                            setAudioModalVisible(true)
                          }}>
                          🎵 BGM 分析
                        </Button>
                      </div>
                    )}
                  </Space>
                )}
              </Modal>

              {/* 音频分析弹窗 */}
              <Modal title="🎵 BGM 音频特征分析" open={audioModalVisible} onCancel={() => setAudioModalVisible(false)} footer={null} width={600}>
                {audioData && (
                  <Descriptions column={2} bordered size="small">
                    <Descriptions.Item label="🎵 风格" span={2}>
                      <Tag color={audioData.mood === '轻快' ? 'green' : audioData.mood === '稳重' ? 'purple' : 'orange'}>
                        {audioData.mood === '轻快' ? '⚡ 轻快' : audioData.mood === '稳重' ? '🐢 稳重' : '➡ 中性'}
                      </Tag>
                      <Tag>轻快度: {audioData.lightness_score}/100</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="BPM"><Tag color="blue">{audioData.bpm}</Tag></Descriptions.Item>
                    <Descriptions.Item label="时长">{audioData.duration}s</Descriptions.Item>
                    <Descriptions.Item label="频谱质心">{audioData.spectral_centroid} Hz</Descriptions.Item>
                    <Descriptions.Item label="过零率">{audioData.zero_crossing_rate}</Descriptions.Item>
                    <Descriptions.Item label="频谱滚降点">{audioData.spectral_rolloff} Hz</Descriptions.Item>
                    <Descriptions.Item label="BPM得分">{audioData.features?.bpm_score}</Descriptions.Item>
                    <Descriptions.Item label="质心得分">{audioData.features?.centroid_score}</Descriptions.Item>
                    <Descriptions.Item label="过零率得分">{audioData.features?.zcr_score}</Descriptions.Item>
                    {audioData.mfcc_mean && (
                      <Descriptions.Item label="MFCC(13维)" span={2}>
                        <div style={{ fontSize: 11, color: '#666', wordBreak: 'break-all' }}>{audioData.mfcc_mean.join(', ')}</div>
                      </Descriptions.Item>
                    )}
                  </Descriptions>
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
