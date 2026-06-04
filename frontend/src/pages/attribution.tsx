import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Tabs, Tag, Empty, Spin, Button, Typography, Progress } from 'antd'
import { ThunderboltOutlined, BarChartOutlined, RiseOutlined, NodeIndexOutlined, LinkOutlined, AppstoreOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import request from '../utils/request'

const { Title, Text } = Typography

const FEATURE_LABELS: Record<string, string> = {
  rhythm: '⚡ 节奏(秒)',
  hook_quality: '🎣 Hook质量',
  pacing_score: '⏱ 节奏评分',
  engagement_strength: '🔥 互动强度',
  cta_clarity: '🎯 CTA清晰度',
  overall_score: '⭐ 综合评分',
  bpm: '🎵 BPM',
  lightness_score: '🎵 轻快度',
  spectral_centroid: '🎵 频谱质心',
  zero_crossing_rate: '🎵 过零率',
  play_count: '📊 播放量',
}

export default function AttributionPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<any[]>([])
  const [result, setResult] = useState<any>(null)
  const [tab, setTab] = useState('data')
  const [selectedFeature, setSelectedFeature] = useState('lightness_score')

  // 加载数据
  const loadData = async () => {
    setLoading(true)
    try {
      const [dataRes, analyzeRes] = await Promise.all([
        request.get('/attribution/data'),
        request.post('/attribution/analyze', {}),
      ])
      setData((dataRes as any)?.items || (dataRes as any)?.data?.items || [])
      setResult(analyzeRes)
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { loadData() }, [])

  // 相关性颜色
  const corrColor = (v: number) => {
    if (v > 0.7) return '#52c41a'
    if (v > 0.4) return '#73d13d'
    if (v > 0.2) return '#bae637'
    if (v > -0.2) return '#f0f0f0'
    if (v > -0.4) return '#ffa39e'
    if (v > -0.7) return '#ff4d4f'
    return '#f5222d'
  }

  const numericCols = result?.numeric_features || []
  const allCols = [...numericCols, 'play_count']

  return (
    <div>
      {/* 头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>📊 多因子归因分析平台</Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            基于 {data.length} 个参考视频的 {numericCols.length} 个数值特征 × 播放量 分析
          </Text>
        </div>
        <Button type="primary" icon={<ThunderboltOutlined />} loading={loading} onClick={loadData}>
          重新分析
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="参考视频数" value={data.length} prefix={<PlayCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="数值特征数" value={numericCols.length} prefix={<BarChartOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="平均播放量" value={data.length ? Math.round(data.reduce((s, f) => s + (f.play_count || 0), 0) / data.length) : 0} prefix={<RiseOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable onClick={() => navigate('/reference')}>
            <Statistic title="查看参考视频" value="" prefix={<LinkOutlined />} suffix="→" />
          </Card>
        </Col>
      </Row>

      {/* 主内容区 */}
      <Card size="small" style={{ minHeight: 500 }}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            // ════ Tab 1: 数据探索 ════
            {
              key: 'data',
              label: <span><NodeIndexOutlined /> 数据探索</span>,
              children: (
                <Spin spinning={loading}>
                  {data.length === 0 ? (
                    <Empty description="暂无参考视频数据，先去上传参考视频" />
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ background: '#fafafa' }}>
                            <th style={thStyle}>#</th>
                            <th style={thStyle}>标题</th>
                            <th style={thStyle}>风格</th>
                            <th style={thStyle}>Hook</th>
                            {numericCols.map((c: string) => (
                              <th key={c} style={{ ...thStyle, cursor: 'pointer', color: c === selectedFeature ? '#1677ff' : undefined }}
                                onClick={() => setSelectedFeature(c)}>
                                {FEATURE_LABELS[c] || c}
                              </th>
                            ))}
                            <th style={{ ...thStyle, fontWeight: 700 }}>📊 播放量</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.map((f, i) => (
                            <tr key={f.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                              <td style={tdStyle}>{i + 1}</td>
                              <td style={tdStyle}>
                                <span style={{ cursor: 'pointer', color: '#1677ff' }}
                                  onClick={() => navigate(`/reference?id=${f.id}`)}>
                                  {f.title || `视频#${f.id}`}
                                </span>
                              </td>
                              <td style={tdStyle}><Tag style={{ fontSize: 10 }}>{f.style || '-'}</Tag></td>
                              <td style={tdStyle}><Text ellipsis style={{ maxWidth: 100, fontSize: 11 }}>{f.hook_method?.slice(0, 12) || '-'}</Text></td>
                              {numericCols.map((c: string) => {
                                const val = (f as any)[c]
                                const isNum = typeof val === 'number'
                                return (
                                  <td key={c} style={{
                                    ...tdStyle,
                                    background: c === selectedFeature && isNum ? `rgba(22,119,255,${Math.min((val || 0) / 100, 0.3)})` : undefined,
                                    fontWeight: c === selectedFeature ? 600 : undefined,
                                  }}>
                                    {isNum ? val.toFixed(1) : '-'}
                                  </td>
                                )
                              })}
                              <td style={{ ...tdStyle, fontWeight: 700 }}>{f.play_count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Spin>
              ),
            },

            // ════ Tab 2: 相关性矩阵 ════
            {
              key: 'correlation',
              label: <span><ThunderboltOutlined /> 相关性矩阵</span>,
              children: result ? (
                <div style={{ overflowX: 'auto' }}>
                  <div style={{ fontSize: 12, marginBottom: 8, color: '#666' }}>
                    Pearson 相关系数（-1 ~ 1），绿色=正相关，红色=负相关
                  </div>
                  <table style={{ borderCollapse: 'collapse', fontSize: 11 }}>
                    <thead>
                      <tr>
                        <th style={thStyle}></th>
                        {allCols.map(c => (
                          <th key={c} style={{ ...thStyle, writingMode: 'vertical-lr', height: 100, fontSize: 10 }}>{FEATURE_LABELS[c] || c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {allCols.map(c1 => (
                        <tr key={c1}>
                          <td style={{ ...thStyle, fontWeight: 600, textAlign: 'right', paddingRight: 8, whiteSpace: 'nowrap' }}>{FEATURE_LABELS[c1] || c1}</td>
                          {allCols.map(c2 => {
                            const v = result.correlation_matrix?.[c1]?.[c2] ?? 0
                            return (
                              <td key={c2} style={{
                                ...tdStyle,
                                background: corrColor(v),
                                color: Math.abs(v) > 0.4 ? '#fff' : '#333',
                                fontWeight: Math.abs(v) > 0.5 ? 700 : 400,
                                textAlign: 'center',
                                minWidth: 60,
                              }}>
                                {v ? v.toFixed(2) : '-'}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <Spin />,
            },

            // ════ Tab 3: 特征重要性 ════
            {
              key: 'importance',
              label: <span><RiseOutlined /> 特征重要性</span>,
              children: result ? (
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 16 }}>
                    基于 |Pearson相关系数| 归一化，越高表示该特征对播放量影响越大
                  </Text>
                  {result.feature_importance.map((item: any) => (
                    <div key={item.feature} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                        <span>{FEATURE_LABELS[item.feature] || item.feature}</span>
                        <span style={{ fontWeight: 600, color: '#1677ff' }}>{item.importance}%</span>
                      </div>
                      <Progress percent={item.importance} size="small" strokeColor={item.importance > 20 ? '#52c41a' : item.importance > 10 ? '#1677ff' : '#d9d9d9'} />
                    </div>
                  ))}
                </div>
              ) : <Spin />,
            },

            // ════ Tab 4: 回归分析 ════
            {
              key: 'regression',
              label: <span><BarChartOutlined /> 回归分析</span>,
              children: result ? (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong style={{ fontSize: 13 }}>选择特征：</Text>
                    <select value={selectedFeature} onChange={e => setSelectedFeature(e.target.value)}
                      style={{ marginLeft: 8, padding: '2px 8px', borderRadius: 4, border: '1px solid #d9d9d9' }}>
                      {result.regression?.map((r: any) => (
                        <option key={r.feature} value={r.feature}>{FEATURE_LABELS[r.feature] || r.feature}</option>
                      ))}
                    </select>
                  </div>
                  {(() => {
                    const reg = result.regression?.find((r: any) => r.feature === selectedFeature)
                    if (!reg) return <Text type="secondary">暂无数据</Text>
                    return (
                      <Row gutter={16}>
                        <Col span={8}>
                          <Card size="small" title="回归方程" style={{ fontSize: 12 }}>
                            <div>播放量 = {reg.slope > 0 ? '+' : ''}{reg.slope.toFixed(2)} × {FEATURE_LABELS[selectedFeature] || selectedFeature} {reg.intercept >= 0 ? '+ ' : '- '}{Math.abs(reg.intercept).toFixed(0)}</div>
                            <div style={{ marginTop: 8, color: '#666' }}>斜率: {reg.slope.toFixed(4)}</div>
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size="small" title="R² 决定系数" style={{ fontSize: 12 }}>
                            <Progress type="circle" percent={Math.round(reg.r2 * 100)} size={80} />
                            <div style={{ marginTop: 8, color: '#666' }}>
                              {reg.r2 > 0.5 ? '✅ 较强解释力' : reg.r2 > 0.2 ? '⚠️ 中等解释力' : '❌ 解释力弱'}
                            </div>
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size="small" title="相关性" style={{ fontSize: 12 }}>
                            <div style={{ fontSize: 24, fontWeight: 700, color: corrColor(reg.correlation) }}>{reg.correlation.toFixed(3)}</div>
                            <div style={{ marginTop: 8, color: '#666' }}>
                              {reg.correlation > 0 ? '📈 正相关' : '📉 负相关'}
                            </div>
                          </Card>
                        </Col>
                      </Row>
                    )
                  })()}
                </div>
              ) : <Spin />,
            },

            // ════ Tab 5: 最佳组合 ════
            {
              key: 'combos',
              label: <span><ThunderboltOutlined /> 最佳组合</span>,
              children: result ? (
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 16 }}>
                    风格×Hook×BGM×节奏 组合的平均播放量排名
                  </Text>
                  {result.best_combos?.length === 0 ? (
                    <Empty description="暂无足够数据" />
                  ) : (
                    <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: '#fafafa' }}>
                          <th style={thStyle}>#</th>
                          <th style={thStyle}>风格</th>
                          <th style={thStyle}>Hook</th>
                          <th style={thStyle}>BGM</th>
                          <th style={thStyle}>节奏</th>
                          <th style={thStyle}>样本数</th>
                          <th style={thStyle}>平均播放量</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.best_combos.map((c: any, i: number) => (
                          <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                            <td style={tdStyle}>{i + 1}</td>
                            <td style={tdStyle}><Tag color="green">{c.style || '-'}</Tag></td>
                            <td style={tdStyle}><Tag color="geekblue">{c.hook_method?.slice(0, 10) || '-'}</Tag></td>
                            <td style={tdStyle}><Tag color={c.bgm === '轻快' ? 'lime' : c.bgm === '稳重' ? 'purple' : 'default'}>{c.bgm}</Tag></td>
                            <td style={tdStyle}><Tag color="orange">{c.rhythm_tag}</Tag></td>
                            <td style={tdStyle}>{c.count}</td>
                            <td style={{ ...tdStyle, fontWeight: 700, fontSize: 14, color: '#1677ff' }}>{c.avg_play_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ) : <Spin />,
            },
          ]}
        />
      </Card>

      {/* 梦幻联动 */}
      <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
        <Button size="small" icon={<LinkOutlined />} onClick={() => navigate('/reference')}>
          去参考视频库
        </Button>
        <Button size="small" icon={<AppstoreOutlined />} onClick={() => navigate('/')}>
          去工作台
        </Button>
      </div>
    </div>
  )
}

const thStyle: React.CSSProperties = {
  padding: '6px 8px',
  border: '1px solid #f0f0f0',
  fontSize: 11,
  whiteSpace: 'nowrap',
  textAlign: 'center' as const,
}
const tdStyle: React.CSSProperties = {
  padding: '4px 8px',
  border: '1px solid #f0f0f0',
  fontSize: 11,
}
