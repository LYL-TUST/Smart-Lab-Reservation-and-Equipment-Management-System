package com.lab.management.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lab.management.entity.Laboratory;
import org.apache.ibatis.annotations.Mapper;

/**
 * 实验室Mapper
 */
@Mapper
public interface LaboratoryMapper extends BaseMapper<Laboratory> {
}

