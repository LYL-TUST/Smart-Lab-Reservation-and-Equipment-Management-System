package com.lab.management;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

public class PasswordTest {
    public static void main(String[] args) {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        
        // 测试当前数据库中的密码
        String dbPassword = "$2a$10$5ZwlZjY4xRxR5ZwlZjY4xOxRxR5ZwlZjY4xOxRxR5ZwlZjY4xO.u.";
        String inputPassword = "teacher123";
        
        System.out.println("测试密码匹配：");
        System.out.println("输入密码: " + inputPassword);
        System.out.println("数据库密码: " + dbPassword);
        System.out.println("匹配结果: " + encoder.matches(inputPassword, dbPassword));
        
        System.out.println("\n生成新的加密密码：");
        String newPassword1 = encoder.encode("admin123");
        String newPassword2 = encoder.encode("teacher123");
        String newPassword3 = encoder.encode("student123");
        
        System.out.println("admin123 -> " + newPassword1);
        System.out.println("teacher123 -> " + newPassword2);
        System.out.println("student123 -> " + newPassword3);
        
        System.out.println("\n验证新密码：");
        System.out.println("admin123 匹配: " + encoder.matches("admin123", newPassword1));
        System.out.println("teacher123 匹配: " + encoder.matches("teacher123", newPassword2));
        System.out.println("student123 匹配: " + encoder.matches("student123", newPassword3));
        
        System.out.println("\n=== SQL更新语句 ===");
        System.out.println("UPDATE `user` SET `password` = '" + newPassword1 + "' WHERE `username` = 'admin';");
        System.out.println("UPDATE `user` SET `password` = '" + newPassword2 + "' WHERE `username` LIKE 'teacher%';");
        System.out.println("UPDATE `user` SET `password` = '" + newPassword3 + "' WHERE `username` LIKE 'student%';");
    }
}

