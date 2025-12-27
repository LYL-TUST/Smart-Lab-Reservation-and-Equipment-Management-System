package com.lab.management.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lab.management.entity.Course;
import org.apache.ibatis.annotations.Mapper;

/**
 * 课程Mapper
 */
@Mapper
public interface CourseMapper extends BaseMapper<Course> {
}

