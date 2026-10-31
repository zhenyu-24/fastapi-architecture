# 认证

## 登录

```http
POST /api/v1/auth/login
Content-Type: application/json
```

请求：

```json
{
  "username": "admin",
  "password": "123456"
}
```

curl：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login   -H 'Content-Type: application/json'   -d '{"username":"admin","password":"123456"}'
```

成功响应中的关键字段：

```json
{
  "code": 200,
  "msg": "请求成功",
  "data": {
    "access_token": "<jwt>",
    "access_token_expire_time": "2026-11-01 13:00:00",
    "session_uuid": "<uuid>",
    "user": {
      "id": "2048601269672738816",
      "username": "admin",
      "is_superuser": true
    }
  }
}
```

## 使用 Bearer Token

```bash
curl http://127.0.0.1:8000/api/v1/opensandbox/overview   -H 'Authorization: Bearer <access_token>'
```

PowerShell：

```powershell
$headers = @{ Authorization = 'Bearer <access_token>' }
Invoke-RestMethod -Headers $headers -Uri 'http://127.0.0.1:8000/api/v1/opensandbox/overview'
```

## 管理员权限

管理员接口会验证 `is_superuser=true`。普通用户访问时返回 403。

前端登录后由请求客户端自动附加访问令牌；不要在 URL、日志或浏览器 Local Storage 之外的位置泄露 Token。

## 常见状态码

| 状态码 | 说明 |
|---:|---|
| 200 | 成功 |
| 400 | 参数或业务状态错误 |
| 401 | 未登录或 Token 失效 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 状态冲突 |
| 502 | OpenSandbox 上游服务错误 |
