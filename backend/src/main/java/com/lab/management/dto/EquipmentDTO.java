package com.lab.management.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 设备DTO
 */
@Data
public class EquipmentDTO {
    
    private Long id;
    
    @NotBlank(message = "设备名称不能为空")
    private String name;
    
    private String model;
    
    @NotNull(message = "所属实验室不能为空")
    private Long labId;
    
    private String category;
    
    private String serialNumber;
    
    private String status;
    
    private LocalDate purchaseDate;
    
    private BigDecimal purchasePrice;
    
    private Integer warrantyPeriod;
    
    private String description;
    
    private String imageUrl;
}

