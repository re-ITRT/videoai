import { Layout as AntLayout, Menu, Dropdown, Space } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  BookOutlined,
  UserOutlined,
  TeamOutlined,
  LogoutOutlined,
  AppstoreOutlined
} from '@ant-design/icons'
import { useAuth } from '../hooks/useAuth'

const { Sider, Content, Header } = AntLayout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/material', icon: <VideoCameraOutlined />, label: '素材管理' },
  { key: '/script', icon: <FileTextOutlined />, label: '剧本模板' },
  { key: '/creation', icon: <ThunderboltOutlined />, label: '视频创作' },
  { key: '/reference', icon: <PlayCircleOutlined />, label: '参考视频' },
  { key: '/templates', icon: <BookOutlined />, label: '灵感模板' },
  { key: '/studio', icon: <AppstoreOutlined />, label: '工作流工作室' },
  { key: '/profile', icon: <UserOutlined />, label: '个人中心' },
]

const adminMenus = [
  { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

  const allItems = (user as any)?.role === 'admin'
    ? [...menuItems, { type: 'divider' as const }, { key: 'admin-group', type: 'group' as const, label: '管理后台', children: adminMenus }]
    : menuItems

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人中心' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
  ]

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout()
    } else if (key === 'profile') {
      navigate('/profile')
    }
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={200} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 20, color: '#4F46E5' }}>
          Video-AI
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={allItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', borderBottom: '1px solid #f0f0f0' }}>
          <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
            <span style={{ cursor: 'pointer' }}>
              <Space>
                <UserOutlined />
                {user?.nickname || user?.username}
              </Space>
            </span>
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8, minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
