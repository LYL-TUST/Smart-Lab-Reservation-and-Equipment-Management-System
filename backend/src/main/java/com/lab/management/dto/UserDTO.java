package com.lab.management.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;

/**
 * 用户DTO
 */
@Data
public class UserDTO {
    
    private Long id;
    
    @NotBlank(message = "用户名不能为空")
    private String username;
    
    private String password;
    
    @NotBlank(message = "姓名不能为空")
    private String name;
    
    @NotBlank(message = "角色不能为空")
    private String role;
    
    private String email;
    
    private String phone;
    
    private String studentId;
    
    private String department;
    
    private Integer status;
    
    private String avatar;
}

