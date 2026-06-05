import { useState, useEffect } from 'react'
import { Table, Button, Card, message, Space, Modal, Input, Tabs, Tag, Spin, Descriptions, Progress, Typography, Divider } from 'antd'
import { PlusOutlined, EditOutlined, ThunderboltOutlined } from '@ant-design/icons'
import request from '../../utils/request'

const { TextArea } = Input
const { Text } = Typography

/** 把 system.md 按 # 标题拆成 { "角色定义": "...", "任务目标": "..." } */
function parseSections(text: string): Record<string, string> {
  const sections: Record<string, string> = {}
  const lines = text.split('\n')
  let key = ''
  let buf: string[] = []
  for (const line of lines) {
    if (line.startsWith('# ')) {
      if (key && buf.length) sections[key] = buf.join('\n').trim()
      key = line.replace('# ', '').trim()
      buf = []
    } else {
      buf.push(line)
    }
  }
  if (key && buf.length) sections[key] = buf.join('\n').trim()
  return sections
}

/** 把 sections 重新组装回 system.md */
function buildSystemMd(sections: Record<string, string>): string {
  return Object.entries(sections)
    .filter(([, v]) => v)
    .map(([k, v]) => `# ${k}\n${v}`)
    .join('\n\n')
}

export default function ScriptTemplates() {
  const [templates, setTemplates] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [editVisible, setEditVisible] = useState(false)
  const [editName, setEditName] = useState('')
  const [sysSections, setSysSections] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [createVisible, setCreateVisible] = useState(false)
  const [createName, setCreateName] = useState('')
  const [creating, setCreating] = useState(false)

  // AI 生成
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiResultVisible, setAiResultVisible] = useState(false)
  const [aiTemplates, setAiTemplates] = useState<any[]>([])
  const [aiSource, setAiSource] = useState('')

  // 优化建议
  const [optLoading, setOptLoading] = useState<string | null>(null)
  const [optResult, setOptResult] = useState<any>(null)
  const [optVisible, setOptVisible] = useState(false)
  const [optPrompting, setOptPrompting] = useState(false)
  const [optPromptResult, setOptPromptResult] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/workflows/prompts')
      const list = Object.entries(res?.templates || {}).map(([name, info]: any) => ({ name, ...info }))
      setTemplates(list)
    } catch { message.error('加载模板失败') }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const openEdit = async (name: string) => {
    if (name === 'default') return message.warning('默认模板不能修改')
    setEditName(name)
    setEditVisible(true)
    try {
      const res: any = await request.get(`/workflows/prompts/${name}`)
      const sys = res.files?.['system.md'] || ''
      setSysSections(parseSections(sys))
    } catch { message.error('加载模板失败') }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await request.put(`/workflows/prompts/${editName}/system.md`, { content: buildSystemMd(sysSections) })
      message.success('模板已保存')
    } catch { message.error('保存失败') }
    setSaving(false)
  }

  const handleCreate = async () => {
    if (!createName.trim()) return message.warning('请输入模板名称')
    setCreating(true)
    try {
      await request.post('/workflows/templates', { name: createName.trim() })
      message.success('模板已创建')
      setCreateVisible(false)
      setCreateName('')
      load()
    } catch (e: any) { message.error(e?.response?.data?.detail || '创建失败') }
    setCreating(false)
  }

  // AI 智能生成
  const handleAiGenerate = async () => {
    setAiGenerating(true)
    try {
      const res: any = await request.post('/template/templates/ai-generate', {})
      setAiTemplates(res.templates || [])
      setAiSource(res.source || 'data')
      setAiResultVisible(true)
      if (!res.templates?.length) message.warning('AI 未能生成模板')
    } catch { message.error('AI 生成失败') }
    setAiGenerating(false)
  }

  // 优化建议
  const handleOptimize = async (name: string) => {
    setOptLoading(name)
    try {
      const res: any = await request.post('/template/templates/optimize', { template_name: name })
      setOptResult(res)
      setOptVisible(true)
    } catch { message.error('获取优化建议失败') }
    setOptLoading(null)
  }

  // 立即优化 Prompt
  const handleOptimizePrompt = async () => {
    if (!optResult?.template) return
    setOptPrompting(true)
    setOptPromptResult(null)
    try {
      const tpl: any = await request.get(`/workflows/prompts/${optResult.template}`)
      const sysContent = tpl.files?.['system.md'] || ''
      const res: any = await request.post('/template/templates/optimize-prompt', {
        template_name: optResult.template,
        content: sysContent,
      })
      if (res.optimized_content) {
        setOptPromptResult(res.optimized_content)
      } else {
        message.warning('优化失败，返回原始内容')
      }
    } catch { message.error('Prompt 优化请求失败') }
    setOptPrompting(false)
  }

  // 保存优化后的 Prompt
  const saveOptimizedPrompt = async () => {
    if (!optPromptResult || !optResult?.template) return
    try {
      await request.put(`/workflows/prompts/${optResult.template}/system.md`, { content: optPromptResult })
      message.success('优化后的 Prompt 已保存')
      setOptPromptResult(null)
    } catch { message.error('保存失败') }
  }

  // 应用AI模板（保存为剧本模板）
  const applyAiTemplate = async (tpl: any) => {
    const name = tpl.name || `AI推荐-${Date.now()}`
    try {
      // 构造 system.md 内容
      const strategyLines = [
        `# 策略描述`,
        tpl.strategy || '',
        ``,
        `# 因子组合`,
        ...Object.entries(tpl.factors || {}).map(([k, v]: any) => `- ${v?.type || k}：${v?.description || ''}`),
        ``,
        `# 适用品类`,
        tpl.category || '通用',
        ``,
        `# 推荐标签`,
        (tpl.tags || []).join('、'),
        ``,
        `# 归因评分`,
        `attribution_score: ${tpl.attribution_score || 0}`,
      ].join('\n')

      await request.post('/workflows/templates', {
        name,
        description: tpl.strategy?.slice(0, 100) || name,
        prompt_preview: `${tpl.strategy?.slice(0, 200)}...`,
      })
      await request.put(`/workflows/prompts/${name}/system.md`, { content: strategyLines })
      message.success(`模板「${name}」已创建`)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '应用失败')
    }
  }

  const columns = [
    { title: '模板名称', dataIndex: 'name', render: (v: string) =>
      v === 'default' ? <span>{v} <Tag color="blue">默认</Tag></span>
      : <a onClick={() => openEdit(v)}>{v}</a> },
    { title: '描述', dataIndex: 'description' },
    { title: 'Prompt 预览', dataIndex: 'prompt_preview', ellipsis: true },
    { title: '操作', render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<EditOutlined />} disabled={r.name === 'default'} onClick={() => openEdit(r.name)}>编辑</Button>
        <Button size="small" loading={optLoading === r.name} onClick={() => handleOptimize(r.name)} disabled={r.name === 'default'}>优化建议</Button>
        {r.name !== 'default' && <Button size="small" danger onClick={async () => {
          try { await request.delete(`/workflows/templates/${r.name}`); message.success('已删除'); load() }
          catch { message.error('删除失败') }
        }}>删除</Button>}
      </Space>
    )},
  ]

  const sectionKeys = Object.keys(sysSections)

  return (
    <Card title="剧本模板" extra={
      <Space>
        <Button icon={<ThunderboltOutlined />} loading={aiGenerating} onClick={handleAiGenerate}>AI 智能生成</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>新建模板</Button>
      </Space>
    }>
      <Table dataSource={templates} columns={columns} rowKey="name" loading={loading} />

      {/* 新建模板 */}
      <Modal title="新建模板" open={createVisible} onCancel={() => setCreateVisible(false)} onOk={handleCreate} confirmLoading={creating}>
        <Input placeholder="输入模板名称" value={createName} onChange={e => setCreateName(e.target.value)} onPressEnter={handleCreate} />
      </Modal>

      {/* 编辑模板 */}
      <Modal title={`编辑模板 - ${editName}`} open={editVisible} onCancel={() => setEditVisible(false)}
        width={700} footer={null} destroyOnClose>
        {sectionKeys.length > 0 && (
          <Tabs defaultActiveKey={sectionKeys[0]} items={sectionKeys.map(k => ({
            key: k,
            label: k,
            children: (
              <TextArea rows={8} value={sysSections[k] || ''}
                onChange={e => setSysSections({ ...sysSections, [k]: e.target.value })}
                style={{ fontSize: 14 }} />
            ),
          }))} />
        )}
        <Button type="primary" style={{ marginTop: 12 }} onClick={handleSave} loading={saving}>保存模板</Button>
      </Modal>

      {/* AI 生成结果弹窗 */}
      <Modal title="🤖 AI 智能生成的模板" open={aiResultVisible} onCancel={() => setAiResultVisible(false)}
        width={800} footer={null} destroyOnClose>
        <Spin spinning={aiTemplates.length === 0}>
          {aiTemplates.map((tpl: any, i: number) => (
            <Card key={i} size="small" title={
              <Space>
                <Tag color="blue">#{i + 1}</Tag>
                <strong>{tpl.name}</strong>
                <Tag color="green">推荐度: {tpl.attribution_score}/100</Tag>
              </Space>
            } extra={<Button size="small" type="primary" onClick={() => applyAiTemplate(tpl)}>应用此模板</Button>}
              style={{ marginBottom: 12 }}>
              <Descriptions column={1} size="small" style={{ fontSize: 12 }}>
                <Descriptions.Item label="📐 策略描述">{tpl.strategy}</Descriptions.Item>
                <Descriptions.Item label="🏷️ 适用品类">
                  <Tag color="purple">{tpl.category || '通用'}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="🏷️ 标签">
                  <Space wrap size={[4, 4]}>{(tpl.tags || []).map((t: string) => <Tag key={t}>{t}</Tag>)}</Space>
                </Descriptions.Item>
                <Descriptions.Item label="🎯 归因评分">
                  <Progress percent={tpl.attribution_score || 0} size="small" strokeColor="#52c41a" />
                </Descriptions.Item>
              </Descriptions>
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#1677ff' }}>展开因子详情</summary>
                <div style={{ marginTop: 8 }}>
                  {Object.entries(tpl.factors || {}).map(([k, v]: any) => (
                    <div key={k} style={{ marginBottom: 4, fontSize: 12 }}>
                      <Tag color="geekblue">{v?.type || k}</Tag>
                      <span style={{ color: '#666' }}>{v?.description || ''}</span>
                    </div>
                  ))}
                </div>
              </details>
            </Card>
          ))}
          {aiTemplates.length > 0 && (
            <div style={{ textAlign: 'center', marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>数据来源: {aiSource === 'ai' ? 'AI 分析' : '归因数据'}</Text>
            </div>
          )}
        </Spin>
      </Modal>

      {/* 优化建议弹窗 */}
      <Modal title={`💡 优化建议：${optResult?.template || ''}`} open={optVisible} onCancel={() => setOptVisible(false)}
        footer={null} width={600} destroyOnClose>
        {optResult && (
          <div>
            <div style={{ marginBottom: 12, padding: 8, background: '#f5f5f5', borderRadius: 4, fontSize: 13 }}>
              <Text strong>概述：</Text>{optResult.summary}
            </div>
            {optResult.suggestions?.map((s: any, i: number) => (
              <Card key={i} size="small" style={{ marginBottom: 8 }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Space>
                    <Tag color="blue">#{i + 1}</Tag>
                    <Text strong style={{ fontSize: 13 }}>{s.aspect}</Text>
                  </Space>
                  <div style={{ fontSize: 12 }}>{s.suggestion}</div>
                  <div style={{ fontSize: 11, color: '#666' }}>预期效果：{s.expected_impact}</div>
                </Space>
              </Card>
            ))}
            <div style={{ textAlign: 'right', marginTop: 8 }}>
              <Tag color={optResult.priority === '高' ? 'red' : optResult.priority === '中' ? 'orange' : 'blue'}>
                优先级: {optResult.priority}
              </Tag>
              <Tag color="default" style={{ marginLeft: 4 }}>来源: {optResult.source === 'ai' ? 'AI分析' : '归因数据'}</Tag>
            </div>
            {/* 立即优化按钮 */}
            <div style={{ textAlign: 'center', margin: '12px 0' }}>
              <Button type="primary" icon={<ThunderboltOutlined />} loading={optPrompting}
                onClick={handleOptimizePrompt} block>
                立即优化 Prompt
              </Button>
            </div>
            {/* 优化后的 Prompt 预览 */}
            {optPromptResult && (
              <div>
                <Divider style={{ margin: '8px 0' }} />
                <Text strong style={{ fontSize: 13 }}>优化后的 Prompt：</Text>
                <div style={{ marginTop: 4, padding: 8, background: '#f6ffed', borderRadius: 4, border: '1px solid #b7eb8f', maxHeight: 300, overflow: 'auto', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                  {optPromptResult}
                </div>
                <Space style={{ marginTop: 8, width: '100%', justifyContent: 'center' }}>
                  <Button type="primary" onClick={saveOptimizedPrompt}>保存到模板</Button>
                  <Button onClick={() => setOptPromptResult(null)}>取消</Button>
                </Space>
              </div>
            )}
          </div>
        )}
      </Modal>
    </Card>
  )
}
