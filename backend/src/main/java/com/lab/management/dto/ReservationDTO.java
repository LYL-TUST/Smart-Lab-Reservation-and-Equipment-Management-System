package com.lab.management.dto;

import lombok.Data;
import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 预约DTO
 */
@Data
public class ReservationDTO {
    
    private Long id;
    
    private Long userId;
    
    @NotNull(message = "实验室不能为空")
    private Long labId;
    
    @NotNull(message = "预约类型不能为空")
    private String type;
    
    @NotNull(message = "开始时间不能为空")
    private LocalDateTime startTime;
    
    @NotNull(message = "结束时间不能为空")
    private LocalDateTime endTime;
    
    private String purpose;
    
    private Integer participantCount;
    
    private String status;
    
    private Long courseId;
    
    private Long parentId;
    
    private String remark;
    
    // 多次预约时的日期列表
    private List<LocalDateTime> dateList;
    
    // 设备预约列表
    private List<Long> equipmentIds;
}

