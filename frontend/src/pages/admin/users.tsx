import { useState, useEffect } from 'react'
import { Card, Table, Switch, Select, Button, Popconfirm, message } from 'antd'
import { getUsers, adminUpdateUser, adminDeleteUser } from '../../utils/api'
import { useAuth } from '../../hooks/useAuth'
import { Navigate } from 'react-router-dom'

export default function AdminUsers() {
  const { user } = useAuth()
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const loadUsers = async () => {
    setLoading(true)
    try {
      const res: any = await getUsers()
      setUsers(Array.isArray(res) ? res : res.items || res.data || [])
    } catch {
      message.error('获取用户列表失败')
    }
    setLoading(false)
  }

  useEffect(() => { loadUsers() }, [])

  if (!user || (user as any).role !== 'admin') {
    return <Navigate to="/" replace />
  }

  const handleToggleActive = async (userId: number, isActive: boolean) => {
    try {
      await adminUpdateUser(userId, { is_active: isActive })
      message.success('更新成功')
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail?.message || error.response?.data?.detail || '操作失败')
    }
  }

  const handleChangeRole = async (userId: number, role: string) => {
    try {
      await adminUpdateUser(userId, { role })
      message.success('角色更新成功')
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail?.message || error.response?.data?.detail || '操作失败')
    }
  }

  const handleDelete = async (userId: number) => {
    try {
      await adminDeleteUser(userId)
      message.success('删除成功')
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail?.message || error.response?.data?.detail || '删除失败')
    }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username' },
    { title: '昵称', dataIndex: 'nickname', render: (v: string | null) => v || '-' },
    { title: '邮箱', dataIndex: 'email', render: (v: string | null) => v || '-' },
    {
      title: '角色',
      dataIndex: 'role',
      render: (role: string, record: any) => (
        <Select
          value={role}
          style={{ width: 120 }}
          onChange={(val) => handleChangeRole(record.id, val)}
        >
          <Select.Option value="user">用户</Select.Option>
          <Select.Option value="admin">管理员</Select.Option>
        </Select>
      ),
    },
    {
      title: '是否激活',
      dataIndex: 'is_active',
      render: (isActive: boolean, record: any) => (
        <Switch
          checked={isActive}
          onChange={(checked) => handleToggleActive(record.id, checked)}
        />
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作',
      render: (_: any, record: any) => (
        <Popconfirm
          title="确定删除此用户？"
          onConfirm={() => handleDelete(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button danger size="small">删除</Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <Card title="用户管理">
      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </Card>
  )
}
