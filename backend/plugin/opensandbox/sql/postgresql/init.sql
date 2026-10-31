create table if not exists sys_opensandbox (
    id bigserial primary key,
    sandbox_id varchar(64) not null,
    name varchar(128) not null,
    image varchar(512) not null,
    user_id bigint not null,
    username varchar(64) not null,
    status varchar(16) not null default 'Pending',
    last_activity_time timestamp with time zone not null default now(),
    paused_time timestamp with time zone,
    expires_at timestamp with time zone,
    created_time timestamp with time zone not null default now(),
    updated_time timestamp with time zone,
    deleted bigint not null default 0,
    deleted_time timestamp with time zone,
    constraint uk_sys_opensandbox_sandbox_id unique (sandbox_id)
);
create index if not exists ix_sys_opensandbox_user_id on sys_opensandbox (user_id);
create index if not exists ix_sys_opensandbox_status on sys_opensandbox (status);
create index if not exists ix_sys_opensandbox_last_activity on sys_opensandbox (last_activity_time);

create table if not exists sys_opensandbox_command (
    id bigserial primary key,
    sandbox_id varchar(64) not null,
    sandbox_name varchar(128) not null,
    user_id bigint not null,
    username varchar(64) not null,
    source varchar(16) not null,
    session_id varchar(128),
    command text not null,
    cwd varchar(512),
    stdout text not null,
    stderr text not null,
    exit_code integer,
    status varchar(16) not null default 'success',
    duration_ms integer not null default 0,
    truncated boolean not null default false,
    created_time timestamp with time zone not null default now(),
    updated_time timestamp with time zone,
    deleted bigint not null default 0,
    deleted_time timestamp with time zone
);
create index if not exists ix_sys_opensandbox_command_sandbox on sys_opensandbox_command (sandbox_id);
create index if not exists ix_sys_opensandbox_command_user on sys_opensandbox_command (user_id);
create index if not exists ix_sys_opensandbox_command_status on sys_opensandbox_command (status);
create index if not exists ix_sys_opensandbox_command_time on sys_opensandbox_command (created_time);
