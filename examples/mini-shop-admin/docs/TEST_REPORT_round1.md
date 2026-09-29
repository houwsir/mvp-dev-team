# 测试报告

- 结论：**❌ 未通过**
- 概述：质量门不通过：pytest 有 4 个失败用例，订单搜索、发货、取消及商品搜索主流程存在后端缺陷；静态体检另报告 1 个 frontend high 缺陷。后端与前端均需返工。

## 已执行的校验

- [x] 核对所提供的 pytest 原始执行结果：共显示 28 个用例进度，其中 4 个失败、其余通过
- [x] 核对订单接口失败用例：精确搜索与分页、待发货订单发货、待付款订单取消
- [x] 核对商品接口失败用例：关键词搜索、状态筛选与分页
- [x] 核对确定性静态体检结果：共 3 项，其中 high 1 项、medium 2 项
- [x] 核对体检原始事实中的后端 API 声明、后端 API 实现、前端路由、前端调用路径和缺失交付文件

## 缺陷清单

| 严重度 | 位置 | 问题 | 建议修复 |
| --- | --- | --- | --- |
| high | `frontend` | PRD 要求但未找到对应路由的页面：['/products/new 和 /products/:id/edit'] | 在路由表中注册这些页面 |
| medium | `frontend/api` | 前端调用的路径未在后端找到实现：['/orders)}', '/products)}'] | 对齐 API 契约中的路径 |
| medium | `交付清单` | 2 个声明文件未产出：['frontend/src/test/pages.test.tsx', 'frontend/e2e/admin-flow.spec.ts'] | 补齐缺失文件 |

## 风险

- pytest 当前未通过，订单与商品管理核心流程不具备放行条件。
- 发货和取消接口出现状态已改变但关联数据或历史记录未同步的情况，存在持久化一致性和审计完整性风险。
- pytest 输出包含 datetime.utcnow() 弃用警告，来源为 backend/app/models.py:20；升级 Python 或依赖后可能失效，应迁移到具备 UTC 时区信息的 datetime.now(datetime.UTC)。
- Starlette TestClient 使用已弃用的 anyio.abc.BlockingPortal 别名，未来依赖升级可能导致测试基础设施兼容性问题。
- 静态体检的 high 路由结论与 frontend_routes 原始清单矛盾，需要通过运行时路由测试确认真实状态，但依照本轮规则仍必须阻断。
- 缺少前端自动化测试文件和 test/e2e 脚本，前端主流程仍有较大未验证范围。

## 需要返工

`both`

## 自动化测试原始输出

```text
..........F.F..F......F.....                                             [100%]
=================================== FAILURES ===================================
________________ test_order_exact_search_pagination_and_detail _________________

authenticated_client = <starlette.testclient.TestClient object at 0x10e018380>

    def test_order_exact_search_pagination_and_detail(
        authenticated_client: TestClient,
    ) -> None:
        order = find_order(authenticated_client, "pending_shipment")
    
        search = authenticated_client.get(
            "/api/orders",
            params={
                "page": 1,
                "page_size": 20,
                "order_no": f"  {order['order_no']}  ",
                "status": "pending_shipment",
            },
        )
    
>       assert search.status_code == 200
E       assert 422 == 200
E        +  where 422 = <Response [422 Unprocessable Entity]>.status_code

tests/test_orders.py:27: AssertionError
___________________________ test_ship_pending_order ____________________________

authenticated_client = <starlette.testclient.TestClient object at 0x10dfd3240>

    def test_ship_pending_order(
        authenticated_client: TestClient,
    ) -> None:
        order = find_order(authenticated_client, "pending_shipment")
    
        response = authenticated_client.post(
            f"/api/orders/{order['id']}/ship",
            json={
                "logistics_company": " 顺丰速运 ",
                "tracking_no": " SF123456789 ",
            },
        )
    
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "shipped"
>       assert body["shipment"]["logistics_company"] == "顺丰速运"
E       TypeError: 'NoneType' object is not subscriptable

tests/test_orders.py:71: TypeError
______________________ test_cancel_pending_payment_order _______________________

authenticated_client = <starlette.testclient.TestClient object at 0x10dfd2f10>

    def test_cancel_pending_payment_order(
        authenticated_client: TestClient,
    ) -> None:
        order = find_order(authenticated_client, "pending_payment")
    
        response = authenticated_client.post(
            f"/api/orders/{order['id']}/cancel",
            json={},
        )
    
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
>       assert response.json()["status_history"][-1]["event_type"] == "cancelled"
E       AssertionError: assert 'created' == 'cancelled'
E         
E         - cancelled
E         + created

tests/test_orders.py:140: AssertionError
_______________ test_product_search_status_filter_and_pagination _______________

authenticated_client = <starlette.testclient.TestClient object at 0x10dfd2ad0>
product_payload = {'description': '由 pytest 创建的商品', 'main_image_url': 'https://example.com/product.jpg', 'name': '自动化测试商品', 'price': '99.90', ...}

    def test_product_search_status_filter_and_pagination(
        authenticated_client: TestClient,
        product_payload: dict,
    ) -> None:
        created = create_product(
            authenticated_client,
            {**product_payload, "name": "唯一搜索词测试商品"},
        )
    
        activated = authenticated_client.patch(
            f"/api/products/{created['id']}/status",
            json={"status": "active"},
        )
        assert activated.status_code == 200
    
        response = authenticated_client.get(
            "/api/products",
            params={
                "page": 1,
                "page_size": 20,
                "keyword": "  唯一搜索词  ",
                "status": "active",
            },
        )
    
>       assert response.status_code == 200
E       assert 422 == 200
E        +  where 422 = <Response [422 Unprocessable Entity]>.status_code

tests/test_products.py:82: AssertionError
=============================== warnings summary ===============================
../../../../../../../.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages/starlette/testclient.py:40
  /Users/hw/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

tests/test_auth.py: 20 warnings
tests/test_consumer_field_isolation.py: 13 warnings
tests/test_health.py: 4 warnings
tests/test_orders.py: 66 warnings
tests/test_products.py: 57 warnings
  /Users/hw/passer/workbuddy-ws/工作流/mvp-dev-team/generated/mini-shop-admin/backend/app/models.py:20: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    return datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_orders.py::test_order_exact_search_pagination_and_detail - ...
FAILED tests/test_orders.py::test_ship_pending_order - TypeError: 'NoneType' ...
FAILED tests/test_orders.py::test_cancel_pending_payment_order - AssertionErr...
FAILED tests/test_products.py::test_product_search_status_filter_and_pagination
```
