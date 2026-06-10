"""
第 11 课：完整 CRUD API

学习要点：
1. CRUD = Create/Read/Update/Delete，对应 POST/GET/PUT+PATCH/DELETE
2. PUT 全量替换，PATCH 部分更新（exclude_unset=True 只更新传入的字段）
3. get_or_404 封装：查到返回，查不到抛 404，避免重复代码
4. 软删除：标记 is_deleted=True，数据不真正删除，可恢复
5. Query 参数可以加 ge/le 约束限制分页参数的合法范围
"""

from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from pydantic import BaseModel, Field

SQLALCHEMY_DATABASE_URL = "sqlite:///./products.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)  # 软删除标志


Base.metadata.create_all(bind=engine)


# ── Pydantic Schemas ──

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(gt=0)
    stock: int = Field(ge=0, default=0)


# PATCH 用：所有字段都是 Optional，客户端只传需要改的字段
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)


class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock: int

    class Config:
        from_attributes = True


app = FastAPI(title="Product CRUD API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 公共工具函数：查不到直接抛 404，避免在每个路由里重复写
def get_product_or_404(product_id: int, db: Session) -> ProductModel:
    product = db.query(ProductModel).filter(
        ProductModel.id == product_id,
        ProductModel.is_deleted == False
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


# ── C: Create ──
@app.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# ── R: Read (list) ──
@app.get("/products", response_model=list[ProductResponse])
def list_products(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="每页最多100条"),
    name: Optional[str] = Query(None, description="按名称过滤（模糊匹配）"),
    db: Session = Depends(get_db),
):
    query = db.query(ProductModel).filter(ProductModel.is_deleted == False)
    if name:
        # ilike：不区分大小写的模糊匹配
        query = query.filter(ProductModel.name.ilike(f"%{name}%"))
    return query.offset(skip).limit(limit).all()


# ── R: Read (single) ──
@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return get_product_or_404(product_id, db)


# ── U: Update（全量替换 PUT）──
@app.put("/products/{product_id}", response_model=ProductResponse)
def replace_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = get_product_or_404(product_id, db)
    for key, value in product.model_dump().items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product


# ── U: Partial Update（部分更新 PATCH）──
@app.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = get_product_or_404(product_id, db)
    # exclude_unset=True：只拿客户端实际传入的字段，不传的字段保持原值
    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product


# ── D: Delete（软删除）──
@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = get_product_or_404(product_id, db)
    # 软删除：标记删除而不是真的 DELETE，数据可恢复，历史可追溯
    db_product.is_deleted = True
    db.commit()


"""
CRUD 路由总览
=============

POST   /products          → 创建商品（201）
GET    /products          → 列表（支持分页 + 名称过滤）
GET    /products/{id}     → 获取单个（404 if not found）
PUT    /products/{id}     → 全量替换（所有字段必传）
PATCH  /products/{id}     → 部分更新（只传要改的字段）
DELETE /products/{id}     → 软删除（204 No Content）

PUT vs PATCH 区别：
    PUT:   {"name":"New","price":99,"stock":10}  → 全部替换
    PATCH: {"price":99}                          → 只改 price，其他字段不变


核心知识点 ★
============
★ PUT vs PATCH：PUT 需要完整对象，PATCH 只传变化的字段
★ exclude_unset=True 是 PATCH 的关键：区分"没传"和"传了 null"
★ 软删除比硬删除更安全：数据不丢，可以恢复，支持审计
★ Query(ge=0, le=100) 对分页参数加边界限制，防止滥用
★ 公共 get_or_404 函数：减少重复代码，统一错误格式
"""
