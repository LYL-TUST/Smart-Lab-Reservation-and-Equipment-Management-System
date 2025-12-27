package com.lab.management.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 设备实体类
 */
@Data
@TableName("equipment")
public class Equipment {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String name;
    
    private String model;
    
    private Long labId;
    
    private String category;
    
    private String serialNumber;
    
    private String status;
    
    private LocalDate purchaseDate;
    
    private BigDecimal purchasePrice;
    
    private Integer warrantyPeriod;
    
    private String description;
    
    private String imageUrl;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
    
    @TableLogic
    private Integer deleted;
}

