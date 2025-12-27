package com.lab.management.enums;

import lombok.Getter;

/**
 * 用户角色枚举
 */
@Getter
public enum UserRole {
    ADMIN("管理员"),
    TEACHER("教师"),
    STUDENT("学生");

    private final String description;

    UserRole(String description) {
        this.description = description;
    }
}

