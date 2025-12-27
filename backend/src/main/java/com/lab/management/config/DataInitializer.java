package com.lab.management.config;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lab.management.entity.User;
import com.lab.management.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 数据初始化器
 * 在应用启动时自动检查并加密用户密码
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {
    
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    
    @Override
    public void run(String... args) {
        log.info("开始检查用户密码...");
        
        try {
            // 获取所有用户
            List<User> users = userMapper.selectList(new LambdaQueryWrapper<User>());
            
            if (users.isEmpty()) {
                log.info("没有用户数据，跳过密码初始化");
                return;
            }
            
            int updatedCount = 0;
            
            for (User user : users) {
                // 检查密码是否已经是BCrypt格式
                // BCrypt密码以 $2a$, $2b$, $2y$ 开头
                if (user.getPassword() != null && 
                    !user.getPassword().startsWith("$2a$") && 
                    !user.getPassword().startsWith("$2b$") && 
                    !user.getPassword().startsWith("$2y$")) {
                    
                    // 密码是明文，需要加密
                    String plainPassword = user.getPassword();
                    String encryptedPassword = passwordEncoder.encode(plainPassword);
                    user.setPassword(encryptedPassword);
                    userMapper.updateById(user);
                    
                    log.info("已加密用户 {} 的密码", user.getUsername());
                    updatedCount++;
                }
            }
            
            if (updatedCount > 0) {
                log.info("密码初始化完成！共更新 {} 个用户的密码", updatedCount);
            } else {
                log.info("所有用户密码已加密，无需更新");
            }
            
        } catch (Exception e) {
            log.error("密码初始化失败", e);
        }
    }
}

