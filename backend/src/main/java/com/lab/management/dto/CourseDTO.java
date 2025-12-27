package com.lab.management.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.time.LocalDate;

/**
 * 课程DTO
 */
@Data
public class CourseDTO {
    
    private Long id;
    
    @NotBlank(message = "课程名称不能为空")
    private String name;
    
    private String code;
    
    @NotNull(message = "授课教师不能为空")
    private Long teacherId;
    
    private Long labId;
    
    @NotBlank(message = "学期不能为空")
    private String semester;
    
    private Integer studentCount;
    
    private String weekSchedule;
    
    private LocalDate startDate;
    
    private LocalDate endDate;
    
    private String description;
    
    private Integer status;
}

