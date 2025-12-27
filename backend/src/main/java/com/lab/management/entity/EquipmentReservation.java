package com.lab.management.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 设备预约关联实体类
 */
@Data
@TableName("equipment_reservation")
public class EquipmentReservation {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long reservationId;
    
    private Long equipmentId;
    
    private Integer quantity;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}

