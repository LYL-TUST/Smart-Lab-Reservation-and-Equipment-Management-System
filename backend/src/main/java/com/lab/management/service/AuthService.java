package com.lab.management.service;

import com.lab.management.dto.LoginDTO;
import com.lab.management.entity.User;
import com.lab.management.mapper.UserMapper;
import com.lab.management.security.UserDetailsImpl;
import com.lab.management.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.HashMap;
import java.util.Map;

/**
 * 认证服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {
    
    private final AuthenticationManager authenticationManager;
    private final JwtUtil jwtUtil;
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    
    /**
     * 用户登录
     */
    public Map<String, Object> login(LoginDTO loginDTO) {
        log.info("用户登录: username={}", loginDTO.getUsername());
        
        try {
            // Spring Security认证
            Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                    loginDTO.getUsername(),
                    loginDTO.getPassword()
                )
            );
            
            UserDetailsImpl userDetails = (UserDetailsImpl) authentication.getPrincipal();
            
            // 查询完整的用户信息
            User user = userMapper.selectById(userDetails.getId());
            if (user == null) {
                throw new RuntimeException("用户不存在");
            }
            
            // 生成JWT Token
            String token = jwtUtil.generateToken(
                user.getId(),
                user.getUsername(),
                user.getRole()
            );
            
            // 清除密码信息
            user.setPassword(null);
            
            Map<String, Object> result = new HashMap<>();
            result.put("token", token);
            result.put("user", user);
            
            log.info("用户登录成功: username={}, role={}", user.getUsername(), user.getRole());
            return result;
            
        } catch (Exception e) {
            log.error("用户登录失败: username={}", loginDTO.getUsername(), e);
            throw new RuntimeException("用户名或密码错误");
        }
    }
    
    /**
     * 用户注册
     */
    @Transactional(rollbackFor = Exception.class)
    public User register(User user) {
        log.info("用户注册: username={}, role={}", user.getUsername(), user.getRole());
        
        // 检查用户名是否已存在
        User existUser = userMapper.selectOne(
            new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                .eq(User::getUsername, user.getUsername())
        );
        
        if (existUser != null) {
            throw new RuntimeException("用户名已存在");
        }
        
        // 验证角色：只允许注册为 STUDENT 或 TEACHER，不允许注册为 ADMIN
        String role = user.getRole();
        if (role == null || role.trim().isEmpty()) {
            // 如果没有指定角色，默认为 STUDENT
            user.setRole("STUDENT");
        } else if ("ADMIN".equals(role)) {
            // 防止权限提升：不允许注册为管理员
            throw new RuntimeException("不允许注册为管理员角色");
        } else if (!"STUDENT".equals(role) && !"TEACHER".equals(role)) {
            // 只允许 STUDENT 和 TEACHER 角色
            throw new RuntimeException("无效的角色类型");
        }
        
        // 加密密码
        user.setPassword(passwordEncoder.encode(user.getPassword()));
        
        // 设置默认状态
        if (user.getStatus() == null) {
            user.setStatus(1);
        }
        
        userMapper.insert(user);
        log.info("用户注册成功: id={}, username={}, role={}", user.getId(), user.getUsername(), user.getRole());
        
        return user;
    }
    
    /**
     * 修改密码
     */
    @Transactional(rollbackFor = Exception.class)
    public void changePassword(Long userId, String oldPassword, String newPassword) {
        log.info("修改密码: userId={}", userId);
        
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        
        // 验证旧密码
        if (!passwordEncoder.matches(oldPassword, user.getPassword())) {
            throw new RuntimeException("原密码错误");
        }
        
        // 更新密码
        user.setPassword(passwordEncoder.encode(newPassword));
        userMapper.updateById(user);
        
        log.info("密码修改成功: userId={}", userId);
    }
}

