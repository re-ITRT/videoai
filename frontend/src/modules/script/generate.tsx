import React, { useState, useCallback } from 'react';
import {
  Card,
  Button,
  Input,
  InputNumber,
  Select,
  Space,
  Typography,
  Divider,
  message,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  SwapOutlined,
  SaveOutlined,
  CaretUpOutlined,
  CaretDownOutlined,
} from '@ant-design/icons';

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

// ============ 类型定义 ============
interface Scene {
  id: number;
  order: number;
  description: string;
  narration: string;
  dialogue?: string;
  visual_style?: string;
  camera_movement?: string;
  bgm_type?: string;
  duration: number;
  transition?: string;
  material_slice_ids?: number[];
}

interface Factor {
  name: string;
  value: string;
  type: 'visual_style' | 'bgm_type' | 'transition' | 'opening' | 'ending';
}

// ============ 预设因子 ============
const FACTOR_OPTIONS: Record<string, Factor[]> = {
  visual_style: [
    { name: '明亮清新', value: 'bright_fresh', type: 'visual_style' },
    { name: '日系复古', value: 'japanese_vintage', type: 'visual_style' },
    { name: '赛博朋克', value: 'cyberpunk', type: 'visual_style' },
    { name: '极简高级', value: 'minimalist', type: 'visual_style' },
  ],
  bgm_type: [
    { name: '轻快节奏', value: 'upbeat', type: 'bgm_type' },
    { name: '温馨抒情', value: 'warm', type: 'bgm_type' },
    { name: '科技感', value: 'techno', type: 'bgm_type' },
    { name: '国风', value: 'chinese_style', type: 'bgm_type' },
  ],
  transition: [
    { name: '淡入淡出', value: 'fade', type: 'transition' },
    { name: '闪切', value: 'flash_cut', type: 'transition' },
    { name: '滑入', value: 'slide', type: 'transition' },
    { name: '缩放转场', value: 'zoom', type: 'transition' },
  ],
};

// ============ 默认分镜模板 ============
const DEFAULT_SCENE: Omit<Scene, 'id' | 'order'> = {
  description: '',
  narration: '',
  duration: 5,
  visual_style: 'bright_fresh',
  bgm_type: 'upbeat',
  transition: 'fade',
};

// ============ 分镜卡片组件 ============
interface SceneCardProps {
  scene: Scene;
  index: number;
  total: number;
  onUpdate: (id: number, updates: Partial<Scene>) => void;
  onDelete: (id: number) => void;
  onMoveUp: (id: number) => void;
  onMoveDown: (id: number) => void;
}

const SceneCard: React.FC<SceneCardProps> = ({
  scene,
  index,
  total,
  onUpdate,
  onDelete,
  onMoveUp,
  onMoveDown,
}) => {
  const isFirst = index === 0;
  const isLast = index === total - 1;

  return (
    <Card
      size="small"
      style={{ marginBottom: 16 }}
      title={
        <Space>
          <Text strong>分镜 {String(index + 1).padStart(2, '0')}</Text>
          <InputNumber
            min={1}
            max={60}
            size="small"
            value={scene.duration}
            onChange={(v) => onUpdate(scene.id, { duration: v || 5 })}
            style={{ width: 70 }}
          />
          <Text type="secondary">秒</Text>
        </Space>
      }
      extra={
        <Space>
          <Button
            icon={<CaretUpOutlined />}
            size="small"
            disabled={isFirst}
            onClick={() => onMoveUp(scene.id)}
          />
          <Button
            icon={<CaretDownOutlined />}
            size="small"
            disabled={isLast}
            onClick={() => onMoveDown(scene.id)}
          />
          <Popconfirm
            title="确认删除此分镜？"
            onConfirm={() => onDelete(scene.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 画面描述 */}
        <div>
          <Text strong style={{ display: 'block', marginBottom: 4 }}>
            画面描述
          </Text>
          <TextArea
            value={scene.description}
            onChange={(e) => onUpdate(scene.id, { description: e.target.value })}
            placeholder="描述这个分镜的画面内容..."
            rows={2}
          />
        </div>

        {/* 旁白 */}
        <div>
          <Text strong style={{ display: 'block', marginBottom: 4 }}>
            旁白台词
          </Text>
          <TextArea
            value={scene.narration}
            onChange={(e) => onUpdate(scene.id, { narration: e.target.value })}
            placeholder="AI旁白的台词内容..."
            rows={2}
          />
        </div>

        {/* 因子选择 */}
        <Space wrap>
          <Select
            value={scene.visual_style}
            onChange={(v) => onUpdate(scene.id, { visual_style: v })}
            style={{ width: 120 }}
          >
            {FACTOR_OPTIONS.visual_style.map((f) => (
              <Option key={f.value} value={f.value}>
                {f.name}
              </Option>
            ))}
          </Select>

          <Select
            value={scene.bgm_type}
            onChange={(v) => onUpdate(scene.id, { bgm_type: v })}
            style={{ width: 120 }}
          >
            {FACTOR_OPTIONS.bgm_type.map((f) => (
              <Option key={f.value} value={f.value}>
                {f.name}
              </Option>
            ))}
          </Select>

          <Select
            value={scene.transition}
            onChange={(v) => onUpdate(scene.id, { transition: v })}
            style={{ width: 120 }}
          >
            {FACTOR_OPTIONS.transition.map((f) => (
              <Option key={f.value} value={f.value}>
                {f.name}
              </Option>
            ))}
          </Select>
        </Space>
      </Space>
    </Card>
  );
};

// ============ 主编辑器组件 ============
const ScriptGenerateEditor: React.FC = () => {
  const [scenes, setScenes] = useState<Scene[]>([
    { id: 1, order: 1, description: '产品特写开场', narration: '夏天到了，防晒可别忘了', duration: 5 },
    { id: 2, order: 2, description: '使用场景展示', narration: '这款喷雾轻薄不油腻', duration: 6 },
    { id: 3, order: 3, description: '效果展示+收尾', narration: '点击下方小黄车抢购吧', duration: 4 },
  ]);

  const [nextId, setNextId] = useState(4);

  // 更新分镜
  const updateScene = useCallback((id: number, updates: Partial<Scene>) => {
    setScenes((prev) => prev.map((s) => (s.id === id ? { ...s, ...updates } : s)));
  }, []);

  // 删除分镜
  const deleteScene = useCallback((id: number) => {
    if (scenes.length <= 1) {
      message.warning('至少保留一个分镜');
      return;
    }
    setScenes((prev) => {
      const filtered = prev.filter((s) => s.id !== id);
      return filtered.map((s, i) => ({ ...s, order: i + 1 }));
    });
    message.success('已删除分镜');
  }, [scenes.length]);

  // 上移分镜
  const moveUp = useCallback((id: number) => {
    setScenes((prev) => {
      const idx = prev.findIndex((s) => s.id === id);
      if (idx <= 0) return prev;
      const arr = [...prev];
      [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]];
      return arr.map((s, i) => ({ ...s, order: i + 1 }));
    });
  }, []);

  // 下移分镜
  const moveDown = useCallback((id: number) => {
    setScenes((prev) => {
      const idx = prev.findIndex((s) => s.id === id);
      if (idx >= prev.length - 1) return prev;
      const arr = [...prev];
      [arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]];
      return arr.map((s, i) => ({ ...s, order: i + 1 }));
    });
  }, []);

  // 插入新分镜
  const addScene = useCallback(() => {
    const newScene: Scene = {
      ...DEFAULT_SCENE,
      id: nextId,
      order: scenes.length + 1,
    };
    setScenes((prev) => [...prev, newScene]);
    setNextId((prev) => prev + 1);
    message.success('已添加新分镜');
  }, [nextId, scenes.length]);

  // 保存
  const handleSave = useCallback(() => {
    console.log('保存剧本:', scenes);
    message.success('剧本已保存');
  }, [scenes]);

  // 计算总时长
  const totalDuration = scenes.reduce((sum, s) => sum + s.duration, 0);

  return (
    <div style={{ padding: 24 }}>
      {/* 头部 */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3}>
            <SwapOutlined style={{ marginRight: 8 }} />
            分镜编辑器
          </Title>
          <Text type="secondary">
            共 {scenes.length} 个分镜 · 总时长 {totalDuration} 秒
          </Text>
        </div>
        <Space>
          <Button icon={<PlusOutlined />} onClick={addScene} type="default">
            添加分镜
          </Button>
          <Button icon={<SaveOutlined />} onClick={handleSave} type="primary">
            保存剧本
          </Button>
        </Space>
      </div>

      <Divider />

      {/* 时间轴 */}
      <div style={{ display: 'flex' }}>
        {/* 左侧时间轴线 */}
        <div style={{ width: 40, position: 'relative' }}>
          <div
            style={{
              position: 'absolute',
              left: 16,
              top: 0,
              bottom: 0,
              width: 2,
              background: 'linear-gradient(to bottom, #1890ff, #52c41a)',
            }}
          />
        </div>

        {/* 分镜列表 */}
        <div style={{ flex: 1 }}>
          {scenes.map((scene, index) => (
            <SceneCard
              key={scene.id}
              scene={scene}
              index={index}
              total={scenes.length}
              onUpdate={updateScene}
              onDelete={deleteScene}
              onMoveUp={moveUp}
              onMoveDown={moveDown}
            />
          ))}
        </div>
      </div>

      {/* 底部提示 */}
      <Card size="small" style={{ marginTop: 24 }}>
        <Text type="secondary">💡 提示：点击上下箭头调整顺序，因子下拉框可以快速替换画面风格、BGM、转场效果</Text>
      </Card>
    </div>
  );
};

export default ScriptGenerateEditor;
