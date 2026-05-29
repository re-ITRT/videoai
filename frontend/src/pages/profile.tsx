import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Descriptions, message, Spin } from 'antd'
import { useAuth } from '../hooks/useAuth'
import WorkflowSettings from '../modules/workflow/WorkflowSettings'
import LlmConfigForm from '../modules/common/LlmConfigForm'
import { getMyProfile, updateMyProfile, changeMyPassword, getAIConfig, updateAIConfig, scanModels } from '../utils/api'

export default function Profile() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [changingPwd, setChangingPwd] = useState(false)
  const [profileForm] = Form.useForm()
  const [pwdForm] = Form.useForm()

  useEffect(() => {
    getMyProfile().then((res: any) => {
      setProfile(res)
      profileForm.setFieldsValue({ nickname: res.nickname, email: res.email })
    }).catch(() => message.error('加载个人信息失败')).finally(() => setLoading(false))
  }, [])

  const handleUpdateProfile = async (values: any) => {
    setSaving(true)
    try {
      await updateMyProfile(values)
      message.success('资料更新成功')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '更新失败')
    }
    setSaving(false)
  }

  const handleChangePassword = async (values: any) => {
    setChangingPwd(true)
    try {
      await changeMyPassword(values)
      message.success('密码修改成功')
      pwdForm.resetFields()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '密码修改失败')
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
          <Form.Item name="nickname" label="昵称"><Input placeholder="输入昵称" /></Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}>
            <Input placeholder="输入邮箱" />
          </Form.Item>
          <Form.Item><Button type="primary" htmlType="submit" loading={saving}>保存修改</Button></Form.Item>
        </Form>
      </Card>

      <Card title="AI 配置" style={{ marginBottom: 24 }}>
        <LlmConfigForm getConfig={getAIConfig} saveConfig={updateAIConfig} scanModels={scanModels} />
      </Card>

      <Card title="工作流设置" style={{ marginBottom: 24 }}>
        <WorkflowSettings />
      </Card>

      <Card title="修改密码">
        <Form form={pwdForm} layout="vertical" onFinish={handleChangePassword}>
          <Form.Item name="old_password" label="当前密码" rules={[{ required: true, message: '请输入当前密码' }]}>
            <Input.Password placeholder="输入当前密码" />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true }, { min: 6, message: '密码至少6位' }]}>
            <Input.Password placeholder="输入新密码" />
          </Form.Item>
          <Form.Item><Button type="primary" htmlType="submit" loading={changingPwd}>修改密码</Button></Form.Item>
        </Form>
      </Card>
    </div>
  )
}
