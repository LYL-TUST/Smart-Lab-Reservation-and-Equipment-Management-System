package com.lab.management.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lab.management.entity.Reservation;
import org.apache.ibatis.annotations.Mapper;

/**
 * 预约Mapper
 */
@Mapper
public interface ReservationMapper extends BaseMapper<Reservation> {
}

