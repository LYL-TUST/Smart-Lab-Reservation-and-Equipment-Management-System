package com.lab.management.dto;

import com.lab.management.entity.Laboratory;
import lombok.Data;
import org.springframework.beans.BeanUtils;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 实验室视图对象（包含关联信息）
 */
@Data
public class LaboratoryVO {
    
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
    
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;
    
    private Integer equipmentCount;  // 设备数量
    
    /**
     * 从Laboratory实体转换为VO
     */
    public static LaboratoryVO from(Laboratory laboratory) {
        LaboratoryVO vo = new LaboratoryVO();
        BeanUtils.copyProperties(laboratory, vo);
        return vo;
    }
}

