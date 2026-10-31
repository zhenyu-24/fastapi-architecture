set @system_menu_id = (select id from sys_menu where name = 'System');

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values ('config.menu', 'PluginConfig', '/plugins/config', 7, 'codicon:symbol-parameter', 1, '/plugins/config/views/index', null, 1, 1, 1, '', null, @system_menu_id, now(), null);

set @config_menu_id = LAST_INSERT_ID();

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
('新增', 'AddConfig', null, 0, null, 2, null, 'sys:config:add', 1, 0, 1, '', null, @config_menu_id, now(), null),
('修改', 'EditConfig', null, 0, null, 2, null, 'sys:config:edit', 1, 0, 1, '', null, @config_menu_id, now(), null),
('删除', 'DeleteConfig', null, 0, null, 2, null, 'sys:config:del', 1, 0, 1, '', null, @config_menu_id, now(), null);

insert into sys_config (id, name, type, `key`, value, is_frontend, remark, created_time, updated_time)
values
(1, '状态', 'EMAIL', 'EMAIL_CONFIG_STATUS', '1', false, null, now(), null),
(2, '服务器地址', 'EMAIL', 'EMAIL_HOST', 'smtp.qq.com', false, null, now(), null),
(3, '服务器端口', 'EMAIL', 'EMAIL_PORT', '465', false, null, now(), null),
(4, '邮箱账号', 'EMAIL', 'EMAIL_USERNAME', 'fba@qq.com', false, null, now(), null),
(5, '邮箱密码', 'EMAIL', 'EMAIL_PASSWORD', '', false, null, now(), null),
(6, 'SSL 加密', 'EMAIL', 'EMAIL_SSL', 'true', false, null, now(), null),
(7, '状态', 'USER_SECURITY', 'USER_SECURITY_CONFIG_STATUS', '1', false, null, now(), null),
(8, '密码错误锁定阈值', 'USER_SECURITY', 'USER_LOCK_THRESHOLD', '5', false, '0 表示禁用锁定', now(), null),
(9, '密码错误锁定时长（秒）', 'USER_SECURITY', 'USER_LOCK_SECONDS', '300', false, null, now(), null),
(10, '密码有效期（天）', 'USER_SECURITY', 'USER_PASSWORD_EXPIRY_DAYS', '0', false, '0 表示永不过期', now(), null),
(11, '密码到期提醒（天）', 'USER_SECURITY', 'USER_PASSWORD_REMINDER_DAYS', '7', false, '0 表示不提醒', now(), null),
(12, '密码历史检查次数', 'USER_SECURITY', 'USER_PASSWORD_HISTORY_CHECK_COUNT', '3', false, null, now(), null),
(13, '密码最小长度', 'USER_SECURITY', 'USER_PASSWORD_MIN_LENGTH', '6', false, null, now(), null),
(14, '密码最大长度', 'USER_SECURITY', 'USER_PASSWORD_MAX_LENGTH', '32', false, null, now(), null),
(15, '密码必须包含特殊字符', 'USER_SECURITY', 'USER_PASSWORD_REQUIRE_SPECIAL_CHAR', 'false', false, null, now(), null),
(16, '状态', 'LOGIN', 'LOGIN_CONFIG_STATUS', '1', false, null, now(), null),
(17, '验证码开关', 'LOGIN', 'LOGIN_CAPTCHA_ENABLED', 'false', false, null, now(), null);

insert into sys_config (id, name, type, `key`, value, is_frontend, remark, created_time, updated_time)
values
(18, '启用沙盒动态配置', 'SANDBOX', 'OPEN_SANDBOX_CONFIG_STATUS', '1', false, '启用后使用参数配置中的全局沙盒参数', now(), null),
(19, '默认沙盒镜像', 'SANDBOX', 'OPEN_SANDBOX_IMAGE', 'sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.1.0', false, '新建沙盒默认镜像', now(), null),
(20, '每用户最大沙盒数', 'SANDBOX', 'OPEN_SANDBOX_MAX_SANDBOXES_PER_USER', '2', false, '所有用户统一全局配额', now(), null),
(21, '空闲暂停秒数', 'SANDBOX', 'OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS', '1800', false, '超过该时间无活动后自动暂停', now(), null),
(22, '空闲自动暂停', 'SANDBOX', 'OPEN_SANDBOX_AUTO_PAUSE_ENABLED', 'true', false, null, now(), null),
(23, 'CPU 限制', 'SANDBOX', 'OPEN_SANDBOX_RESOURCE_CPU', '1', false, '例如 1 或 2', now(), null),
(24, '内存限制', 'SANDBOX', 'OPEN_SANDBOX_RESOURCE_MEMORY', '2Gi', false, '例如 2Gi 或 4Gi', now(), null),
(25, '命令输出最大字符数', 'SANDBOX', 'OPEN_SANDBOX_MAX_OUTPUT_CHARS', '200000', false, '超过后截断输出', now(), null),
(26, '文件上传限制（字节）', 'SANDBOX', 'OPEN_SANDBOX_UPLOAD_LIMIT_BYTES', '52428800', false, '单文件最大字节数', now(), null),
(27, '文本预览限制（字节）', 'SANDBOX', 'OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES', '2097152', false, '文本预览最大字节数', now(), null),
(28, '服务器地址', 'SANDBOX', 'OPEN_SANDBOX_URL', 'http://127.0.0.1:8080', false, 'OpenSandbox 服务地址，例如 http://127.0.0.1:8080', now(), null),
(29, '沙盒 API 开关', 'SANDBOX', 'OPEN_SANDBOX_API_STATUS', '1', false, '1=开启，0=暂停；不停止 OpenSandbox Server 进程', now(), null);
