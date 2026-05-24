import { Card, Row, Col, Statistic } from 'antd'
import { VideoCameraOutlined, FileTextOutlined, ThunderboltOutlined } from '@ant-design/icons'

export default function Dashboard() {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>工作台</h2>
      <Row gutter={16}>
        <Col span={8}>
          <Card><Statistic title="素材总数" value={0} prefix={<VideoCameraOutlined />} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="剧本总数" value={0} prefix={<FileTextOutlined />} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="视频任务" value={0} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
      </Row>
    </div>
  )
}
