package com.lab.management.dto;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * 日历视图预约DTO
 */
@Data
public class CalendarReservationDTO {
    
    private Long id;
    
    private String title;  // 日历事件标题（实验室名称 + 预约目的）
    
    private LocalDateTime start;  // 开始时间
    
    private LocalDateTime end;  // 结束时间
    
    private String labId;  // 实验室ID（字符串格式，用于FullCalendar）
    
    private String laboratoryName;  // 实验室名称
    
    private String status;  // 预约状态
    
    private String type;  // 预约类型
    
    private String purpose;  // 预约目的
    
    private String color;  // 事件颜色（根据状态）
    
    private String backgroundColor;  // 背景颜色
    
    private String borderColor;  // 边框颜色
    
    private String textColor;  // 文字颜色
    
    private Boolean allDay;  // 是否全天事件（false，因为预约都有具体时间）
}

