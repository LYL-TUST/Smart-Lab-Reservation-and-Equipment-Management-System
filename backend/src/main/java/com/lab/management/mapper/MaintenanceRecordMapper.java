package com.lab.management.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lab.management.entity.MaintenanceRecord;
import org.apache.ibatis.annotations.Mapper;

/**
 * 维护记录Mapper
 */
@Mapper
public interface MaintenanceRecordMapper extends BaseMapper<MaintenanceRecord> {
}

