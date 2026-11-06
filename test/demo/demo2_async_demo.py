"""
async / await 完整演示（纯 Python，不依赖 FastAPI）

直接运行：python3 test/demo/demo2_async_demo.py

本文件讲四件事：
    1. async 函数是什么、await 做什么
    2. 三种调用 async 函数的方式
    3. 两个常见错误（忘 await、async 里写同步阻塞）
    4. 联系 FastAPI：uvicorn 帮你开了门，路由里直接用 await
"""

import asyncio
import time

# ═══════════════════════════════════════════════════════════════
# 定义区：四种函数
# ═══════════════════════════════════════════════════════════════

def sync_func(name):
    """普通函数：一口气跑完，中间不能停，外部直接 sync_func('A') 调用"""
    print(f"  [{name}] 开始")
    time.sleep(0.5)
    print(f"  [{name}] 结束")
    return f"sync-{name}"


async def async_func(name):
    """async 函数 = 协程：可以暂停，必须用 await 调用才能真正执行"""
    print(f"  [{name}] 开始")
    await asyncio.sleep(0.5)      # await = 在这里暂停，把控制权交还给事件循环
    print(f"  [{name}] 结束")
    return f"async-{name}"


async def async_missing_await(name):
    """错误示范：async 函数里忘写 await → 协程创建了但没执行"""
    print(f"  [{name}] 开始")
    asyncio.sleep(0.5)            # ❌ 没 await，等于没写
    print(f"  [{name}] 结束")
    return f"missing-{name}"


async def async_trap(name):
    """错误示范：async 函数里写同步阻塞 → 并发失效"""
    print(f"  [{name}] 开始")
    time.sleep(0.5)               # ❌ 同步阻塞，不交出控制权
    print(f"  [{name}] 结束")
    return f"trap-{name}"


# ═══════════════════════════════════════════════════════════════
# 演示 1：三种调用 async 函数的方式
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("演示 1：三种调用 async 函数的方式")
print("=" * 60)

# ── 方式 A：asyncio.run() —— 从普通代码进入异步世界的唯一大门 ──
print("\n方式 A — asyncio.run()（脚本顶层入口）：")
t0 = time.time()
result = asyncio.run(async_func("A"))
print(f"  返回值: {result}，耗时: {time.time() - t0:.1f}s\n")
# asyncio.run 做了三件事：创建事件循环 → 跑协程 → 拿到结果 → 关闭循环
# 整个程序通常只在最外层调一次 asyncio.run()

# ── 方式 B：await —— 已经在 async 函数里，直接用 await ──
print("方式 B — await（在另一个 async 函数里调用）：")


async def caller_with_await():
    print("  caller 开始")
    result = await async_func("B")    # ✅ 直接 await，不用 asyncio.run
    print(f"  caller 拿到: {result}")
    print("  caller 结束")


asyncio.run(caller_with_await())
print()

# ── 方式 C：asyncio.gather() —— 多个协程并发跑 ──
print("方式 C — asyncio.gather()（批量并发）：")


async def caller_with_gather():
    t0 = time.time()
    results = await asyncio.gather(
        async_func("C1"),
        async_func("C2"),
        async_func("C3"),
    )
    print(f"  全部完成: {results}")
    print(f"  总耗时: {time.time() - t0:.1f}s  （三个并发，不是 3×0.5）")


asyncio.run(caller_with_gather())
print()

# ── 总结三种方式 ──
print("""三种方式总结：
    asyncio.run(x)    → 从普通脚本进入异步世界，最外层只调一次
    await x           → 已在 async 函数里，直接用 await 调用
    asyncio.gather()  → 同时跑多个协程，并发拿到结果
""")


# ═══════════════════════════════════════════════════════════════
# 演示 2：四个函数的对比测试
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("演示 2：四个函数性能对比（都用 gather 并发两个）")
print("=" * 60)


def test_sync():
    """普通函数：两个串行，0.5+0.5=1.0s"""
    t0 = time.time()
    r1 = sync_func("A")
    r2 = sync_func("B")
    print(f"  结果: {r1}, {r2}")
    print(f"  耗时: {time.time() - t0:.1f}s（串行，不可并发）\n")


async def test_async_correct():
    """正确 async：两个并发，总共 0.5s"""
    t0 = time.time()
    r1, r2 = await asyncio.gather(async_func("A"), async_func("B"))
    print(f"  结果: {r1}, {r2}")
    print(f"  耗时: {time.time() - t0:.1f}s（A await 时 B 也在跑，真并发 ✅）\n")


async def test_missing_await():
    """忘 await：瞬间结束，0s"""
    t0 = time.time()
    r1 = async_missing_await("A")   # 没 await，返回 coroutine 对象
    r2 = async_missing_await("B")
    print(f"  r1 类型: {type(r1).__name__}，r2 类型: {type(r2).__name__}")
    print(f"  耗时: {time.time() - t0:.1f}s（协程创建了但没执行 ❌）\n")


async def test_trap():
    """async + time.sleep：两个串行，0.5+0.5=1.0s"""
    t0 = time.time()
    r1, r2 = await asyncio.gather(async_trap("A"), async_trap("B"))
    print(f"  结果: {r1}, {r2}")
    print(f"  耗时: {time.time() - t0:.1f}s（async 里同步阻塞，并发失效 ❌）\n")


print("\n① 普通函数（同步串行）：")
test_sync()

print("② async + await（正确并发）：")
asyncio.run(test_async_correct())

print("③ 忘写 await（协程没执行）：")
asyncio.run(test_missing_await())

print("④ async + 同步阻塞（陷阱）：")
asyncio.run(test_trap())


# ═══════════════════════════════════════════════════════════════
# 演示 3：联系 FastAPI
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("演示 3：联系 FastAPI — uvicorn 帮你开了门")
print("=" * 60)

print("""
┌─────────────────────────────────────────────────┐
│                    谁来启动事件循环？            │
│                                                 │
│  普通脚本      → 你手动调用 asyncio.run()       │
│  FastAPI 路由  → uvicorn 已经启动了事件循环     │
│                  路由里直接用 await 就行         │
│                                                 │
│  uvicorn 额外做的事：                           │
│  ├─ def 路由     → 自动丢线程池                 │
│  ├─ async def + await → 主线程事件循环直接跑    │
│  └─ async def + time.sleep → 主线程卡死 ☠️      │
└─────────────────────────────────────────────────┘

写法对照：
    本文件                        FastAPI 路由里
    ─────────────────────        ─────────────────────
    result = asyncio.run(        @app.get("/user")
        async_func("A")          async def get_user():
    )                                data = await fetch_db()
                                     return data
                                 # ✅ 直接 await，不写 asyncio.run
""")