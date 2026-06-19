import { useState, useEffect } from 'react'
import { Card, Button, Spin, message, Tag, Space } from 'antd'
import {
  getWorkflowConfigs, updateWorkflowConfig, getAvailableWorkflows,
} from '../../utils/api'
import request from '../../utils/request'
import LlmConfigForm from '../common/LlmConfigForm'
import PromptEditor from './PromptEditor'

export default function WorkflowSettings() {
  const [configs, setConfigs] = useState<Record<string, any>>({})
  const [availMeta, setAvailMeta] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [promptWorkflow, setPromptWorkflow] = useState<string | null>(null)

  const load = async () => {
    try {
      const [cfgRes, availRes] = await Promise.all([
        getWorkflowConfigs(),
        getAvailableWorkflows(),
      ])
      const cfgs: Record<string, any> = {}
      for (const c of (cfgRes as any)) cfgs[c.workflow_name] = c
      setConfigs(cfgs)
      setAvailMeta((availRes as any).workflows || {})
    } catch { message.error('加载工作流配置失败') }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  if (loading) return <Spin />

  const names = Object.keys(availMeta)
  if (names.length === 0) return <div style={{ color: '#999' }}>暂无可用工作流</div>

  return (
    <div>
      {names.map((name) => {
        const meta = availMeta[name]
        const isLlm = meta.fields?.some((f: any) => f.key === 'model')
        const cfg = configs[name]?.config || {}

        return (
          <Card
            key={name}
            title={
              <Space>
                <span>{meta.name}</span>
                <Tag color={configs[name]?.enabled ? 'green' : 'default'}>
                  {configs[name]?.enabled ? '本地' : 'Coze'}
                </Tag>
              </Space>
            }
            size="small"
            style={{ marginBottom: 12 }}
            extra={<Button size="small" onClick={() => setPromptWorkflow(name)}>编辑 Prompt</Button>}
          >
            <p style={{ color: '#666', fontSize: 13, marginBottom: 12 }}>{meta.description}</p>

            {isLlm ? (
              <LlmConfigForm
                getConfig={async () => ({
                  base_url: cfg.base_url || '',
                  model: cfg.model || '',
                  has_api_key: !!cfg.api_key,
                  available_models: cfg.available_models || [],
                })}
                saveConfig={async (data) => {
                  const merged = { ...cfg, ...data }
                  const res: any = await updateWorkflowConfig(name, { config: merged })
                  const newCfg = res.config
                  return {
                    base_url: newCfg.base_url || '',
                    model: newCfg.model || '',
                    has_api_key: !!newCfg.api_key,
                    available_models: newCfg.available_models || [],
                  }
                }}
                scanModels={async (data) => {
                  const res = await request.post(`/workflows/configs/${name}/scan-models`, data)
                  return res
                }}
              />
            ) : (
              <p style={{ color: '#999', fontSize: 13 }}>该工作流无需配置</p>
            )}
          </Card>
        )
      })}
      {promptWorkflow && (
        <PromptEditor workflowName={promptWorkflow} visible={!!promptWorkflow} onClose={() => setPromptWorkflow(null)} />
      )}
    </div>
  )
}
