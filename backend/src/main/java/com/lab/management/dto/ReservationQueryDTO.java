package com.lab.management.dto;

import lombok.Data;

/**
 * 预约查询DTO
 */
@Data
public class ReservationQueryDTO {
    
    private Long labId;
    
    private String status;
    
    private String type;
    
    private String startDate;
    
    private String endDate;
    
    private Long userId;
    
    private Long courseId;
    
    private Integer current = 1;
    
    private Integer size = 10;
}

