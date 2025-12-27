package com.lab.management.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 维护记录实体类
 */
@Data
@TableName("maintenance_record")
public class MaintenanceRecord {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String resourceType;
    
    private Long resourceId;
    
    private String type;
    
    private LocalDateTime startTime;
    
    private LocalDateTime endTime;
    
    private String reason;
    
    private String description;
    
    private BigDecimal cost;
    
    private Long operatorId;
    
    private String status;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
    
    @TableLogic
    private Integer deleted;
}

