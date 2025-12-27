package com.lab.management.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.math.BigDecimal;

/**
 * 实验室DTO
 */
@Data
public class LaboratoryDTO {
    
    private Long id;
    
    @NotBlank(message = "实验室名称不能为空")
    private String name;
    
    @NotBlank(message = "位置不能为空")
    private String location;
    
    private String building;
    
    private Integer floor;
    
    private String roomNumber;
    
    @NotNull(message = "容纳人数不能为空")
    private Integer capacity;
    
    private BigDecimal area;
    
    private String type;
    
    private String description;
    
    private String status;
    
    private String openTime;
    
    private String facilities;
    
    private String imageUrl;
    
    private Long managerId;
}

