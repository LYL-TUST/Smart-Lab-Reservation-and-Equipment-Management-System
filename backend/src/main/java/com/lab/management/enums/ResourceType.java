package com.lab.management.enums;

import lombok.Getter;

/**
 * 资源类型枚举
 */
@Getter
public enum ResourceType {
    LAB("实验室"),
    EQUIPMENT("设备");

    private final String description;

    ResourceType(String description) {
        this.description = description;
    }
}

