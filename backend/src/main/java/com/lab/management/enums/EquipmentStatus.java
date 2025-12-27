package com.lab.management.enums;

import lombok.Getter;

/**
 * 设备状态枚举
 */
@Getter
public enum EquipmentStatus {
    IDLE("空闲"),
    RESERVED("已预约"),
    IN_USE("使用中"),
    MAINTENANCE("维护中"),
    SCRAPPED("报废");

    private final String description;

    EquipmentStatus(String description) {
        this.description = description;
    }

    /**
     * 检查状态转换是否合法
     */
    public boolean canTransitionTo(EquipmentStatus target) {
        switch (this) {
            case IDLE:
                return target == RESERVED || target == MAINTENANCE || target == SCRAPPED;
            case RESERVED:
                return target == IN_USE || target == IDLE || target == MAINTENANCE;
            case IN_USE:
                return target == IDLE || target == MAINTENANCE;
            case MAINTENANCE:
                return target == IDLE || target == SCRAPPED;
            case SCRAPPED:
                return false; // 报废后不能转换到其他状态
            default:
                return false;
        }
    }
}

