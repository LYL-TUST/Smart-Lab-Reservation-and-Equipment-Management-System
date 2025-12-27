package com.lab.management;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 智能实验室预约与设备管理系统 - 启动类
 * 
 * @author Lab Management Team
 * @since 2024-12-24
 */
@SpringBootApplication
@MapperScan("com.lab.management.mapper")
public class LabManagementApplication {

    public static void main(String[] args) {
        SpringApplication.run(LabManagementApplication.class, args);
        System.out.println("\n========================================");
        System.out.println("智能实验室预约与设备管理系统启动成功！");
        System.out.println("访问地址: http://localhost:8080/api");
        System.out.println("========================================\n");
    }
}

