package com.lab.management.security;

import com.lab.management.entity.User;
import com.lab.management.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

/**
 * 用户详情服务实现
 */
@Service
@RequiredArgsConstructor
public class UserDetailsServiceImpl implements UserDetailsService {
    
    private final UserMapper userMapper;
    
    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        // 去除首尾空格
        String trimmedUsername = username.trim();
        
        User user = userMapper.selectOne(
            new LambdaQueryWrapper<User>()
                .eq(User::getUsername, trimmedUsername)
        );
        
        if (user == null) {
            throw new UsernameNotFoundException("用户不存在: " + trimmedUsername);
        }
        
        return new UserDetailsImpl(user);
    }
}

