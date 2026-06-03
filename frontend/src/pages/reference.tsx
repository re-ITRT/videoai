/**
 * 优质视频库 - 带筛选的视频卡片列表页面
 */
import React, { useState, useEffect } from 'react';
import request from '../utils/request';
import {
  Card,
  Button,
  Input,
  Select,
  Space,
  Tag,
  Row,
  Col,
  Pagination,
  Modal,
  Spin,
  Empty,
  Typography,
  Divider,
} from 'antd';
import {
  PlayCircleOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlusOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// 类型定义
interface ReferenceVideo {
  id: number;
  user_id: string;
  source_platform?: string;
  source_url?: string;
  title?: string;
  category?: string;
  hook_method?: string;
  selling_points?: string[];
  storyboard?: any[];
  style?: string;
  analysis_report?: any;
  cover_url?: string;
  scenes?: any[];
  tags?: string[];
  created_at: string;
}

// 平台标签颜色映射
const platformColors: Record<string, string> = {
  FB: '#1877F2',
  INS: '#E4405F',
  TikTok: '#000000',
  custom: '#8c8c8c',
};

const ReferencePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [videos, setVideos] = useState<ReferenceVideo[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);

  // 筛选条件
  const [category, setCategory] = useState<string | undefined>();
  const [style, setStyle] = useState<string | undefined>();
  const [sourcePlatform, setSourcePlatform] = useState<string | undefined>();

  // 分析弹窗
  const [analyzeModalVisible, setAnalyzeModalVisible] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState('');
  const [analyzeTitle, setAnalyzeTitle] = useState('');
  const [analyzeCategory, setAnalyzeCategory] = useState('');
  const [analyzePlatform, setAnalyzePlatform] = useState('custom');

  // 详情弹窗
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<ReferenceVideo | null>(null);

  // 加载视频列表
  const loadVideos = async () => {
    setLoading(true);
    try {
      const data: any = await request.get('/reference/videos', {
        params: {
          category: category || undefined,
          style: style || undefined,
          source_platform: sourcePlatform || undefined,
          skip: (currentPage - 1) * pageSize,
          limit: pageSize,
        }
      });
      setVideos(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('加载视频列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVideos();
  }, [currentPage, pageSize, category, style, sourcePlatform]);

  // 上传并分析视频
  const handleAnalyze = async () => {
    if (!uploadFile && !sourceUrl) {
      Modal.error({ title: '请上传视频或填写视频链接' });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      if (uploadFile) formData.append('file', uploadFile);
      if (sourceUrl) formData.append('source_url', sourceUrl);
      formData.append('title', analyzeTitle);
      formData.append('category', analyzeCategory);
      formData.append('source_platform', analyzePlatform);

      const data: any = await request.post('/reference/upload-analyze', formData, { timeout: 300000 });
      if (data.success) {
        Modal.success({ title: '分析完成！' });
        setAnalyzeModalVisible(false);
        setUploadFile(null);
        setSourceUrl('');
        setAnalyzeTitle('');
        setAnalyzeCategory('');
        loadVideos();
      } else {
        Modal.error({ title: '分析失败', content: data.message });
      }
    } catch (error) {
      Modal.error({ title: '分析失败', content: String(error) });
    } finally {
      setLoading(false);
    }
  };

  // 删除视频
  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个参考视频吗？',
      onOk: async () => {
        try {
          await request.delete(`/reference/videos/${id}`);
          loadVideos();
        } catch (error) {
          console.error('删除失败:', error);
        }
      },
    });
  };

  // 查看详情
  const handleViewDetail = (video: ReferenceVideo) => {
    setSelectedVideo(video);
    setDetailModalVisible(true);
  };

  // 重置筛选
  const handleResetFilter = () => {
    setCategory(undefined);
    setStyle(undefined);
    setSourcePlatform(undefined);
    setCurrentPage(1);
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 头部 */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>
          优质视频库
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setAnalyzeModalVisible(true)}
        >
          分析视频
        </Button>
      </div>

      {/* 筛选栏 */}
      <Card style={{ marginBottom: '24px' }}>
        <Space wrap size="large">
          <Select
            placeholder="按分类筛选"
            style={{ width: 150 }}
            allowClear
            value={category}
            onChange={(v) => { setCategory(v); setCurrentPage(1); }}
          >
            <Option value="美妆">美妆</Option>
            <Option value="数码">数码</Option>
            <Option value="食品">食品</Option>
            <Option value="服饰">服饰</Option>
            <Option value="家居">家居</Option>
          </Select>

          <Select
            placeholder="按风格筛选"
            style={{ width: 150 }}
            allowClear
            value={style}
            onChange={(v) => { setStyle(v); setCurrentPage(1); }}
          >
            <Option value="口播">口播</Option>
            <Option value="测评">测评</Option>
            <Option value="剧情">剧情</Option>
            <Option value="展示">展示</Option>
            <Option value="教程">教程</Option>
          </Select>

          <Select
            placeholder="按平台筛选"
            style={{ width: 150 }}
            allowClear
            value={sourcePlatform}
            onChange={(v) => { setSourcePlatform(v); setCurrentPage(1); }}
          >
            <Option value="FB">Facebook</Option>
            <Option value="INS">Instagram</Option>
            <Option value="TikTok">TikTok</Option>
            <Option value="custom">其他</Option>
          </Select>

          <Button onClick={handleResetFilter}>重置筛选</Button>
        </Space>
      </Card>

      {/* 视频列表 */}
      <Spin spinning={loading}>
        {videos.length === 0 && !loading ? (
          <Empty description="暂无视频，点击右上角按钮添加第一个优质视频" />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {videos.map((video) => (
                <Col xs={24} sm={12} md={8} lg={6} key={video.id}>
                  <Card
                    hoverable
                    cover={
                      video.cover_url ? (
                        <img src={video.cover_url} alt={video.title}
                          style={{ height: '160px', width: '100%', objectFit: 'cover', cursor: 'pointer' }}
                          onClick={() => window.open(video.source_url, '_blank')} />
                      ) : (
                        <div
                          style={{
                            height: '160px',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontSize: '48px',
                            cursor: 'pointer',
                          }}
                          onClick={() => window.open(video.source_url, '_blank')}
                        >
                          <PlayCircleOutlined />
                        </div>
                      )
                    }
                    actions={[
                      <EyeOutlined key="view" onClick={() => handleViewDetail(video)} />,
                      <DeleteOutlined key="delete" onClick={() => handleDelete(video.id)} />,
                    ]}
                  >
                    <Card.Meta
                      title={video.title || '未命名视频'}
                      description={
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <Space wrap>
                            {video.source_platform && (
                              <Tag color={platformColors[video.source_platform] || 'default'}>
                                {video.source_platform}
                              </Tag>
                            )}
                            {video.category && <Tag color="blue">{video.category}</Tag>}
                            {video.style && <Tag color="green">{video.style}</Tag>}
                          </Space>
                          {video.hook_method && (
                            <Text type="secondary" ellipsis>
                              Hook: {video.hook_method}
                            </Text>
                          )}
                        </Space>
                      }
                    />
                  </Card>
                </Col>
              ))}
            </Row>

            {/* 分页 */}
            <div style={{ marginTop: '24px', textAlign: 'right' }}>
              <Pagination
                current={currentPage}
                pageSize={pageSize}
                total={total}
                onChange={(page, size) => {
                  setCurrentPage(page);
                  if (size) setPageSize(size);
                }}
                showSizeChanger
                showQuickJumper
                showTotal={(total) => `共 ${total} 个视频`}
              />
            </div>
          </>
        )}
      </Spin>

      {/* 上传分析弹窗 */}
      <Modal
        title="上传视频分析"
        open={analyzeModalVisible}
        onOk={handleAnalyze}
        onCancel={() => setAnalyzeModalVisible(false)}
        width={500}
        confirmLoading={loading}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <input type="file" accept="video/*" onChange={e => setUploadFile(e.target.files?.[0] || null)} />
            {uploadFile && <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>已选择: {uploadFile.name}</div>}
          </div>
          <div>
            <Text strong>或输入视频链接</Text>
            <Input placeholder="https://example.com/video.mp4" value={sourceUrl}
              onChange={e => setSourceUrl(e.target.value)} />
          </div>
          <div>
            <Text strong>视频标题</Text>
            <Input
              placeholder="输入视频标题"
              value={analyzeTitle}
              onChange={(e) => setAnalyzeTitle(e.target.value)}
            />
          </div>
          <div>
            <Text strong>分类</Text>
            <Select
              placeholder="选择分类"
              style={{ width: '100%' }}
              value={analyzeCategory}
              onChange={setAnalyzeCategory}
            >
              <Option value="美妆">美妆</Option>
              <Option value="数码">数码</Option>
              <Option value="食品">食品</Option>
              <Option value="服饰">服饰</Option>
              <Option value="家居">家居</Option>
            </Select>
          </div>
          <div>
            <Text strong>来源平台</Text>
            <Select
              placeholder="选择平台"
              style={{ width: '100%' }}
              value={analyzePlatform}
              onChange={setAnalyzePlatform}
            >
              <Option value="FB">Facebook</Option>
              <Option value="INS">Instagram</Option>
              <Option value="TikTok">TikTok</Option>
              <Option value="custom">其他</Option>
            </Select>
          </div>
          <Paragraph type="secondary">
            上传后系统将调用 video-analyze 工作流分析视频，提取 Hook 手法、卖点、风格等结构化数据并保存。
          </Paragraph>
        </Space>
      </Modal>

      {/* 详情弹窗 */}
      <Modal
        title="视频详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedVideo && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Title level={4}>{selectedVideo.title || '未命名视频'}</Title>
              <Space wrap>
                {selectedVideo.source_platform && (
                  <Tag color={platformColors[selectedVideo.source_platform] || 'default'}>
                    {selectedVideo.source_platform}
                  </Tag>
                )}
                {selectedVideo.category && <Tag color="blue">{selectedVideo.category}</Tag>}
                {selectedVideo.style && <Tag color="green">{selectedVideo.style}</Tag>}
              </Space>
            </div>

            {selectedVideo.source_url && (
              <div>
                <Text strong>来源链接：</Text>
                <a href={selectedVideo.source_url} target="_blank" rel="noopener noreferrer">
                  {selectedVideo.source_url}
                </a>
              </div>
            )}

            <Divider />

            {selectedVideo.scenes && selectedVideo.scenes.length > 0 && (
              <div>
                <Text strong>🎬 分镜分析（{selectedVideo.scenes.length} 个场景）</Text>
                {selectedVideo.scenes.map((scene: any, i: number) => (
                  <div key={i} style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4 }}>
                    <Text strong>场景 {scene.scene_id}</Text>
                    <div style={{ fontSize: 12, color: '#666' }}>时间: {scene.time_range}</div>
                    <div style={{ fontSize: 12, marginTop: 2 }}>{scene.description}</div>
                    {scene.script && <div style={{ fontSize: 12, color: '#1677ff', marginTop: 2 }}>🎙 {scene.script}</div>}
                    {scene.embedding && <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>embedding: {scene.embedding.length}维</div>}
                  </div>
                ))}
              </div>
            )}

            {selectedVideo.tags && selectedVideo.tags.length > 0 && (
              <div>
                <Text strong>标签：</Text>
                <Space wrap style={{ marginTop: 4 }}>
                  {selectedVideo.tags.map((t: string, i: number) => <Tag key={i}>{t}</Tag>)}
                </Space>
              </div>
            )}

            {selectedVideo.style && (
              <div>
                <Text strong>风格：</Text>
                <Tag color="green">{selectedVideo.style}</Tag>
              </div>
            )}

            {selectedVideo.hook_method && (
              <div>
                <Text strong>Hook手法：</Text>
                <Paragraph style={{ margin: 0 }}>{selectedVideo.hook_method}</Paragraph>
              </div>
            )}

            {selectedVideo.selling_points && selectedVideo.selling_points.length > 0 && (
              <div>
                <Text strong>核心卖点：</Text>
                <ul style={{ margin: 0 }}>
                  {selectedVideo.selling_points.map((p: string, i: number) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* analysis_report 逐字段渲染（不含和顶层重复的 storyboard） */}
            {selectedVideo.analysis_report && Object.keys(selectedVideo.analysis_report).length > 0 && (
              <div>
                <Text strong>分析报告</Text>
                {Object.entries(selectedVideo.analysis_report).filter(([k]) => !['run_id', 'analysis_report'].includes(k)).map(([key, val]: [string, any]) => (
                  <div key={key} style={{ marginTop: 8 }}>
                    <Text strong style={{ fontSize: 13 }}>{{
                      hook_quality: '📊 Hook质量',
                      pacing_score: '⏱ 节奏评分',
                      engagement_strength: '🔥 互动强度',
                      cta_clarity: '🎯 CTA清晰度',
                      improvement_suggestions: '💡 优化建议',
                      overall_score: '⭐ 综合评分',
                      tags: '🏷 分析标签',
                      style: '🎨 风格',
                      rhythm: '🎵 节奏',
                      formula: '📐 公式',
                    }[key] || key}：</Text>
                    {Array.isArray(val) ? (
                      val.length > 0 && typeof val[0] === 'object' && val[0].visual ? (
                        <div style={{ maxHeight: 300, overflow: 'auto' }}>
                          {val.map((s: any, i: number) => (
                            <div key={i} style={{ background: '#f8f8f8', padding: 6, borderRadius: 4, marginTop: 4, fontSize: 12 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                                <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>{s.type || '场景'}</Tag>
                                <span style={{ color: '#999' }}>{s.time_range}</span>
                              </div>
                              <div style={{ color: '#333' }}>{s.visual}</div>
                              {s.narration && <div style={{ color: '#1677ff', marginTop: 2 }}>🎙 {s.narration}</div>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <ul style={{ margin: 0, paddingLeft: 20 }}>
                          {val.map((v: any, i: number) => <li key={i} style={{ fontSize: 12 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</li>)}
                        </ul>
                      )
                    ) : typeof val === 'number' ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                        <div style={{ flex: 1, height: 8, background: '#f0f0f0', borderRadius: 4 }}>
                          <div style={{ width: `${Math.min(val, 100)}%`, height: 8, background: val >= 70 ? '#52c41a' : val >= 40 ? '#faad14' : '#ff4d4f', borderRadius: 4 }} />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 600 }}>{val}</span>
                      </div>
                    ) : typeof val === 'object' && !Array.isArray(val) ? (
                      <Paragraph style={{ margin: 0, fontSize: 12 }}>{JSON.stringify(val)}</Paragraph>
                    ) : (
                      <Paragraph style={{ margin: 0, fontSize: 12 }}>{String(val)}</Paragraph>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default ReferencePage;
