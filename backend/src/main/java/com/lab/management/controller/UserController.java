package com.lab.management.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.common.Result;
import com.lab.management.dto.UpdateProfileDTO;
import com.lab.management.dto.UserDTO;
import com.lab.management.entity.User;
import com.lab.management.security.UserDetailsImpl;
import com.lab.management.service.UserService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 用户控制器
 */
@Slf4j
@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    /**
     * 分页查询用户
     */
    @GetMapping
    public Result<Page<User>> page(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) String role,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String username) {
        try {
            Page<User> page = userService.page(current, size, role, name, username);
            return Result.success(page);
        } catch (Exception e) {
            log.error("查询用户列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 查询用户详情
     */
    @GetMapping("/{id}")
    public Result<User> getById(@PathVariable Long id) {
        try {
            User user = userService.getById(id);
            if (user == null) {
                return Result.error("用户不存在");
            }
            // 清除密码信息
            user.setPassword(null);
            return Result.success(user);
        } catch (Exception e) {
            log.error("查询用户详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 创建用户（仅管理员）
     */
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<User> create(@Validated @RequestBody UserDTO dto) {
        try {
            User user = userService.create(dto);
            // 清除密码信息
            user.setPassword(null);
            return Result.success("创建成功", user);
        } catch (Exception e) {
            log.error("创建用户失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 更新用户（仅管理员）
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<User> update(@PathVariable Long id,
            @Validated @RequestBody UserDTO dto) {
        try {
            User user = userService.update(id, dto);
            // 清除密码信息
            user.setPassword(null);
            return Result.success("更新成功", user);
        } catch (Exception e) {
            log.error("更新用户失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 删除用户（仅管理员）
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<String> delete(@PathVariable Long id) {
        try {
            userService.delete(id);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("删除用户失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 更新个人信息（当前登录用户）
     */
    @PutMapping("/profile")
    public Result<User> updateProfile(
            @Validated @RequestBody UpdateProfileDTO dto,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            User user = userService.updateProfile(userDetails.getId(), dto);
            // 清除密码信息
            user.setPassword(null);
            return Result.success("更新成功", user);
        } catch (Exception e) {
            log.error("更新个人信息失败", e);
            return Result.error(e.getMessage());
        }
    }
}

