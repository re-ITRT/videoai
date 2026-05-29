import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Descriptions, message, Spin, Select, Space } from 'antd'
import { useAuth } from '../hooks/useAuth'
import { getMyProfile, updateMyProfile, changeMyPassword, getAIConfig, updateAIConfig, scanModels } from '../utils/api'

export default function Profile() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [changingPwd, setChangingPwd] = useState(false)
  const [profileForm] = Form.useForm()
  const [pwdForm] = Form.useForm()

  useEffect(() => {
    getMyProfile()
      .then((res: any) => {
        setProfile(res)
        profileForm.setFieldsValue({ nickname: res.nickname || '', email: res.email || '' })
      })
      .catch(() => message.error('获取个人信息失败'))
      .finally(() => setLoading(false))
  }, [])

  const handleUpdateProfile = async (values: { nickname: string; email: string }) => {
    setSaving(true)
    try {
      const res: any = await updateMyProfile(values)
      setProfile(res)
      message.success('更新成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail?.message || error.response?.data?.detail || '更新失败')
    }
    setSaving(false)
  }

  const handleChangePassword = async (values: { old_password: string; new_password: string }) => {
    setChangingPwd(true)
    try {
      await changeMyPassword(values)
      message.success('密码修改成功')
      pwdForm.resetFields()
    } catch (error: any) {
      message.error(error.response?.data?.detail?.message || error.response?.data?.detail || '密码修改失败')
    }
    setChangingPwd(false)
  }

  if (loading) return <Spin />

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <Card title="个人信息" style={{ marginBottom: 24 }}>
        <Descriptions column={1}>
          <Descriptions.Item label="用户名">{user?.username || profile?.username}</Descriptions.Item>
          <Descriptions.Item label="角色">{profile?.role === 'admin' ? '管理员' : '用户'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{profile?.created_at ? new Date(profile.created_at).toLocaleString() : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="编辑资料" style={{ marginBottom: 24 }}>
        <Form form={profileForm} layout="vertical" onFinish={handleUpdateProfile}>
          <Form.Item name="nickname" label="昵称">
            <Input placeholder="输入昵称" />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}>
            <Input placeholder="输入邮箱" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>保存修改</Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="AI 配置" style={{ marginBottom: 24 }}>
        <AIConfigForm />
      </Card>

      <Card title="修改密码">
        <Form form={pwdForm} layout="vertical" onFinish={handleChangePassword}>
          <Form.Item name="old_password" label="当前密码" rules={[{ required: true, message: '请输入当前密码' }]}>
            <Input.Password placeholder="输入当前密码" />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '密码至少6位' }]}>
            <Input.Password placeholder="输入新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={changingPwd}>修改密码</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

function AIConfigForm() {
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    getAIConfig().then((res: any) => {
      setConfig(res)
      form.setFieldsValue({ base_url: res.base_url, api_key: '', model: [res.model] })
    }).catch(() => message.error('加载AI配置失败')).finally(() => setLoading(false))
  }, [])

  const handleSave = async (values: any) => {
    setSaving(true)
    try {
      const data: any = { base_url: values.base_url, model: values.model?.[0] }
      if (values.api_key) data.api_key = values.api_key
      const res = await updateAIConfig(data)
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
      const res: any = await scanModels(data)
      form.setFieldsValue({ model: [res.selected] })
      setConfig((prev: any) => ({ ...prev, available_models: res.models, base_url: values.base_url }))
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
