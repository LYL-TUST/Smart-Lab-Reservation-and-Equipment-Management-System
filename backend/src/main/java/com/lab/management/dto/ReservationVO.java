package com.lab.management.dto;

import com.lab.management.entity.Reservation;
import lombok.Data;
import org.springframework.beans.BeanUtils;

import java.time.LocalDateTime;

/**
 * 预约视图对象（包含关联信息）
 */
@Data
public class ReservationVO {
    
    private Long id;
    
    private Long userId;
    
    private Long labId;
    
    private String laboratoryName;  // 实验室名称
    
    private String type;
    
    private LocalDateTime startTime;
    
    private LocalDateTime endTime;
    
    private String purpose;
    
    private Integer participantCount;
    
    private String status;
    
    private Long courseId;
    
    private Long parentId;
    
    private Long approvalUserId;
    
    private LocalDateTime approvalTime;
    
    private String approvalRemark;
    
    private LocalDateTime checkInTime;
    
    private LocalDateTime checkOutTime;
    
    private String remark;
    
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;
    
    /**
     * 从Reservation实体转换为VO
     */
    public static ReservationVO from(Reservation reservation) {
        ReservationVO vo = new ReservationVO();
        BeanUtils.copyProperties(reservation, vo);
        return vo;
    }
}

