import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../utils/api'

export default function Login() {
  const navigate = useNavigate()
  const onFinish = async (values: any) => {
    try {
      const res: any = await login(values)
      localStorage.setItem('token', res.access_token)
      message.success('登录成功')
      navigate('/')
    } catch (error: any) {
      message.error(error.response?.data?.detail?.message || error.response?.data?.detail || '登录失败')
    }
  }
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f5f5f5' }}>
      <Card title="Video-AI 登录" style={{ width: 400 }}>
        <Form onFinish={onFinish}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>登录</Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            还没有账号？<Link to="/register">注册</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}
