package com.lab.management.util;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/**
 * 密码生成工具类
 * 用于生成BCrypt加密的密码
 */
public class PasswordGenerator {

    public static void main(String[] args) {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

        System.out.println("=== 生成BCrypt加密密码 ===");
        System.out.println();

        // 生成管理员密码
        String adminPassword = encoder.encode("admin123");
        System.out.println("admin123 -> " + adminPassword);

        // 生成教师密码
        String teacherPassword = encoder.encode("teacher123");
        System.out.println("teacher123 -> " + teacherPassword);

        // 生成学生密码
        String studentPassword = encoder.encode("student123");
        System.out.println("student123 -> " + studentPassword);

        System.out.println();
        System.out.println("=== SQL更新语句 ===");
        System.out.println();
        System.out.println("-- 更新管理员密码");
        System.out.println("UPDATE `user` SET `password` = '" + adminPassword + "' WHERE `username` = 'admin';");
        System.out.println();
        System.out.println("-- 更新教师密码");
        System.out
                .println("UPDATE `user` SET `password` = '" + teacherPassword + "' WHERE `username` LIKE 'teacher%';");
        System.out.println();
        System.out.println("-- 更新学生密码");
        System.out
                .println("UPDATE `user` SET `password` = '" + studentPassword + "' WHERE `username` LIKE 'student%';");
    }
}
