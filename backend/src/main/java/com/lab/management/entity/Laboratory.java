package com.lab.management.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 实验室实体类
 */
@Data
@TableName("laboratory")
public class Laboratory {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String name;
    
    private String location;
    
    private String building;
    
    private Integer floor;
    
    private String roomNumber;
    
    private Integer capacity;
    
    private BigDecimal area;
    
    private String type;
    
    private String description;
    
    private String status;
    
    private String openTime;
    
    private String facilities;
    
    private String imageUrl;
    
    private Long managerId;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
    
    @TableLogic
    private Integer deleted;
}

