"""素材模块业务层"""
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.material.models import Material, MaterialSlice, Product


# ── Product ───────────────────────────────

async def create_product(db: AsyncSession, user_id: int, name: str, category: str | None = None) -> Product:
    product = Product(user_id=user_id, name=name, category=category)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_products(db: AsyncSession, user_id: int) -> list[Product]:
    result = await db.execute(select(Product).where(Product.user_id == user_id).order_by(Product.id))
    return list(result.scalars().all())


# ── Material ──────────────────────────────

async def create_material(
    db: AsyncSession,
    user_id: str,
    material_type: str,
    input_type: str,
    product_id: int | None = None,
    image_url: str | None = None,
    text_content: str | None = None,
    source: str | None = "upload",
) -> Material:
    material = Material(
        user_id=user_id,
        material_type=material_type,
        input_type=input_type,
        product_id=product_id,
        image_url=image_url,
        text_content=text_content,
        source=source,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


async def get_material(db: AsyncSession, material_id: int) -> Material | None:
    result = await db.execute(select(Material).where(Material.id == material_id))
    return result.scalar_one_or_none()


async def list_materials(
    db: AsyncSession,
    user_id: str,
    material_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Material]:
    query = select(Material).where(Material.user_id == user_id)
    if material_type:
        query = query.where(Material.material_type == material_type)
    query = query.order_by(Material.id.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_material(db: AsyncSession, material_id: int) -> bool:
    material = await get_material(db, material_id)
    if not material:
        return False
    # 级联删除切片
    await db.execute(sa_delete(MaterialSlice).where(MaterialSlice.material_id == material_id))
    await db.delete(material)
    await db.commit()
    return True


# ── MaterialSlice ─────────────────────────

async def create_slice(
    db: AsyncSession,
    material_id: int,
    slice_type: str,
    scene_id: int | None = None,
    time_range: str | None = None,
    description: str | None = None,
    image_url: str | None = None,
) -> MaterialSlice:
    slice_ = MaterialSlice(
        material_id=material_id,
        slice_type=slice_type,
        scene_id=scene_id,
        time_range=time_range,
        description=description,
        image_url=image_url,
    )
    db.add(slice_)
    await db.commit()
    await db.refresh(slice_)
    return slice_


async def list_slices(db: AsyncSession, material_id: int, slice_type: str | None = None) -> list[MaterialSlice]:
    query = select(MaterialSlice).where(MaterialSlice.material_id == material_id)
    if slice_type:
        query = query.where(MaterialSlice.slice_type == slice_type)
    query = query.order_by(MaterialSlice.scene_id, MaterialSlice.id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_video_slices(
    db: AsyncSession,
    material_id: int,
    scene_count: int = 3,
) -> list[MaterialSlice]:
    """视频入库时自动创建默认切片（后续可由 material-embed 工作流细化）"""
    slices = []
    for i in range(scene_count):
        s = MaterialSlice(
            material_id=material_id,
            slice_type="video_scene",
            scene_id=i + 1,
            time_range=f"{i * 5}s-{(i + 1) * 5}s",
            description=f"场景 {i + 1}",
        )
        db.add(s)
        slices.append(s)
    await db.commit()
    for s in slices:
        await db.refresh(s)
    return slices
