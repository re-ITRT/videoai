"""模型层测试 — 覆盖所有 ORM 模型定义"""


class TestAuthModels:
    """app.auth.models"""

    def test_user_model(self):
        from app.auth.models import User
        u = User(username="test", hashed_password="hash", is_active=True, role="user")
        assert u.username == "test"
        assert u.is_active is True
        assert u.role == "user"


class TestMaterialModels:
    """app.material.models"""

    def test_product_model(self):
        from app.material.models import Product
        p = Product(name="测试产品", user_id=1, category="电子产品", status="draft")
        assert p.name == "测试产品"
        assert p.status == "draft"

    def test_material_model(self):
        from app.material.models import Material
        m = Material(user_id="user1", material_type="product", input_type="image")
        assert m.material_type == "product"
        assert m.input_type == "image"

    def test_material_slice_model(self):
        from app.material.models import MaterialSlice
        ms = MaterialSlice(material_id=1, slice_type="video_scene")
        assert ms.slice_type == "video_scene"


class TestCreationModels:
    """app.creation.models"""

    def test_video_task_model(self):
        from app.creation.models import VideoTask
        vt = VideoTask(
            user_id=1, product_info={"name": "test"}, auto_mode=True,
            status="CREATED", aspect_ratio="9:16", retry_count=0, script_id=1
        )
        assert vt.status == "CREATED"
        assert vt.aspect_ratio == "9:16"
        assert vt.auto_mode is True

    def test_task_log_model(self):
        from app.creation.models import TaskLog
        tl = TaskLog(task_id=1, step="script", status="completed", model_used="gpt4",
                     input_data={}, output_data={})
        assert tl.step == "script"


class TestScriptModels:
    """app.script.models"""

    def test_script_model(self):
        from app.script.models import Script
        s = Script(task_id=1, content={"scenes": []}, strategy="promotional", version=1)
        assert s.strategy == "promotional"

    def test_inspiration_template_model(self):
        from app.script.models import InspirationTemplate
        it = InspirationTemplate(
            user_id="user1", name="展示型", strategy="开场3秒展示产品",
            category="product_show", tags=[]
        )
        assert it.name == "展示型"

    def test_reference_video_model(self):
        from app.script.models import ReferenceVideo
        rv = ReferenceVideo(
            user_id="user1", title="爆款样例", source_url="https://example.com/v.mp4"
        )
        assert rv.title == "爆款样例"
