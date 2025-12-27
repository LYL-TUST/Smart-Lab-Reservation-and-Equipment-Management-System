package com.lab.management.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 预约实体类
 */
@Data
@TableName("reservation")
public class Reservation {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long userId;
    
    private Long labId;
    
    private String type;
    
    private LocalDateTime startTime;
    
    private LocalDateTime endTime;
    
    private String purpose;
    
    private Integer participantCount;
    
    private String status;
    
    private Long courseId;
    
    private Long parentId;
    
    private Long approvalUserId;
    
    private LocalDateTime approvalTime;
    
    private String approvalRemark;
    
    private LocalDateTime checkInTime;
    
    private LocalDateTime checkOutTime;
    
    private String remark;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
    
    @TableLogic
    private Integer deleted;
}

