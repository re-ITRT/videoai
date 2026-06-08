"""数据归因模块路由"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.creation.models import VideoTask, VideoMetric
from typing import Optional

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/overview")
async def get_overview(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """数据概览"""
    query = select(
        func.sum(VideoMetric.views).label("total_views"),
        func.sum(VideoMetric.impressions).label("total_impressions"),
        func.sum(VideoMetric.gmv).label("total_gmv"),
        func.sum(VideoMetric.cost).label("total_cost"),
        func.count(VideoMetric.id).label("video_count"),
        func.avg(VideoMetric.completion_rate).label("avg_completion_rate"),
    ).where(VideoMetric.user_id == current_user.id)

    if start_date:
        query = query.where(VideoMetric.publish_date >= start_date)
    if end_date:
        query = query.where(VideoMetric.publish_date <= end_date)
    if platform:
        query = query.where(VideoMetric.platform == platform)

    result = await db.execute(query)
    row = result.first()

    total_views = row.total_views or 0
    total_impressions = row.total_impressions or 0
    total_gmv = float(row.total_gmv or 0)
    total_cost = float(row.total_cost or 0)
    video_count = row.video_count or 0
    avg_completion_rate = float(row.avg_completion_rate or 0)

    # 计算整体ROI
    overall_roi = round(total_gmv / total_cost, 2) if total_cost > 0 else 0
    # 互动率
    interaction_rate = 0  # 后续完善

    return {
        "total_views": int(total_views),
        "total_impressions": int(total_impressions),
        "total_gmv": total_gmv,
        "total_cost": total_cost,
        "overall_roi": overall_roi,
        "video_count": int(video_count),
        "avg_completion_rate": avg_completion_rate,
    }


@router.get("/trend")
async def get_trend(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    dimension: str = Query("day", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """趋势数据"""
    # 按时间维度分组
    if dimension == "day":
        date_func = func.date(VideoMetric.publish_date)  # pragma: no cover
    elif dimension == "week":
        date_func = func.date_trunc('week', VideoMetric.publish_date)  # pragma: no cover
    else:  # month
        date_func = func.date_trunc('month', VideoMetric.publish_date)  # pragma: no cover

    query = select(
        date_func.label("date"),
        func.sum(VideoMetric.views).label("views"),
        func.sum(VideoMetric.gmv).label("gmv"),
        func.sum(VideoMetric.cost).label("cost"),
        func.sum(VideoMetric.orders).label("orders"),
    ).where(VideoMetric.user_id == current_user.id)

    if start_date:
        query = query.where(VideoMetric.publish_date >= start_date)
    if end_date:
        query = query.where(VideoMetric.publish_date <= end_date)

    query = query.group_by("date").order_by("date")

    result = await db.execute(query)
    rows = result.all()

    trend_data = []
    for row in rows:
        gmv = float(row.gmv or 0)
        cost = float(row.cost or 0)
        roi = round(gmv / cost, 2) if cost > 0 else 0
        trend_data.append({
            "date": str(row.date)[:10],
            "views": int(row.views or 0),
            "gmv": gmv,
            "orders": int(row.orders or 0),
            "roi": roi,
        })

    return trend_data


@router.get("/aggregate")
async def get_aggregate(
    by: str = Query("platform", regex="^(platform|region|template|material)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """维度聚合数据"""
    # 选择聚合维度
    if by == "platform":
        dim_col = VideoMetric.platform
    elif by == "region":
        dim_col = VideoMetric.region
    elif by == "template":
        dim_col = VideoMetric.template_id
    else:  # material - 需要JSON数组处理，暂简化
        dim_col = VideoMetric.material_ids  # pragma: no cover

    query = select(
        dim_col.label("dimension"),
        func.sum(VideoMetric.views).label("views"),
        func.sum(VideoMetric.gmv).label("gmv"),
        func.sum(VideoMetric.cost).label("cost"),
        func.count(VideoMetric.id).label("video_count"),
    ).where(VideoMetric.user_id == current_user.id)

    if start_date:
        query = query.where(VideoMetric.publish_date >= start_date)
    if end_date:
        query = query.where(VideoMetric.publish_date <= end_date)

    query = query.group_by("dimension").order_by(func.sum(VideoMetric.gmv).desc()).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    aggregate_data = []
    for row in rows:
        gmv = float(row.gmv or 0)
        cost = float(row.cost or 0)
        roi = round(gmv / cost, 2) if cost > 0 else 0
        aggregate_data.append({
            "dimension": row.dimension,
            "views": int(row.views or 0),
            "gmv": gmv,
            "roi": roi,
            "video_count": int(row.video_count or 0),
        })

    return aggregate_data


@router.get("/funnel")
async def get_funnel(
    task_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """转化漏斗数据"""
    query = select(
        func.sum(VideoMetric.impressions).label("impressions"),
        func.sum(VideoMetric.views).label("views"),
        func.sum(VideoMetric.product_clicks).label("product_clicks"),
        func.sum(VideoMetric.add_to_cart).label("add_to_cart"),
        func.sum(VideoMetric.orders).label("orders"),
    ).where(VideoMetric.user_id == current_user.id)

    if task_id:
        query = query.where(VideoMetric.task_id == task_id)
    if start_date:
        query = query.where(VideoMetric.publish_date >= start_date)
    if end_date:
        query = query.where(VideoMetric.publish_date <= end_date)

    result = await db.execute(query)
    row = result.first()

    return [
        {"name": "曝光", "value": int(row.impressions or 0)},
        {"name": "播放", "value": int(row.views or 0)},
        {"name": "商品点击", "value": int(row.product_clicks or 0)},
        {"name": "加购", "value": int(row.add_to_cart or 0)},
        {"name": "下单", "value": int(row.orders or 0)},
    ]


@router.get("")
async def list_metrics(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    platform: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """视频指标列表"""
    query = select(VideoMetric).where(VideoMetric.user_id == current_user.id)

    if platform:
        query = query.where(VideoMetric.platform == platform)
    if start_date:
        query = query.where(VideoMetric.publish_date >= start_date)
    if end_date:
        query = query.where(VideoMetric.publish_date <= end_date)

    query = query.order_by(VideoMetric.publish_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    metrics = result.scalars().all()

    return [
        {
            "id": m.id,
            "task_id": m.task_id,
            "platform": m.platform,
            "video_url": m.video_url,
            "publish_date": m.publish_date,
            "region": m.region,
            "impressions": m.impressions,
            "views": m.views,
            "completion_rate": float(m.completion_rate or 0),
            "likes": m.likes,
            "comments": m.comments,
            "shares": m.shares,
            "product_clicks": m.product_clicks,
            "orders": m.orders,
            "gmv": float(m.gmv or 0),
            "cost": float(m.cost or 0),
            "roi": float(m.roi or 0),
        }
        for m in metrics
    ]


@router.post("")
async def create_metric(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上报视频指标"""
    metric = VideoMetric(
        user_id=current_user.id,
        task_id=data.get("task_id"),
        platform=data.get("platform"),
        video_url=data.get("video_url"),
        publish_date=data.get("publish_date"),
        region=data.get("region"),
        audience_tag=data.get("audience_tag"),
        impressions=data.get("impressions", 0),
        views=data.get("views", 0),
        completion_rate=data.get("completion_rate", 0),
        likes=data.get("likes", 0),
        comments=data.get("comments", 0),
        shares=data.get("shares", 0),
        product_clicks=data.get("product_clicks", 0),
        add_to_cart=data.get("add_to_cart", 0),
        orders=data.get("orders", 0),
        gmv=data.get("gmv", 0),
        cost=data.get("cost", 0),
        roi=data.get("roi", 0),
        material_ids=data.get("material_ids", []),
        template_id=data.get("template_id"),
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return {"id": metric.id}
