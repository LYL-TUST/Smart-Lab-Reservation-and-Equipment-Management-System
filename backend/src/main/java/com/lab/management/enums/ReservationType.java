package com.lab.management.enums;

import lombok.Getter;

/**
 * 预约类型枚举
 */
@Getter
public enum ReservationType {
    SINGLE("单次预约"),
    MULTIPLE("多次预约"),
    COURSE("课程绑定预约");

    private final String description;

    ReservationType(String description) {
        this.description = description;
    }
}

