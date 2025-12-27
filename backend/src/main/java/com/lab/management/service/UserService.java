package com.lab.management.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.dto.UpdateProfileDTO;
import com.lab.management.dto.UserDTO;
import com.lab.management.entity.User;
import com.lab.management.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

/**
 * 用户服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UserService {
    
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    
    /**
     * 统计活跃用户数（状态为1的用户）
     */
    public long countActive() {
        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(User::getStatus, 1);
        return userMapper.selectCount(wrapper);
    }
    
    /**
     * 分页查询用户
     */
    public Page<User> page(Integer current, Integer size, String role, String name, String username) {
        log.info("分页查询用户: current={}, size={}, role={}, name={}, username={}", 
            current, size, role, name, username);
        
        Page<User> page = new Page<>(current, size);
        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<>();
        
        if (StringUtils.hasText(role)) {
            wrapper.eq(User::getRole, role);
        }
        if (StringUtils.hasText(name)) {
            wrapper.like(User::getName, name);
        }
        if (StringUtils.hasText(username)) {
            wrapper.like(User::getUsername, username);
        }
        
        wrapper.orderByDesc(User::getCreatedAt);
        
        return userMapper.selectPage(page, wrapper);
    }
    
    /**
     * 根据ID查询用户
     */
    public User getById(Long id) {
        log.info("查询用户详情: id={}", id);
        return userMapper.selectById(id);
    }
    
    /**
     * 创建用户
     */
    @Transactional(rollbackFor = Exception.class)
    public User create(UserDTO dto) {
        log.info("创建用户: {}", dto.getUsername());
        
        // 检查用户名是否已存在
        User existUser = userMapper.selectOne(
            new LambdaQueryWrapper<User>()
                .eq(User::getUsername, dto.getUsername())
        );
        
        if (existUser != null) {
            throw new RuntimeException("用户名已存在");
        }
        
        User user = new User();
        BeanUtils.copyProperties(dto, user);
        
        // 加密密码
        if (StringUtils.hasText(user.getPassword())) {
            user.setPassword(passwordEncoder.encode(user.getPassword()));
        }
        
        // 设置默认状态
        if (user.getStatus() == null) {
            user.setStatus(1);
        }
        
        userMapper.insert(user);
        log.info("用户创建成功: id={}", user.getId());
        
        return user;
    }
    
    /**
     * 更新用户
     */
    @Transactional(rollbackFor = Exception.class)
    public User update(Long id, UserDTO dto) {
        log.info("更新用户: id={}", id);
        
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        
        // 如果用户名改变，检查新用户名是否已存在
        if (StringUtils.hasText(dto.getUsername()) && !dto.getUsername().equals(user.getUsername())) {
            User existUser = userMapper.selectOne(
                new LambdaQueryWrapper<User>()
                    .eq(User::getUsername, dto.getUsername())
            );
            if (existUser != null) {
                throw new RuntimeException("用户名已存在");
            }
        }
        
        BeanUtils.copyProperties(dto, user);
        user.setId(id);
        
        // 如果提供了新密码，则加密
        if (StringUtils.hasText(dto.getPassword())) {
            user.setPassword(passwordEncoder.encode(dto.getPassword()));
        } else {
            // 不更新密码，保持原密码
            User existingUser = userMapper.selectById(id);
            if (existingUser != null) {
                user.setPassword(existingUser.getPassword());
            }
        }
        
        userMapper.updateById(user);
        log.info("用户更新成功: id={}", id);
        
        return user;
    }
    
    /**
     * 更新个人信息（当前登录用户）
     */
    @Transactional(rollbackFor = Exception.class)
    public User updateProfile(Long userId, UpdateProfileDTO dto) {
        log.info("更新个人信息: userId={}", userId);
        
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        
        // 只更新允许的字段
        if (StringUtils.hasText(dto.getEmail())) {
            user.setEmail(dto.getEmail());
        }
        if (StringUtils.hasText(dto.getPhone())) {
            user.setPhone(dto.getPhone());
        }
        if (StringUtils.hasText(dto.getName())) {
            user.setName(dto.getName());
        }
        if (StringUtils.hasText(dto.getStudentId())) {
            user.setStudentId(dto.getStudentId());
        }
        if (StringUtils.hasText(dto.getDepartment())) {
            user.setDepartment(dto.getDepartment());
        }
        if (StringUtils.hasText(dto.getAvatar())) {
            user.setAvatar(dto.getAvatar());
        }
        
        userMapper.updateById(user);
        log.info("个人信息更新成功: userId={}", userId);
        
        return user;
    }
    
    /**
     * 删除用户（逻辑删除）
     */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        log.info("删除用户: id={}", id);
        
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        
        userMapper.deleteById(id);
        log.info("用户删除成功: id={}", id);
    }
}

