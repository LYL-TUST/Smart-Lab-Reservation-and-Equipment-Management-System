package com.lab.management.dto;

import lombok.Data;

/**
 * 预约查询DTO
 */
@Data
public class ReservationQueryDTO {
    
    private Long labId;
    
    private String laboratoryName;  // 实验室名称（用于模糊查询）
    
    private String status;
    
    private String type;
    
    private String startDate;
    
    private String endDate;
    
    private Long userId;
    
    private Long courseId;
    
    private Integer current = 1;
    
    private Integer size = 10;
}

