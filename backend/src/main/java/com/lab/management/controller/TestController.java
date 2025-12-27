package com.lab.management.controller;

import com.lab.management.common.Result;
import com.lab.management.entity.User;
import com.lab.management.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

/**
 * 测试控制器
 */
@Slf4j
@RestController
@RequestMapping("/test")
@RequiredArgsConstructor
public class TestController {

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    /**
     * 初始化用户密码
     */
    @GetMapping("/init-passwords")
    public Result<String> initPasswords() {
        try {
            // 更新admin密码
            User admin = userMapper.selectOne(
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                            .eq(User::getUsername, "admin"));
            if (admin != null) {
                admin.setPassword(passwordEncoder.encode("admin123"));
                userMapper.updateById(admin);
                log.info("更新admin密码成功");
            }

            // 更新teacher密码
            userMapper.selectList(
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                            .like(User::getUsername, "teacher"))
                    .forEach(user -> {
                        user.setPassword(passwordEncoder.encode("teacher123"));
                        userMapper.updateById(user);
                        log.info("更新{}密码成功", user.getUsername());
                    });

            // 更新student密码
            userMapper.selectList(
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                            .like(User::getUsername, "student"))
                    .forEach(user -> {
                        user.setPassword(passwordEncoder.encode("student123"));
                        userMapper.updateById(user);
                        log.info("更新{}密码成功", user.getUsername());
                    });

            return Result.success("密码初始化成功！\n" +
                    "admin/admin123\n" +
                    "teacher1/teacher123\n" +
                    "student1/student123");

        } catch (Exception e) {
            log.error("密码初始化失败", e);
            return Result.error("密码初始化失败: " + e.getMessage());
        }
    }

    /**
     * 验证密码
     */
    @GetMapping("/verify-password")
    public Result<String> verifyPassword(@RequestParam String username, @RequestParam String password) {
        try {
            User user = userMapper.selectOne(
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                            .eq(User::getUsername, username));

            if (user == null) {
                return Result.error("用户不存在");
            }

            boolean matches = passwordEncoder.matches(password, user.getPassword());

            return Result.success("用户: " + username +
                    "\n输入密码: " + password +
                    "\n数据库密码: " + user.getPassword().substring(0, 30) + "..." +
                    "\n匹配结果: " + matches);

        } catch (Exception e) {
            log.error("验证失败", e);
            return Result.error("验证失败: " + e.getMessage());
        }
    }

    /**
     * 查看所有用户密码状态
     */
    @GetMapping("/check-all-passwords")
    public Result<String> checkAllPasswords() {
        try {
            StringBuilder result = new StringBuilder("用户密码状态：\n\n");

            java.util.List<User> users = userMapper.selectList(
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>());

            for (User user : users) {
                String passwordPreview = user.getPassword().substring(0, Math.min(30, user.getPassword().length()));
                boolean isEncrypted = user.getPassword().startsWith("$2a$") ||
                        user.getPassword().startsWith("$2b$") ||
                        user.getPassword().startsWith("$2y$");

                result.append(String.format("用户: %s\n", user.getUsername()));
                result.append(String.format("密码预览: %s...\n", passwordPreview));
                result.append(String.format("是否加密: %s\n", isEncrypted ? "是" : "否"));
                result.append(String.format("状态: %s\n\n", user.getStatus() == 1 ? "正常" : "禁用"));
            }

            return Result.success(result.toString());

        } catch (Exception e) {
            log.error("检查失败", e);
            return Result.error("检查失败: " + e.getMessage());
        }
    }

    /**
     * 生成BCrypt密码
     */
    @GetMapping("/generate-password")
    public Result<String> generatePassword(@RequestParam String password) {
        try {
            String encoded = passwordEncoder.encode(password);
            return Result.success("原始密码: " + password + "\nBCrypt加密: " + encoded);
        } catch (Exception e) {
            log.error("生成密码失败", e);
            return Result.error("生成密码失败: " + e.getMessage());
        }
    }

    /**
     * 测试接口
     */
    @GetMapping("/hello")
    public Result<String> hello() {
        return Result.success("API正常运行");
    }
}
