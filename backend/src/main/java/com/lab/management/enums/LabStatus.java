package com.lab.management.enums;

import lombok.Getter;

/**
 * 实验室状态枚举
 */
@Getter
public enum LabStatus {
    IDLE("空闲"),
    RESERVED("已预约"),
    IN_USE("使用中"),
    MAINTENANCE("维护中");

    private final String description;

    LabStatus(String description) {
        this.description = description;
    }

    /**
     * 检查状态转换是否合法
     */
    public boolean canTransitionTo(LabStatus target) {
        switch (this) {
            case IDLE:
                return target == RESERVED || target == MAINTENANCE;
            case RESERVED:
                return target == IN_USE || target == IDLE || target == MAINTENANCE;
            case IN_USE:
                return target == IDLE || target == MAINTENANCE;
            case MAINTENANCE:
                return target == IDLE;
            default:
                return false;
        }
    }
}

