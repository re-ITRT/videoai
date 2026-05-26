/**
 * 灵感模板库页面 - 点击模板可以直接生成剧本
 */
import React, { useState, useEffect } from 'react';
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
  Tabs,
  Form,
  List,
  Avatar,
} from 'antd';
import {
  FileTextOutlined,
  ThunderboltOutlined,
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  EditOutlined,
  RocketOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

// 类型定义
interface InspirationTemplate {
  id: number;
  user_id: string;
  name: string;
  strategy: string;
  factors: Record<string, any>;
  reference_video_ids: number[];
  category?: string;
  tags: string[];
  created_at: string;
}

interface StrategyFactor {
  id: number;
  user_id: string;
  name: string;
  factor_type: string;
  description?: string;
  content: Record<string, any>;
  category?: string;
  tags: string[];
  usage_count: number;
  created_at: string;
}

const TemplatesPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<InspirationTemplate[]>([]);
  const [factors, setFactors] = useState<StrategyFactor[]>([]);
  const [totalTemplates, setTotalTemplates] = useState(0);
  const [totalFactors, setTotalFactors] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);

  // 筛选条件
  const [templateCategory, setTemplateCategory] = useState<string>();
  const [factorType, setFactorType] = useState<string>();
  const [factorCategory, setFactorCategory] = useState<string>();

  // 弹窗状态
  const [templateModalVisible, setTemplateModalVisible] = useState(false);
  const [factorModalVisible, setFactorModalVisible] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<InspirationTemplate | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<InspirationTemplate | null>(null);
  const [editingFactor, setEditingFactor] = useState<StrategyFactor | null>(null);

  const [templateForm] = Form.useForm();
  const [factorForm] = Form.useForm();
  const [generateForm] = Form.useForm();

  // 加载模板列表
  const loadTemplates = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (templateCategory) params.append('category', templateCategory);
      params.append('skip', String((currentPage - 1) * pageSize));
      params.append('limit', String(pageSize));

      const response = await fetch(`/api/v1/template/templates?${params}`);
      const data = await response.json();
      setTemplates(data.items || []);
      setTotalTemplates(data.total || 0);
    } catch (error) {
      console.error('加载模板失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载因子列表
  const loadFactors = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (factorType) params.append('factor_type', factorType);
      if (factorCategory) params.append('category', factorCategory);
      params.append('skip', String((currentPage - 1) * pageSize));
      params.append('limit', String(pageSize));

      const response = await fetch(`/api/v1/template/factors?${params}`);
      const data = await response.json();
      setFactors(data.items || []);
      setTotalFactors(data.total || 0);
    } catch (error) {
      console.error('加载因子失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, [currentPage, pageSize, templateCategory]);

  // 颜色映射
  const categoryColors: Record<string, string> = {
    美妆: 'pink',
    数码: 'blue',
    食品: 'orange',
    服饰: 'purple',
    家居: 'green',
  };

  const factorTypeColors: Record<string, string> = {
    hook: 'red',
    scene: 'blue',
    narration: 'cyan',
    visual: 'purple',
    ending: 'green',
  };

  const factorTypeLabels: Record<string, string> = {
    hook: 'Hook开场',
    scene: '场景构建',
    narration: '旁白话术',
    visual: '视觉呈现',
    ending: '结尾引导',
  };

  // 提交模板
  const handleSubmitTemplate = async (values: any) => {
    setLoading(true);
    try {
      const url = editingTemplate
        ? `/api/v1/template/templates/${editingTemplate.id}`
        : '/api/v1/template/templates';
      const method = editingTemplate ? 'PUT' : 'POST';

      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });

      setTemplateModalVisible(false);
      templateForm.resetFields();
      setEditingTemplate(null);
      loadTemplates();
    } catch (error) {
      console.error('保存模板失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 提交因子
  const handleSubmitFactor = async (values: any) => {
    setLoading(true);
    try {
      // 解析 JSON 字段
      const data = {
        ...values,
        content: values.content ? JSON.parse(values.content) : {},
        tags: values.tags ? values.tags.split(',').map((t: string) => t.trim()) : [],
      };

      const url = editingFactor
        ? `/api/v1/template/factors/${editingFactor.id}`
        : '/api/v1/template/factors';
      const method = editingFactor ? 'PUT' : 'POST';

      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      setFactorModalVisible(false);
      factorForm.resetFields();
      setEditingFactor(null);
      loadFactors();
    } catch (error) {
      console.error('保存因子失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 删除模板
  const handleDeleteTemplate = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个模板吗？',
      onOk: async () => {
        await fetch(`/api/v1/template/templates/${id}`, { method: 'DELETE' });
        loadTemplates();
      },
    });
  };

  // 删除因子
  const handleDeleteFactor = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个策略因子吗？',
      onOk: async () => {
        await fetch(`/api/v1/template/factors/${id}`, { method: 'DELETE' });
        loadFactors();
      },
    });
  };

  // 使用模板生成剧本
  const handleGenerateScript = async (values: any) => {
    if (!selectedTemplate) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/v1/template/templates/${selectedTemplate.id}/generate-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: selectedTemplate.id,
          product_info: values.product_info ? JSON.parse(values.product_info) : {},
        }),
      });

      const result = await response.json();
      if (result.success) {
        Modal.success({
          title: '剧本生成成功！',
          content: (
            <div>
              <Paragraph>使用模板：{selectedTemplate.name}</Paragraph>
              <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
                {JSON.stringify(result.script, null, 2)}
              </pre>
            </div>
          ),
          width: 700,
        });
        setGenerateModalVisible(false);
        generateForm.resetFields();
      }
    } catch (error) {
      Modal.error({ title: '生成失败', content: String(error) });
    } finally {
      setLoading(false);
    }
  };

  // 打开生成弹窗
  const openGenerateModal = (template: InspirationTemplate) => {
    setSelectedTemplate(template);
    setGenerateModalVisible(true);
  };

  // 打开编辑弹窗
  const openEditTemplate = (template: InspirationTemplate) => {
    setEditingTemplate(template);
    templateForm.setFieldsValue({
      name: template.name,
      strategy: template.strategy,
      category: template.category,
      tags: template.tags?.join(', ') || '',
      factors: JSON.stringify(template.factors, null, 2),
      reference_video_ids: template.reference_video_ids?.join(', ') || '',
    });
    setTemplateModalVisible(true);
  };

  const openEditFactor = (factor: StrategyFactor) => {
    setEditingFactor(factor);
    factorForm.setFieldsValue({
      name: factor.name,
      factor_type: factor.factor_type,
      description: factor.description,
      category: factor.category,
      tags: factor.tags?.join(', ') || '',
      content: JSON.stringify(factor.content, null, 2),
    });
    setFactorModalVisible(true);
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 头部 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={3} style={{ margin: 0 }}>
          灵感模板库
        </Title>
        <Text type="secondary">选择模板一键生成剧本，积累你的爆款创作策略</Text>
      </div>

      <Tabs defaultActiveKey="templates">
        {/* 模板库 Tab */}
        <TabPane tab={<span><FileTextOutlined /> 灵感模板</span>} key="templates">
          {/* 筛选栏 */}
          <Card style={{ marginBottom: '24px' }}>
            <Space wrap size="large">
              <Select
                placeholder="按分类筛选"
                style={{ width: 150 }}
                allowClear
                value={templateCategory}
                onChange={(v) => { setTemplateCategory(v); setCurrentPage(1); }}
              >
                <Option value="美妆">美妆</Option>
                <Option value="数码">数码</Option>
                <Option value="食品">食品</Option>
                <Option value="服饰">服饰</Option>
                <Option value="家居">家居</Option>
              </Select>

              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingTemplate(null);
                  templateForm.resetFields();
                  setTemplateModalVisible(true);
                }}
              >
                新建模板
              </Button>
            </Space>
          </Card>

          {/* 模板卡片列表 */}
          <Spin spinning={loading}>
            {templates.length === 0 && !loading ? (
              <Empty description="暂无模板，点击新建模板创建第一个" />
            ) : (
              <>
                <Row gutter={[16, 16]}>
                  {templates.map((template) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={template.id}>
                      <Card
                        hoverable
                        actions={[
                          <EyeOutlined key="view" onClick={() => openEditTemplate(template)} />,
                          <RocketOutlined key="generate" onClick={() => openGenerateModal(template)} style={{ color: '#1890ff' }} />,
                          <DeleteOutlined key="delete" onClick={() => handleDeleteTemplate(template.id)} />,
                        ]}
                      >
                        <Card.Meta
                          avatar={<Avatar icon={<FileTextOutlined />} />}
                          title={template.name}
                          description={
                            <Space direction="vertical" size="small" style={{ width: '100%', marginTop: '8px' }}>
                              <Text ellipsis style={{ maxWidth: '100%' }}>
                                {template.strategy}
                              </Text>
                              <Space wrap>
                                {template.category && (
                                  <Tag color={categoryColors[template.category] || 'default'}>
                                    {template.category}
                                  </Tag>
                                )}
                                {Object.keys(template.factors || {}).length > 0 && (
                                  <Tag color="blue">{Object.keys(template.factors).length} 个因子</Tag>
                                )}
                              </Space>
                            </Space>
                          }
                        />
                      </Card>
                    </Col>
                  ))}
                </Row>

                <div style={{ marginTop: '24px', textAlign: 'right' }}>
                  <Pagination
                    current={currentPage}
                    pageSize={pageSize}
                    total={totalTemplates}
                    onChange={(page, size) => {
                      setCurrentPage(page);
                      if (size) setPageSize(size);
                    }}
                    showSizeChanger
                    showQuickJumper
                    showTotal={(total) => `共 ${total} 个模板`}
                  />
                </div>
              </>
            )}
          </Spin>
        </TabPane>

        {/* 策略因子 Tab */}
        <TabPane tab={<span><ThunderboltOutlined /> 策略因子</span>} key="factors">
          {/* 筛选栏 */}
          <Card style={{ marginBottom: '24px' }}>
            <Space wrap size="large">
              <Select
                placeholder="按因子类型筛选"
                style={{ width: 150 }}
                allowClear
                value={factorType}
                onChange={(v) => { setFactorType(v); setCurrentPage(1); }}
              >
                <Option value="hook">Hook开场</Option>
                <Option value="scene">场景构建</Option>
                <Option value="narration">旁白话术</Option>
                <Option value="visual">视觉呈现</Option>
                <Option value="ending">结尾引导</Option>
              </Select>

              <Select
                placeholder="按分类筛选"
                style={{ width: 150 }}
                allowClear
                value={factorCategory}
                onChange={(v) => { setFactorCategory(v); setCurrentPage(1); }}
              >
                <Option value="美妆">美妆</Option>
                <Option value="数码">数码</Option>
                <Option value="食品">食品</Option>
                <Option value="服饰">服饰</Option>
                <Option value="家居">家居</Option>
              </Select>

              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingFactor(null);
                  factorForm.resetFields();
                  setFactorModalVisible(true);
                }}
              >
                新建因子
              </Button>
            </Space>
          </Card>

          {/* 因子列表 */}
          <Spin spinning={loading}>
            {factors.length === 0 && !loading ? (
              <Empty description="暂无因子，点击新建因子创建第一个" />
            ) : (
              <>
                <List
                  grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
                  dataSource={factors}
                  renderItem={(factor) => (
                    <List.Item>
                      <Card
                        hoverable
                        size="small"
                        actions={[
                          <EditOutlined key="edit" onClick={() => openEditFactor(factor)} />,
                          <DeleteOutlined key="delete" onClick={() => handleDeleteFactor(factor.id)} />,
                        ]}
                      >
                        <Card.Meta
                          title={
                            <Space>
                              {factor.name}
                              <Tag color={factorTypeColors[factor.factor_type] || 'default'}>
                                {factorTypeLabels[factor.factor_type] || factor.factor_type}
                              </Tag>
                            </Space>
                          }
                          description={
                            <Space direction="vertical" size="small" style={{ width: '100%', marginTop: '8px' }}>
                              <Text type="secondary" ellipsis>
                                {factor.description || '暂无描述'}
                              </Text>
                              <Space wrap>
                                {factor.category && (
                                  <Tag color={categoryColors[factor.category] || 'default'}>
                                    {factor.category}
                                  </Tag>
                                )}
                                <Tag color="green">使用 {factor.usage_count} 次</Tag>
                              </Space>
                            </Space>
                          }
                        />
                      </Card>
                    </List.Item>
                  )}
                />

                <div style={{ marginTop: '24px', textAlign: 'right' }}>
                  <Pagination
                    current={currentPage}
                    pageSize={pageSize}
                    total={totalFactors}
                    onChange={(page, size) => {
                      setCurrentPage(page);
                      if (size) setPageSize(size);
                    }}
                    showSizeChanger
                    showQuickJumper
                    showTotal={(total) => `共 ${total} 个因子`}
                  />
                </div>
              </>
            )}
          </Spin>
        </TabPane>
      </Tabs>

      {/* 模板编辑弹窗 */}
      <Modal
        title={editingTemplate ? '编辑灵感模板' : '新建灵感模板'}
        open={templateModalVisible}
        onOk={() => templateForm.submit()}
        onCancel={() => {
          setTemplateModalVisible(false);
          templateForm.resetFields();
          setEditingTemplate(null);
        }}
        width={700}
        confirmLoading={loading}
      >
        <Form form={templateForm} layout="vertical" onFinish={handleSubmitTemplate}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="例如：痛点共鸣型带货模板" />
          </Form.Item>

          <Form.Item name="strategy" label="创作策略" rules={[{ required: true }]}>
            <TextArea rows={3} placeholder="描述这个模板的核心创作策略，例如：'通过直击用户痛点引发共鸣，快速展示产品核心价值，最后用优惠活动引导下单'" />
          </Form.Item>

          <Form.Item name="category" label="分类">
            <Select placeholder="选择分类">
              <Option value="美妆">美妆</Option>
              <Option value="数码">数码</Option>
              <Option value="食品">食品</Option>
              <Option value="服饰">服饰</Option>
              <Option value="家居">家居</Option>
            </Select>
          </Form.Item>

          <Form.Item name="tags" label="标签">
            <Input placeholder="多个标签用逗号分隔，例如：带货, 痛点, 美妆" />
          </Form.Item>

          <Form.Item name="factors" label="因子组合 (JSON)">
            <TextArea rows={6} placeholder={'例如：\n{\n  "hook": "痛点开场文案",\n  "scene1": "产品展示场景",\n  "cta": "结尾引导"\n}'} />
          </Form.Item>

          <Form.Item name="reference_video_ids" label="参考视频ID">
            <Input placeholder="从优质视频库聚类而来的视频ID，多个用逗号分隔" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 因子编辑弹窗 */}
      <Modal
        title={editingFactor ? '编辑策略因子' : '新建策略因子'}
        open={factorModalVisible}
        onOk={() => factorForm.submit()}
        onCancel={() => {
          setFactorModalVisible(false);
          factorForm.resetFields();
          setEditingFactor(null);
        }}
        width={700}
        confirmLoading={loading}
      >
        <Form form={factorForm} layout="vertical" onFinish={handleSubmitFactor}>
          <Form.Item name="name" label="因子名称" rules={[{ required: true }]}>
            <Input placeholder="例如：夏天脱妆痛点开场" />
          </Form.Item>

          <Form.Item name="factor_type" label="因子类型" rules={[{ required: true }]}>
            <Select placeholder="选择因子类型">
              <Option value="hook">Hook开场</Option>
              <Option value="scene">场景构建</Option>
              <Option value="narration">旁白话术</Option>
              <Option value="visual">视觉呈现</Option>
              <Option value="ending">结尾引导</Option>
            </Select>
          </Form.Item>

          <Form.Item name="description" label="因子描述">
            <TextArea rows={2} placeholder="描述这个策略因子的用途和效果" />
          </Form.Item>

          <Form.Item name="category" label="分类">
            <Select placeholder="选择分类">
              <Option value="美妆">美妆</Option>
              <Option value="数码">数码</Option>
              <Option value="食品">食品</Option>
              <Option value="服饰">服饰</Option>
              <Option value="家居">家居</Option>
            </Select>
          </Form.Item>

          <Form.Item name="tags" label="标签">
            <Input placeholder="多个标签用逗号分隔" />
          </Form.Item>

          <Form.Item name="content" label="因子内容 (JSON)" rules={[{ required: true }]}>
            <TextArea rows={6} placeholder={'例如：\n{\n  "text": "姐妹们，夏天是不是一出门就脱妆？",\n  "visual": "女生擦汗妆容花掉的画面",\n  "duration": "3s"\n}'} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 生成剧本弹窗 */}
      <Modal
        title="使用模板生成剧本"
        open={generateModalVisible}
        onOk={() => generateForm.submit()}
        onCancel={() => {
          setGenerateModalVisible(false);
          generateForm.resetFields();
          setSelectedTemplate(null);
        }}
        width={600}
        confirmLoading={loading}
      >
        {selectedTemplate && (
          <Form form={generateForm} layout="vertical" onFinish={handleGenerateScript}>
            <div style={{ marginBottom: '16px' }}>
              <Text strong>当前模板：</Text>
              <Tag color="blue">{selectedTemplate.name}</Tag>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <Text strong>创作策略：</Text>
              <Paragraph>{selectedTemplate.strategy}</Paragraph>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <Text strong>包含因子：</Text>
              <Space wrap>
                {Object.keys(selectedTemplate.factors || {}).map((key) => (
                  <Tag key={key}>{key}</Tag>
                ))}
              </Space>
            </div>

            <Divider />

            <Form.Item name="product_info" label="产品信息 (JSON)">
              <TextArea rows={4} placeholder={'例如：\n{\n  "name": "持妆粉底液",\n  "price": "¥199",\n  "features": ["持妆24小时", "防水防汗"]\n}'} />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default TemplatesPage;
