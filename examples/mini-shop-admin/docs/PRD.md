# 产品需求文档（PRD）

> 产品定位：面向小型电商运营人员的商品与订单一体化管理后台。

## 1. 概述

mini-shop-admin 是面向小程序商城店主和运营人员的桌面端管理后台。MVP 提供管理员登录、商品维护与上下架、订单检索与详情查看、订单发货、订单取消和内部备注能力，形成“登录后台 → 维护商品 → 查询订单 → 处理发货或异常订单”的运营闭环。系统采用单管理员角色、单商品单库存模型；金额统一以 decimal(10,2) 存储，时间统一存储为 UTC 并在前端按本地时区展示。所有管理页面均需会话鉴权，未登录或会话失效时跳转至 /login。订单由初始化数据或消费者端外部系统写入，本 MVP 不提供后台创建订单功能。

## 2. 用户故事

| 编号 | 角色 | 诉求 | 价值 | 优先级 |
| --- | --- | --- | --- | --- |
| US-001 | 商城管理员 | 使用账号密码登录后台并安全退出 | 只有经过认证的人员能够访问商品和订单数据 | P0 |
| US-002 | 商品运营人员 | 创建、搜索、筛选和编辑商品，并调整价格与库存 | 商城展示的商品资料和可售库存保持准确 | P0 |
| US-003 | 商品运营人员 | 控制商品的上架和下架状态 | 我可以决定商品是否允许在消费者端销售，并避免零库存商品被上架 | P0 |
| US-004 | 订单运营人员 | 按完整订单号或订单状态查找订单并查看完整详情 | 我可以快速确认订单商品、金额、收货信息和处理进度 | P0 |
| US-005 | 订单运营人员 | 为待发货订单录入物流信息并发货，或取消符合条件的异常订单 | 订单能够按照明确的状态规则完成履约或终止 | P0 |
| US-006 | 订单运营人员 | 为订单保存仅后台可见的内部备注 | 运营人员可以记录订单处理信息且不会泄露给消费者 | P1 |

## 3. 功能清单

| 编号 | 功能 | 说明 | 使用角色 | 优先级 |
| --- | --- | --- | --- | --- |
| F-001 | 管理员认证与会话保护 | 支持管理员使用账号和密码登录、主动退出及管理路由鉴权。账号不存在、密码错误或账号被禁用时显示明确错误且不得创建会话；退出后立即使当前会话失效；未登录或会话失效访问 /products、/products/new、/products/:id/edit、/orders、/orders/:id 时跳转 /login。登录成功默认进入 /products。 | 商城管理员 | P0 |
| F-002 | 商品分页搜索与筛选 | 在商品列表分页展示主图、名称、售价、库存、上下架状态和更新时间。支持按商品名称模糊搜索、按 active 或 inactive 状态筛选；搜索词去除首尾空格；默认按 updated_at 倒序；默认 page=1、page_size=20，可选 20、50；切换搜索或筛选条件时回到第 1 页；无数据、加载中和接口失败分别展示对应状态。 | 商品运营 | P0 |
| F-003 | 商品创建与编辑 | 支持创建商品和编辑已有商品的名称、主图 URL、售价、库存及描述。name 和 main_image_url 必填；price 必须大于 0 且最多两位小数；stock 必须为大于等于 0 的整数；description 可为空。新商品默认下架。客户端与服务端均执行校验，字段错误就近显示；保存期间禁止重复提交；保存成功返回商品列表，重新打开可见最新数据；接口失败时保留表单输入、显示失败提示且不得展示未持久化结果。 | 商品运营 | P0 |
| F-004 | 商品库存与上下架管理 | 支持在商品列表中快速修改库存并执行上架或下架。库存只能保存为大于等于 0 的整数；库存为 0 时禁止上架并显示“库存为 0，无法上架”；已上架商品库存调整为 0 后自动变为下架；状态或库存更新成功后同步刷新列表数据，失败时恢复服务端原值并显示错误。 | 商品运营 | P0 |
| F-005 | 订单分页搜索与筛选 | 分页展示订单号、下单时间、买家名称、订单金额和订单状态。支持按完整订单号精确搜索及按 pending_payment、pending_shipment、shipped、completed、cancelled 状态筛选；默认按 placed_at 倒序；默认 page=1、page_size=20，可选 20、50；搜索词去除首尾空格；切换条件时回到第 1 页；无匹配结果时显示空状态。 | 订单运营 | P0 |
| F-006 | 订单详情与状态记录 | 展示订单号、当前状态、下单时间、商品明细、商品金额、运费、实付金额、收货人姓名、手机号、完整地址、买家留言、内部备注、物流信息及按时间升序排列的状态记录。订单商品名称、图片和单价使用下单快照，不随商品后续编辑变化。数据加载失败时显示重试入口，不展示残缺详情。 | 订单运营 | P0 |
| F-007 | 订单发货 | 仅 pending_shipment 订单显示发货操作。物流公司和运单号均为去除首尾空格后的非空字符串；提交成功后订单状态变为 shipped，保存物流信息，并新增一条 event_type=shipped、包含操作时间和管理员标识的状态记录；提交失败时保持 pending_shipment 状态和原详情，不新增状态记录。 | 订单运营 | P0 |
| F-008 | 订单取消 | 仅 pending_payment 和 pending_shipment 订单允许取消。操作前显示确认对话框；取消成功后状态变为 cancelled，并新增一条 event_type=cancelled、包含操作时间和管理员标识的状态记录。shipped、completed、cancelled 状态不显示取消按钮；服务端必须再次校验状态以避免并发越权流转。 | 订单运营 | P0 |
| F-009 | 订单内部备注 | 支持在订单详情中新增或修改内部备注，最多 1000 个字符，可清空。保存成功后刷新页面仍可见；保存失败时显示错误并保留编辑内容。internal_note 仅允许管理后台鉴权接口读写，不得映射到消费者端订单响应、买家留言或状态记录中。 | 订单运营 | P1 |

## 4. 页面清单

| 页面 | 路由 | 目的 | 关键元素 |
| --- | --- | --- | --- |
| 管理员登录 | `/login` | 完成管理员身份认证并建立后台会话。 | 账号输入框、密码输入框、登录按钮、字段必填提示、账号或密码错误提示、登录提交加载状态 |
| 商品列表 | `/products` | 查询商品并执行新增、编辑、库存调整和上下架操作。 | 后台主导航与退出入口、商品名称搜索框、上下架状态筛选器、新建商品按钮、商品分页表格、主图、名称、售价、库存、状态和更新时间列、编辑、调整库存、上架和下架操作、分页器与每页条数选择器、加载、空状态和接口错误提示、库存调整对话框 |
| 商品创建与编辑 | `/products/new 和 /products/:id/edit` | 创建新商品或修改已有商品资料；两条路由复用同一表单页面。 | 商品名称输入框、主图 URL 输入框与图片预览、售价数字输入框、库存整数输入框、商品描述文本域、字段级校验提示、保存按钮、取消并返回列表按钮、编辑模式数据加载状态、保存失败提示 |
| 订单列表 | `/orders` | 按订单号或状态定位订单并进入详情处理。 | 后台主导航与退出入口、完整订单号搜索框、订单状态筛选器、订单分页表格、订单号、下单时间、买家、订单金额和状态列、查看详情操作、分页器与每页条数选择器、加载、空状态和接口错误提示 |
| 订单详情 | `/orders/:id` | 查看订单完整信息并完成发货、取消和内部备注维护。 | 订单编号、当前状态和下单时间、商品明细表格、商品金额、运费和实付金额、收货人姓名、手机号和完整地址、买家留言、物流公司和运单号、内部备注编辑区与保存按钮、状态记录时间线、发货按钮与物流信息对话框、按状态显示的取消订单按钮、取消确认对话框、操作加载状态、成功提示和失败提示 |

## 5. 数据实体

### admin_user

后台管理员账号。MVP 仅区分启用和禁用，不实现多角色权限。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键，自增 |
| `username` | varchar(64) | 是 | 登录账号，全局唯一，去除首尾空格后存储 |
| `password_hash` | varchar(255) | 是 | 使用安全密码哈希算法生成，不存储明文密码 |
| `display_name` | varchar(64) | 是 | 后台展示名称 |
| `is_active` | boolean | 是 | 账号是否允许登录，默认 true |
| `last_login_at` | datetime | 否 | 最近一次成功登录时间 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 最后更新时间 |

### admin_session

管理员登录会话，用于鉴权、主动退出和会话过期控制。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | uuid | 是 | 会话主键 |
| `admin_user_id` | bigint | 是 | 关联 admin_user.id |
| `token_hash` | varchar(255) | 是 | 会话令牌哈希，全局唯一，不存储原始令牌 |
| `expires_at` | datetime | 是 | 会话过期时间 |
| `revoked_at` | datetime | 否 | 主动退出或服务端撤销时间 |
| `created_at` | datetime | 是 | 会话创建时间 |

### product

单规格商品及其可售库存。MVP 不拆分 SKU。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键，自增 |
| `name` | varchar(200) | 是 | 商品名称，去除首尾空格后不可为空 |
| `main_image_url` | varchar(2048) | 是 | 商品主图 URL，必须为有效的 http 或 https 地址 |
| `price` | decimal(10,2) | 是 | 商品售价，必须大于 0 |
| `stock` | integer | 是 | 可售库存，必须大于等于 0 |
| `description` | text | 否 | 商品描述，可为空 |
| `status` | enum('active','inactive') | 是 | 上下架状态，新建默认 inactive；stock=0 时不得为 active |
| `created_by` | bigint | 是 | 创建管理员，关联 admin_user.id |
| `updated_by` | bigint | 是 | 最后修改管理员，关联 admin_user.id |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 最后更新时间 |

### shop_order

订单主记录，包含下单时的买家、金额和收货信息快照。表名避免使用数据库保留字 order。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键，自增 |
| `order_no` | varchar(32) | 是 | 面向业务的订单号，全局唯一，用于精确搜索 |
| `buyer_id` | varchar(64) | 是 | 消费者系统中的买家标识 |
| `buyer_name` | varchar(100) | 是 | 下单时买家名称快照 |
| `status` | enum('pending_payment','pending_shipment','shipped','completed','cancelled') | 是 | 订单状态；允许 pending_payment→pending_shipment、pending_payment→cancelled、pending_shipment→shipped、pending_shipment→cancelled、shipped→completed |
| `items_amount` | decimal(10,2) | 是 | 商品金额合计，必须大于等于 0 |
| `shipping_fee` | decimal(10,2) | 是 | 运费，必须大于等于 0 |
| `payable_amount` | decimal(10,2) | 是 | 订单应付或实付金额，等于 items_amount 加 shipping_fee |
| `receiver_name` | varchar(100) | 是 | 收货人姓名快照 |
| `receiver_phone` | varchar(32) | 是 | 收货人手机号快照 |
| `receiver_province` | varchar(100) | 是 | 省级行政区快照 |
| `receiver_city` | varchar(100) | 是 | 城市快照 |
| `receiver_district` | varchar(100) | 是 | 区县快照 |
| `receiver_address` | varchar(500) | 是 | 详细地址快照 |
| `buyer_message` | varchar(500) | 否 | 消费者下单时留言 |
| `internal_note` | varchar(1000) | 否 | 仅后台可见的运营备注，不得包含在消费者端响应中 |
| `placed_at` | datetime | 是 | 下单时间 |
| `created_at` | datetime | 是 | 记录创建时间 |
| `updated_at` | datetime | 是 | 最后更新时间 |

### order_item

订单商品明细，保存下单时的商品信息和价格快照。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键，自增 |
| `order_id` | bigint | 是 | 关联 shop_order.id |
| `product_id` | bigint | 是 | 关联 product.id |
| `product_name` | varchar(200) | 是 | 下单时商品名称快照 |
| `product_image_url` | varchar(2048) | 是 | 下单时商品主图 URL 快照 |
| `unit_price` | decimal(10,2) | 是 | 下单时单价，必须大于 0 |
| `quantity` | integer | 是 | 购买数量，必须大于 0 |
| `line_amount` | decimal(10,2) | 是 | 明细金额，等于 unit_price 乘 quantity |
| `created_at` | datetime | 是 | 记录创建时间 |

### order_shipment

订单发货信息。MVP 每个订单最多一条发货记录，不支持拆单和多包裹。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键，自增 |
| `order_id` | bigint | 是 | 关联 shop_order.id，唯一 |
| `logistics_company` | varchar(100) | 是 | 物流公司名称，去除首尾空格后不可为空 |
| `tracking_no` | varchar(100) | 是 | 运单号，去除首尾空格后不可为空 |
| `shipped_by` | bigint | 是 | 发货管理员，关联 admin_user.id |
| `shipped_at` | datetime | 是 | 发货操作时间 |
| `created_at` | datetime | 是 | 记录创建时间 |
| `updated_at` | datetime | 是 | 最后更新时间 |

### order_status_history

订单状态变更记录，用于订单详情时间线和操作追踪。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键，自增 |
| `order_id` | bigint | 是 | 关联 shop_order.id |
| `from_status` | enum('pending_payment','pending_shipment','shipped','completed','cancelled') | 否 | 变更前状态；订单创建记录可为空 |
| `to_status` | enum('pending_payment','pending_shipment','shipped','completed','cancelled') | 是 | 变更后状态 |
| `event_type` | enum('created','payment_confirmed','shipped','completed','cancelled') | 是 | 状态事件类型 |
| `operator_type` | enum('system','admin') | 是 | 操作来源 |
| `operator_admin_id` | bigint | 否 | 管理员操作时关联 admin_user.id，系统操作时为空 |
| `event_note` | varchar(500) | 否 | 状态事件说明，不用于存储内部备注 |
| `created_at` | datetime | 是 | 状态变更时间 |

## 6. 本期不做

- 消费者端小程序页面、商品浏览、购物车及下单流程
- 后台创建订单、修改订单商品、金额或收货地址
- 在线支付、退款、售后、支付平台对账及支付回调实现
- 多规格 SKU、商品分类、商品删除、商品富文本编辑和图片上传服务
- 优惠券、满减、秒杀、会员等级和积分体系
- 多角色权限、组织架构、多管理员审批和多租户
- 供应商、采购、入库、盘点、仓库调拨、库存预占和复杂库存流水
- 拆单发货、多包裹发货、修改物流信息及自动同步第三方物流轨迹
- 批量导入商品、批量修改商品、批量发货和批量处理订单
- 数据报表、经营分析、财务结算及数据导出
- 短信、站内信、邮件及发货通知
- 移动端和小于 1280 像素桌面视口的专项适配
