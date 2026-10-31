# API 文档

## 基本信息

| 项目 | 值 |
|---|---|
| API 根地址 | `http://127.0.0.1:8000/api/v1` |
| 认证方式 | `Authorization: Bearer <access_token>` |
| 请求类型 | JSON；文件上传使用 `multipart/form-data` |
| OpenAPI | `http://127.0.0.1:8000/openapi` |
| Swagger | `http://127.0.0.1:8000/docs` |
| Redoc | `http://127.0.0.1:8000/redoc` |

## 统一响应

```json
{
  "code": 200,
  "msg": "请求成功",
  "data": {}
}
```

无数据成功响应：

```json
{
  "code": 200,
  "msg": "请求成功",
  "data": null
}
```

失败响应：

```json
{
  "code": 400,
  "msg": "请求参数错误",
  "data": null,
  "trace_id": "c0f6f80a5db44d8d87b6beb9d3d30d6d"
}
```

## ID 类型

响应中的 `id`、`*_id`、`ids`、`*_ids` 会转换为字符串，避免雪花 ID 在 JavaScript 中丢失精度。数据库和 Python 内部仍使用整数。

## 分页参数

使用分页依赖的接口通常支持：

| 参数 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `page` | integer | 页码，从 1 开始 | `page=1` |
| `page_size` | integer | 每页数量 | `page_size=20` |

分页响应包含 `items`、`total`、`page`、`page_size` 等字段。

## 权限级别

| 级别 | 说明 |
|---|---|
| 公开 | 登录等公开接口 |
| JWT | 登录用户可访问 |
| Superuser | 仅超级管理员可访问 |

## 专题文档

- [认证](authentication.md)
- [沙盒工作台用户接口](opensandbox-user.md)
- [沙盒工作台管理员接口](opensandbox-admin.md)
