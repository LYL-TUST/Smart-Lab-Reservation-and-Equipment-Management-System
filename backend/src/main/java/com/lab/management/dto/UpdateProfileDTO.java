package com.lab.management.dto;

import lombok.Data;
import javax.validation.constraints.Email;

/**
 * 更新个人信息DTO
 */
@Data
public class UpdateProfileDTO {
    
    @Email(message = "邮箱格式不正确")
    private String email;
    
    private String phone;
    
    private String name;
    
    private String studentId;
    
    private String department;
    
    private String avatar;
}

