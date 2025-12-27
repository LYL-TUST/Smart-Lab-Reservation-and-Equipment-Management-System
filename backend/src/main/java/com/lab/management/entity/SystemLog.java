package com.lab.management.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 系统日志实体类
 */
@Data
@TableName("system_log")
public class SystemLog {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long userId;
    
    private String username;
    
    private String operation;
    
    private String method;
    
    private String params;
    
    private String ip;
    
    private String result;
    
    private String errorMsg;
    
    private Integer executionTime;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}

