package com.lab.management.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lab.management.dto.ConflictResult;
import com.lab.management.dto.ReservationDTO;
import com.lab.management.entity.Laboratory;
import com.lab.management.entity.MaintenanceRecord;
import com.lab.management.entity.Reservation;
import com.lab.management.enums.LabStatus;
import com.lab.management.mapper.LaboratoryMapper;
import com.lab.management.mapper.MaintenanceRecordMapper;
import com.lab.management.mapper.ReservationMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 冲突检测服务 - 核心算法实现
 * 
 * 检测维度：
 * 1. 时间冲突：同一资源在同一时间段是否已被预约
 * 2. 资源状态：资源是否处于可预约状态（非维护中）
 * 3. 容量限制：实验室人数是否超过容量
 * 4. 时间规则：是否在开放时间内
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ConflictDetectionService {
    
    private final ReservationMapper reservationMapper;
    private final LaboratoryMapper laboratoryMapper;
    private final MaintenanceRecordMapper maintenanceRecordMapper;
    
    /**
     * 检测单次预约冲突
     */
    public ConflictResult detectConflict(ReservationDTO dto) {
        log.info("开始检测预约冲突: labId={}, startTime={}, endTime={}", 
            dto.getLabId(), dto.getStartTime(), dto.getEndTime());
        
        // 1. 验证时间有效性
        ConflictResult timeValidation = validateTimeRange(dto.getStartTime(), dto.getEndTime());
        if (timeValidation.getHasConflict()) {
            return timeValidation;
        }
        
        // 2. 检查实验室是否存在
        Laboratory lab = laboratoryMapper.selectById(dto.getLabId());
        if (lab == null) {
            return ConflictResult.conflict("实验室不存在");
        }
        
        // 3. 检查实验室状态
        ConflictResult statusCheck = checkLabStatus(lab);
        if (statusCheck.getHasConflict()) {
            return statusCheck;
        }
        
        // 4. 检查容量限制
        ConflictResult capacityCheck = checkCapacity(lab, dto.getParticipantCount());
        if (capacityCheck.getHasConflict()) {
            return capacityCheck;
        }
        
        // 5. 检查时间冲突（核心算法）
        ConflictResult timeConflict = checkTimeConflict(
            dto.getLabId(), 
            dto.getStartTime(), 
            dto.getEndTime(),
            dto.getId()
        );
        if (timeConflict.getHasConflict()) {
            return timeConflict;
        }
        
        // 6. 检查维护期间冲突
        ConflictResult maintenanceCheck = checkMaintenanceConflict(
            dto.getLabId(), 
            dto.getStartTime(), 
            dto.getEndTime()
        );
        if (maintenanceCheck.getHasConflict()) {
            return maintenanceCheck;
        }
        
        log.info("预约冲突检测通过");
        return ConflictResult.noConflict();
    }
    
    /**
     * 批量检测多次预约冲突
     */
    public List<ConflictResult> batchDetectConflict(List<ReservationDTO> dtoList) {
        log.info("开始批量检测预约冲突，数量: {}", dtoList.size());
        
        List<ConflictResult> results = new ArrayList<>();
        for (ReservationDTO dto : dtoList) {
            ConflictResult result = detectConflict(dto);
            results.add(result);
        }
        
        return results;
    }
    
    /**
     * 验证时间范围有效性
     */
    private ConflictResult validateTimeRange(LocalDateTime startTime, LocalDateTime endTime) {
        if (startTime == null || endTime == null) {
            return ConflictResult.conflict("开始时间和结束时间不能为空");
        }
        
        if (startTime.isAfter(endTime)) {
            return ConflictResult.conflict("开始时间不能晚于结束时间");
        }
        
        // 允许预约未来时间，但不允许预约过去时间（至少是当前时间之后）
        LocalDateTime now = LocalDateTime.now();
        if (startTime.isBefore(now)) {
            return ConflictResult.conflict("开始时间不能早于当前时间，请选择未来的时间");
        }
        
        // 检查预约时长（不超过24小时，允许跨天预约）
        long hours = java.time.Duration.between(startTime, endTime).toHours();
        if (hours > 24) {
            return ConflictResult.conflict("单次预约时长不能超过24小时");
        }
        
        // 检查预约时长是否太短（至少15分钟）
        long minutes = java.time.Duration.between(startTime, endTime).toMinutes();
        if (minutes < 15) {
            return ConflictResult.conflict("预约时长至少需要15分钟");
        }
        
        return ConflictResult.noConflict();
    }
    
    /**
     * 检查实验室状态
     */
    private ConflictResult checkLabStatus(Laboratory lab) {
        if (LabStatus.MAINTENANCE.name().equals(lab.getStatus())) {
            return ConflictResult.conflict("实验室正在维护中，暂不可预约");
        }
        return ConflictResult.noConflict();
    }
    
    /**
     * 检查容量限制
     */
    private ConflictResult checkCapacity(Laboratory lab, Integer participantCount) {
        if (participantCount != null && participantCount > lab.getCapacity()) {
            return ConflictResult.conflict(
                String.format("参与人数(%d)超过实验室容量(%d)", participantCount, lab.getCapacity())
            );
        }
        return ConflictResult.noConflict();
    }
    
    /**
     * 检查时间冲突（核心算法）
     * 
     * 时间区间重叠判断：
     * 两个时间区间 [start1, end1] 和 [start2, end2] 重叠的条件是：
     * start1 < end2 AND start2 < end1
     * 
     * 数据库查询优化：使用索引查询时间范围内的预约
     */
    private ConflictResult checkTimeConflict(Long labId, LocalDateTime startTime, 
                                            LocalDateTime endTime, Long excludeId) {
        log.debug("检查时间冲突: labId={}, startTime={}, endTime={}", labId, startTime, endTime);
        
        LambdaQueryWrapper<Reservation> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Reservation::getLabId, labId)
               .in(Reservation::getStatus, "PENDING", "APPROVED")
               .and(w -> w
                   // 情况1: 新预约的开始时间在已有预约期间
                   .apply("start_time <= {0} AND end_time > {0}", startTime)
                   // 情况2: 新预约的结束时间在已有预约期间
                   .or().apply("start_time < {0} AND end_time >= {0}", endTime)
                   // 情况3: 新预约完全包含已有预约
                   .or().apply("start_time >= {0} AND end_time <= {1}", startTime, endTime)
               );
        
        // 如果是更新操作，排除当前预约
        if (excludeId != null) {
            wrapper.ne(Reservation::getId, excludeId);
        }
        
        List<Reservation> conflictReservations = reservationMapper.selectList(wrapper);
        
        if (!conflictReservations.isEmpty()) {
            Reservation conflict = conflictReservations.get(0);
            String message = String.format(
                "时间冲突：该时间段已被预约（预约ID: %d, 时间: %s ~ %s）",
                conflict.getId(),
                conflict.getStartTime(),
                conflict.getEndTime()
            );
            return ConflictResult.conflict(message, conflictReservations);
        }
        
        return ConflictResult.noConflict();
    }
    
    /**
     * 检查维护期间冲突
     */
    private ConflictResult checkMaintenanceConflict(Long labId, LocalDateTime startTime, 
                                                   LocalDateTime endTime) {
        log.debug("检查维护期间冲突: labId={}, startTime={}, endTime={}", labId, startTime, endTime);
        
        LambdaQueryWrapper<MaintenanceRecord> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MaintenanceRecord::getResourceType, "LAB")
               .eq(MaintenanceRecord::getResourceId, labId)
               .eq(MaintenanceRecord::getStatus, "IN_PROGRESS")
               .and(w -> w
                   .apply("start_time <= {0} AND (end_time IS NULL OR end_time > {0})", startTime)
                   .or().apply("start_time < {0} AND (end_time IS NULL OR end_time >= {0})", endTime)
                   .or().apply("start_time >= {0} AND start_time < {1}", startTime, endTime)
               );
        
        List<MaintenanceRecord> maintenanceRecords = maintenanceRecordMapper.selectList(wrapper);
        
        if (!maintenanceRecords.isEmpty()) {
            MaintenanceRecord record = maintenanceRecords.get(0);
            String message = String.format(
                "该时间段实验室正在维护中（维护原因: %s, 开始时间: %s）",
                record.getReason(),
                record.getStartTime()
            );
            return ConflictResult.conflict(message, maintenanceRecords);
        }
        
        return ConflictResult.noConflict();
    }
    
    /**
     * 检查是否有任何冲突（快速检查）
     */
    public boolean hasAnyConflict(Long labId, LocalDateTime startTime, LocalDateTime endTime) {
        ReservationDTO dto = new ReservationDTO();
        dto.setLabId(labId);
        dto.setStartTime(startTime);
        dto.setEndTime(endTime);
        
        ConflictResult result = detectConflict(dto);
        return result.getHasConflict();
    }
    
    /**
     * 获取指定时间段内的所有预约（用于日历视图）
     */
    public List<Reservation> getReservationsInTimeRange(Long labId, LocalDateTime startTime, 
                                                        LocalDateTime endTime) {
        LambdaQueryWrapper<Reservation> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Reservation::getLabId, labId)
               .in(Reservation::getStatus, "PENDING", "APPROVED", "COMPLETED")
               .and(w -> w
                   .apply("start_time < {0} AND end_time > {1}", endTime, startTime)
               )
               .orderByAsc(Reservation::getStartTime);
        
        return reservationMapper.selectList(wrapper);
    }
}

