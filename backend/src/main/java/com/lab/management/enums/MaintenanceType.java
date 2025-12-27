package com.lab.management.enums;

import lombok.Getter;

/**
 * 维护类型枚举
 */
@Getter
public enum MaintenanceType {
    MAINTENANCE("维护"),
    REPAIR("维修"),
    INSPECTION("检查");

    private final String description;

    MaintenanceType(String description) {
        this.description = description;
    }
}

