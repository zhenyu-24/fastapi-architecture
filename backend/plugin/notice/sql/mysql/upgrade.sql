-- 升级脚本：sys_user_notice 表结构调整
-- 1. 移除 is_deleted 列（改用 LogicalDeleteMixin 的 deleted 列）
-- 2. 添加外键级联删除约束

-- 清理旧数据：已标记 is_deleted=true 的记录，对应 deleted 设为 id
update sys_user_notice set deleted = id, deleted_time = now() where is_deleted = true;

-- 移除 is_deleted 列
alter table sys_user_notice drop column is_deleted;

-- 添加外键约束（如果尚未添加）
alter table sys_user_notice add constraint fk_sys_user_notice_user_id foreign key (user_id) references sys_user(id) on delete cascade;
alter table sys_user_notice add constraint fk_sys_user_notice_notice_id foreign key (notice_id) references sys_notice(id) on delete cascade;
