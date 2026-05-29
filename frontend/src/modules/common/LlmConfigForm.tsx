import { useState, useEffect } from 'react'
import { Form, Input, Button, Select, Space, Spin, message } from 'antd'

interface Props {
  /** 读取配置的API函数 */
  getConfig: () => Promise<any>
  /** 保存配置的API函数，接收 {base_url, api_key?, model} */
  saveConfig: (data: any) => Promise<any>
  /** 扫描模型的API函数 */
  scanModels: (data: any) => Promise<any>
}

/**
 * 通用 LLM 配置表单（带扫描模型）
 * 用于 AI 配置 + 工作流 LLM 配置
 */
export default function LlmConfigForm({ getConfig, saveConfig, scanModels: scanModelsApi }: Props) {
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    getConfig().then((res: any) => {
      setConfig(res)
      form.setFieldsValue({ base_url: res.base_url, api_key: '', model: [res.model] })
    }).catch(() => message.error('加载配置失败')).finally(() => setLoading(false))
  }, [])

  const handleSave = async (values: any) => {
    setSaving(true)
    try {
      const data: any = { base_url: values.base_url, model: values.model?.[0] }
      if (values.api_key) data.api_key = values.api_key
      const res = await saveConfig(data)
      setConfig(res)
      form.setFieldsValue({ api_key: '' })
      message.success('配置已保存')
    } catch { message.error('保存失败') }
    setSaving(false)
  }

  const handleScan = async () => {
    setScanning(true)
    try {
      const values = form.getFieldsValue()
      const data: any = {}
      if (values.api_key) data.api_key = values.api_key
      data.base_url = values.base_url || 'https://api.openai.com/v1'
      const res: any = await scanModelsApi(data)
      form.setFieldsValue({ model: [res.selected] })
      setConfig((prev: any) => ({
        ...prev, available_models: res.models, base_url: values.base_url,
        model: res.selected,
      }))
      message.success(`扫描到 ${res.models.length} 个模型`)
    } catch (e: any) { message.error(e?.response?.data?.detail || '扫描失败') }
    setScanning(false)
  }

  if (loading) return <Spin />

  return (
    <Form form={form} layout="vertical" onFinish={handleSave}>
      <Form.Item name="base_url" label="API 地址" rules={[{ required: true }]}>
        <Input placeholder="https://api.openai.com/v1" />
      </Form.Item>
      <Form.Item name="api_key" label="API Key">
        <Input.Password placeholder={config?.has_api_key ? '••••••••（已配置，留空不修改）' : '输入 API Key'} />
      </Form.Item>
      <Form.Item label="模型">
        <Space>
          <Form.Item name="model" noStyle>
            <Select style={{ width: 280 }} placeholder="选择或输入模型名" mode="tags" maxCount={1}
              showSearch
              dropdownRender={(menu) => menu}
              options={config?.available_models?.map((m: string) => ({ value: m, label: m })) || []}
            />
          </Form.Item>
          <Button onClick={handleScan} loading={scanning}>扫描模型</Button>
        </Space>
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" loading={saving}>保存配置</Button>
      </Form.Item>
    </Form>
  )
}
