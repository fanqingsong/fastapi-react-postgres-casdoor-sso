# OIDC集成说明

本项目已集成OpenID Connect (OIDC) 单点登录功能，支持两种登录方式：

## 1. 密码登录（原有功能）
- 用户名/密码直接登录
- 使用Casdoor的Resource Owner Password Credentials流程

## 2. OIDC SSO登录（新增功能）
- 点击"Login with SSO (OIDC)"按钮
- 重定向到Casdoor登录页面
- 支持企业SSO、社交登录等

## 后端配置

### 环境变量
```bash
CASDOOR_ENDPOINT=http://casdoor:8000
CASDOOR_CLIENT_ID=fastapi-client
CASDOOR_CLIENT_SECRET=your-client-secret
CASDOOR_ORGANIZATION=admin
CASDOOR_APPLICATION=app-example
```

### 新增API端点
- `GET /api/auth/oidc/login` - 获取OIDC登录URL
- `GET /api/auth/oidc/callback` - 处理OIDC回调
- `GET /api/auth/oidc/user` - 获取当前OIDC用户信息

## 前端配置

### 新增组件
- `OIDCCallback.tsx` - 处理OIDC回调
- 更新 `Login.tsx` - 添加OIDC登录按钮
- 更新 `Auth.ts` - 添加OIDC相关函数

### 新增路由
- `/oidc/callback` - OIDC回调处理页面

## 使用方法

1. **配置Casdoor应用程序**
   - 在Casdoor中创建应用程序
   - 设置Valid Redirect URIs为 `http://localhost/oidc/callback`
   - 启用Authorization Code flow

2. **启动服务**
   ```bash
   ./bin/start.sh
   ```

3. **访问登录页面**
   - 访问 `http://localhost/login`
   - 选择"Login with SSO (OIDC)"进行OIDC登录
   - 或使用"Login with Password"进行密码登录

## 回调URL配置

当前回调URL设置为：`http://localhost/oidc/callback`

如需修改，请更新以下文件：
- `backend/app/main.py` - 更新 `callback_uri` 参数
- Casdoor应用程序配置 - 更新Valid Redirect URIs

## 注意事项

1. 确保Casdoor服务正常运行
2. 检查网络连接和DNS解析
3. 验证应用程序配置和密钥
4. 回调URL必须与Casdoor配置匹配

## 故障排除

1. **OIDC登录失败**
   - 检查Casdoor服务状态
   - 验证应用程序配置
   - 查看后端日志

2. **回调处理失败**
   - 检查回调URL配置
   - 验证授权码格式
   - 查看前端控制台错误

3. **Token验证失败**
   - 检查JWT签名
   - 验证Token过期时间
   - 确认用户角色权限 