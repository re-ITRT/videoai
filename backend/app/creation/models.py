from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class VideoTask(Base):
    __tablename__ = "video_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), nullable=False, default="CREATED")
    auto_mode = Column(Boolean, default=True)
    product_info = Column(JSONB, nullable=False)
    style = Column(String(64))
    duration = Column(Integer)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    audio_url = Column(Text)
    video_urls = Column(JSONB, default=[])
    output_url = Column(Text)
    target_languages = Column(JSONB, default=[])  # 多语种目标语言列表
    tts_results = Column(JSONB, default={})  # 多语种TTS结果: {lang: {audio_url, scene_audios}}
    aspect_ratio = Column(String(8), default="9:16")  # 9:16 / 16:9
    error_msg = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskLog(Base):
    """生成过程追踪"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("video_tasks.id"), nullable=False)
    step = Column(String(32), nullable=False)  # material_embed / query_generate / ...
    status = Column(String(16), nullable=False)  # started / completed / failed
    duration_ms = Column(Integer)
    model_used = Column(String(64))
    tokens_consumed = Column(Integer)
    input_data = Column(JSONB, default={})
    output_data = Column(JSONB, default={})
    error_msg = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VideoMetric(Base):
    """视频效果归因指标"""
    __tablename__ = "video_metrics"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("video_tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(32), nullable=False)  # tiktok / fb / ins / douyin
    video_url = Column(Text)
    publish_date = Column(DateTime)
    region = Column(String(64))  # 地区
    audience_tag = Column(String(64))  # 人群标签

    # 播放指标
    impressions = Column(Integer, default=0)  # 曝光量
    views = Column(Integer, default=0)  # 播放量
    play_rate = Column(Numeric(5,2), default=0)  # 播放率 = 播放/曝光
    completion_rate = Column(Numeric(5,2), default=0)  # 完播率
    avg_play_duration = Column(Numeric(8,2), default=0)  # 平均播放时长(秒)
    drop_rate = Column(Numeric(5,2), default=0)  # 3秒跳出率

    # 互动指标
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    favorites = Column(Integer, default=0)
    profile_clicks = Column(Integer, default=0)

    # 转化指标
    product_clicks = Column(Integer, default=0)  # 商品点击
    add_to_cart = Column(Integer, default=0)  # 加购
    orders = Column(Integer, default=0)  # 下单
    gmv = Column(Numeric(12,2), default=0)  # 成交金额
    cost = Column(Numeric(12,2), default=0)  # 投放成本
    roi = Column(Numeric(8,2), default=0)  # ROI

    # 关联素材
    material_ids = Column(JSONB, default=[])  # 使用的素材ID列表
    template_id = Column(Integer, ForeignKey("inspiration_templates.id"))  # 使用的模板

    extra = Column(JSONB, default={})  # 扩展字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AttributionLog(Base):
    """归因日志，细粒度事件追踪"""
    __tablename__ = "attribution_logs"

    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(Integer, ForeignKey("video_metrics.id"))
    event_type = Column(String(32), nullable=False)  # view / click / add_cart / order
    event_time = Column(DateTime, nullable=False)
    user_identifier = Column(String(128))  # 设备ID/用户标识
    source_channel = Column(String(64))
    extra = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
