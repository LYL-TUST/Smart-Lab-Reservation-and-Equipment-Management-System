package com.lab.management.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.dto.CourseDTO;
import com.lab.management.entity.Course;
import com.lab.management.mapper.CourseMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

/**
 * 课程服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CourseService {
    
    private final CourseMapper courseMapper;
    
    /**
     * 分页查询课程
     */
    public Page<Course> page(Integer current, Integer size, String name, 
                            Long teacherId, String semester, Integer status) {
        log.info("分页查询课程: current={}, size={}, name={}, teacherId={}, semester={}, status={}", 
            current, size, name, teacherId, semester, status);
        
        Page<Course> page = new Page<>(current, size);
        LambdaQueryWrapper<Course> wrapper = new LambdaQueryWrapper<>();
        
        if (StringUtils.hasText(name)) {
            wrapper.like(Course::getName, name);
        }
        if (teacherId != null) {
            wrapper.eq(Course::getTeacherId, teacherId);
        }
        if (StringUtils.hasText(semester)) {
            wrapper.eq(Course::getSemester, semester);
        }
        if (status != null) {
            wrapper.eq(Course::getStatus, status);
        }
        
        wrapper.orderByDesc(Course::getCreatedAt);
        
        return courseMapper.selectPage(page, wrapper);
    }
    
    /**
     * 根据ID查询课程
     */
    public Course getById(Long id) {
        log.info("查询课程详情: id={}", id);
        return courseMapper.selectById(id);
    }
    
    /**
     * 创建课程
     */
    @Transactional(rollbackFor = Exception.class)
    public Course create(CourseDTO dto) {
        log.info("创建课程: {}", dto.getName());
        
        Course course = new Course();
        BeanUtils.copyProperties(dto, course);
        
        // 设置默认状态
        if (course.getStatus() == null) {
            course.setStatus(1); // 进行中
        }
        
        courseMapper.insert(course);
        log.info("课程创建成功: id={}", course.getId());
        
        return course;
    }
    
    /**
     * 更新课程
     */
    @Transactional(rollbackFor = Exception.class)
    public Course update(Long id, CourseDTO dto) {
        log.info("更新课程: id={}", id);
        
        Course course = courseMapper.selectById(id);
        if (course == null) {
            throw new RuntimeException("课程不存在");
        }
        
        BeanUtils.copyProperties(dto, course);
        course.setId(id);
        
        courseMapper.updateById(course);
        log.info("课程更新成功: id={}", id);
        
        return course;
    }
    
    /**
     * 删除课程（逻辑删除）
     */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        log.info("删除课程: id={}", id);
        
        Course course = courseMapper.selectById(id);
        if (course == null) {
            throw new RuntimeException("课程不存在");
        }
        
        courseMapper.deleteById(id);
        log.info("课程删除成功: id={}", id);
    }
    
    /**
     * 结束课程
     */
    @Transactional(rollbackFor = Exception.class)
    public Course endCourse(Long id) {
        log.info("结束课程: id={}", id);
        
        Course course = courseMapper.selectById(id);
        if (course == null) {
            throw new RuntimeException("课程不存在");
        }
        
        course.setStatus(0); // 已结束
        courseMapper.updateById(course);
        
        log.info("课程已结束: id={}", id);
        return course;
    }
    
    /**
     * 获取教师的课程列表
     */
    public Page<Course> getTeacherCourses(Long teacherId, Integer current, Integer size) {
        log.info("查询教师课程: teacherId={}", teacherId);
        
        Page<Course> page = new Page<>(current, size);
        LambdaQueryWrapper<Course> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Course::getTeacherId, teacherId)
               .orderByDesc(Course::getCreatedAt);
        
        return courseMapper.selectPage(page, wrapper);
    }
    
    /**
     * 获取当前学期的课程
     */
    public Page<Course> getCurrentSemesterCourses(String semester, Integer current, Integer size) {
        log.info("查询当前学期课程: semester={}", semester);
        
        Page<Course> page = new Page<>(current, size);
        LambdaQueryWrapper<Course> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Course::getSemester, semester)
               .eq(Course::getStatus, 1)
               .orderByAsc(Course::getName);
        
        return courseMapper.selectPage(page, wrapper);
    }
}

