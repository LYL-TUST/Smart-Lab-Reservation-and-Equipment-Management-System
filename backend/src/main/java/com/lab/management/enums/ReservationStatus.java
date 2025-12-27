package com.lab.management.enums;

import lombok.Getter;

/**
 * 预约状态枚举
 */
@Getter
public enum ReservationStatus {
    PENDING("待审核"),
    APPROVED("已通过"),
    REJECTED("已拒绝"),
    CANCELLED("已取消"),
    COMPLETED("已完成");

    private final String description;

    ReservationStatus(String description) {
        this.description = description;
    }
}

