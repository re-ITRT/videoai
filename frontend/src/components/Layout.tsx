import { Layout as AntLayout, Menu } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  BookOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useAuth } from '../hooks/useAuth'

const { Sider, Content, Header } = AntLayout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/material', icon: <VideoCameraOutlined />, label: '素材管理' },
  { key: '/script', icon: <FileTextOutlined />, label: '剧本中心' },
  { key: '/creation', icon: <ThunderboltOutlined />, label: '视频创作' },
  { key: '/reference', icon: <PlayCircleOutlined />, label: '参考视频' },
  { key: '/templates', icon: <BookOutlined />, label: '灵感模板' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={200} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 20, color: '#4F46E5' }}>
          Video-AI
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', borderBottom: '1px solid #f0f0f0' }}>
          <span style={{ marginRight: 16 }}>{user?.nickname || user?.username}</span>
          <LogoutOutlined style={{ cursor: 'pointer' }} onClick={logout} />
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8, minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
