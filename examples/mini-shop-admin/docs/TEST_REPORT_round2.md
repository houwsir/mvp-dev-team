# 测试报告

- 结论：**❌ 未通过**
- 概述：质量门不通过：pytest 共 28 项，25 项通过、3 项失败；同时静态体检存在 1 项 frontend high 缺陷。订单与商品查询、订单取消状态历史等后端主流程存在问题，前端商品新建与编辑路由也被静态体检判定为缺失。

## 已执行的校验

- [x] 核对 pytest 原始执行结果：28 项测试中 25 项通过、3 项失败
- [x] 核对订单精确搜索、分页与详情测试结果
- [x] 核对待付款订单取消测试结果
- [x] 核对商品搜索、状态筛选与分页测试结果
- [x] 核对确定性静态体检结果及其 high 严重级别缺陷
- [x] 核对体检原始事实中的 API 声明、API 实现、PRD 路由、前端路由、前端调用、npm 脚本与依赖

## 缺陷清单

| 严重度 | 位置 | 问题 | 建议修复 |
| --- | --- | --- | --- |
| high | `frontend` | PRD 要求但未找到对应路由的页面：['/products/new 和 /products/:id/edit'] | 在路由表中注册这些页面 |

## 风险

- pytest 输出包含 Pydantic 序列化警告：main_image_url 字段期望 HttpUrl，但运行时得到 str，序列化结果可能不符合模型契约。
- Starlette TestClient 使用了已弃用的 anyio.abc.BlockingPortal 别名，未来依赖升级后可能产生兼容性问题。
- 静态体检结论与 frontend_routes 原始事实对商品新建、编辑路由的判断不一致，需要重新验证实际路由可访问性及体检规则。

## 需要返工

`both`

## 自动化测试原始输出

```text
..........F....F......F.....                                             [100%]
=================================== FAILURES ===================================
________________ test_order_exact_search_pagination_and_detail _________________

authenticated_client = <starlette.testclient.TestClient object at 0x10d149ae0>

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
______________________ test_cancel_pending_payment_order _______________________

authenticated_client = <starlette.testclient.TestClient object at 0x10d14af10>

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

authenticated_client = <starlette.testclient.TestClient object at 0x10d1497b0>
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
../../../../../../../.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages/starlette/testclient.py:37
  /Users/hw/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages/starlette/testclient.py:37: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

tests/test_products.py::test_create_and_get_product
tests/test_products.py::test_update_product_persists_changes
tests/test_products.py::test_product_search_status_filter_and_pagination
tests/test_products.py::test_update_stock_to_zero_automatically_deactivates_product
tests/test_products.py::test_zero_stock_product_cannot_be_activated
  /Users/hw/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages/pydantic/main.py:463: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `<class 'pydantic.networks.HttpUrl'>` but got `<class 'str'>` with value `'https://example.com/product.jpg'` - serialized value may not be as expected.)
    return self.__pydantic_serializer__.to_python(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_orders.py::test_order_exact_search_pagination_and_detail - ...
FAILED tests/test_orders.py::test_cancel_pending_payment_order - AssertionErr...
FAILED tests/test_products.py::test_product_search_status_filter_and_pagination
```
