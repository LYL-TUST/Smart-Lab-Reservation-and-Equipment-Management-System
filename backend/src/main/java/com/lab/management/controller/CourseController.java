package com.lab.management.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.common.Result;
import com.lab.management.dto.CourseDTO;
import com.lab.management.entity.Course;
import com.lab.management.security.UserDetailsImpl;
import com.lab.management.service.CourseService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 课程控制器
 */
@Slf4j
@RestController
@RequestMapping("/course")
@RequiredArgsConstructor
public class CourseController {

    private final CourseService courseService;

    /**
     * 分页查询课程
     */
    @GetMapping("/page")
    public Result<Page<Course>> page(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Long teacherId,
            @RequestParam(required = false) String semester,
            @RequestParam(required = false) Integer status) {

        Page<Course> page = courseService.page(current, size, name, teacherId, semester, status);
        return Result.success(page);
    }

    /**
     * 查询课程详情
     */
    @GetMapping("/{id}")
    public Result<Course> getById(@PathVariable Long id) {
        Course course = courseService.getById(id);
        if (course == null) {
            return Result.error("课程不存在");
        }
        return Result.success(course);
    }

    /**
     * 创建课程（仅教师和管理员）
     */
    @PostMapping
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public Result<Course> create(@Validated @RequestBody CourseDTO dto) {
        try {
            Course course = courseService.create(dto);
            return Result.success("创建成功", course);
        } catch (Exception e) {
            log.error("创建课程失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 更新课程（仅教师和管理员）
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public Result<Course> update(@PathVariable Long id,
            @Validated @RequestBody CourseDTO dto) {
        try {
            Course course = courseService.update(id, dto);
            return Result.success("更新成功", course);
        } catch (Exception e) {
            log.error("更新课程失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 删除课程（仅管理员）
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<String> delete(@PathVariable Long id) {
        try {
            courseService.delete(id);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("删除课程失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 结束课程（仅教师和管理员）
     */
    @PutMapping("/{id}/end")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public Result<Course> endCourse(@PathVariable Long id) {
        try {
            Course course = courseService.endCourse(id);
            return Result.success("课程已结束", course);
        } catch (Exception e) {
            log.error("结束课程失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 获取当前教师的课程列表
     */
    @GetMapping("/my")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public Result<Page<Course>> getMyCourses(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {

        Page<Course> page = courseService.getTeacherCourses(userDetails.getId(), current, size);
        return Result.success(page);
    }

    /**
     * 获取当前学期的课程
     */
    @GetMapping("/semester/{semester}")
    public Result<Page<Course>> getCurrentSemesterCourses(
            @PathVariable String semester,
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size) {

        Page<Course> page = courseService.getCurrentSemesterCourses(semester, current, size);
        return Result.success(page);
    }
}
