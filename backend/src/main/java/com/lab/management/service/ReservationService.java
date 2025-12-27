package com.lab.management.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.dto.ConflictResult;
import com.lab.management.dto.ReservationDTO;
import com.lab.management.dto.ReservationQueryDTO;
import com.lab.management.entity.Reservation;
import com.lab.management.enums.ReservationStatus;
import com.lab.management.enums.ReservationType;
import com.lab.management.mapper.ReservationMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 预约服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReservationService {
    
    private final ReservationMapper reservationMapper;
    private final ConflictDetectionService conflictDetectionService;
    
    /**
     * 分页查询预约
     */
    public Page<Reservation> page(ReservationQueryDTO queryDTO) {
        log.info("分页查询预约: {}", queryDTO);
        
        Page<Reservation> page = new Page<>(queryDTO.getCurrent(), queryDTO.getSize());
        LambdaQueryWrapper<Reservation> wrapper = new LambdaQueryWrapper<>();
        
        if (queryDTO.getLabId() != null) {
            wrapper.eq(Reservation::getLabId, queryDTO.getLabId());
        }
        if (StringUtils.hasText(queryDTO.getStatus())) {
            wrapper.eq(Reservation::getStatus, queryDTO.getStatus());
        }
        if (StringUtils.hasText(queryDTO.getType())) {
            wrapper.eq(Reservation::getType, queryDTO.getType());
        }
        if (queryDTO.getUserId() != null) {
            wrapper.eq(Reservation::getUserId, queryDTO.getUserId());
        }
        if (queryDTO.getCourseId() != null) {
            wrapper.eq(Reservation::getCourseId, queryDTO.getCourseId());
        }
        if (StringUtils.hasText(queryDTO.getStartDate())) {
            wrapper.ge(Reservation::getStartTime, queryDTO.getStartDate());
        }
        if (StringUtils.hasText(queryDTO.getEndDate())) {
            wrapper.le(Reservation::getEndTime, queryDTO.getEndDate());
        }
        
        wrapper.orderByDesc(Reservation::getCreatedAt);
        
        return reservationMapper.selectPage(page, wrapper);
    }
    
    /**
     * 根据ID查询预约
     */
    public Reservation getById(Long id) {
        log.info("查询预约详情: id={}", id);
        return reservationMapper.selectById(id);
    }
    
    /**
     * 创建单次预约
     */
    @Transactional(rollbackFor = Exception.class)
    public Reservation createSingleReservation(ReservationDTO dto, Long userId) {
        log.info("创建单次预约: userId={}, labId={}", userId, dto.getLabId());
        
        dto.setUserId(userId);
        dto.setType(ReservationType.SINGLE.name());
        
        // 冲突检测
        ConflictResult conflictResult = conflictDetectionService.detectConflict(dto);
        if (conflictResult.getHasConflict()) {
            throw new RuntimeException(conflictResult.getMessage());
        }
        
        Reservation reservation = new Reservation();
        BeanUtils.copyProperties(dto, reservation);
        reservation.setStatus(ReservationStatus.PENDING.name());
        
        reservationMapper.insert(reservation);
        log.info("单次预约创建成功: id={}", reservation.getId());
        
        return reservation;
    }
    
    /**
     * 创建多次预约
     */
    @Transactional(rollbackFor = Exception.class)
    public List<Reservation> createMultipleReservation(ReservationDTO dto, Long userId) {
        log.info("创建多次预约: userId={}, labId={}, 日期数量={}", 
            userId, dto.getLabId(), dto.getDateList().size());
        
        if (dto.getDateList() == null || dto.getDateList().isEmpty()) {
            throw new RuntimeException("预约日期列表不能为空");
        }
        
        dto.setUserId(userId);
        dto.setType(ReservationType.MULTIPLE.name());
        
        // 创建父预约记录
        Reservation parentReservation = new Reservation();
        parentReservation.setUserId(userId);
        parentReservation.setLabId(dto.getLabId());
        parentReservation.setType(ReservationType.MULTIPLE.name());
        parentReservation.setStartTime(dto.getDateList().get(0));
        parentReservation.setEndTime(dto.getDateList().get(dto.getDateList().size() - 1));
        parentReservation.setPurpose(dto.getPurpose());
        parentReservation.setParticipantCount(dto.getParticipantCount());
        parentReservation.setStatus(ReservationStatus.PENDING.name());
        
        reservationMapper.insert(parentReservation);
        
        // 批量冲突检测
        List<ReservationDTO> dtoList = new ArrayList<>();
        for (LocalDateTime dateTime : dto.getDateList()) {
            ReservationDTO singleDto = new ReservationDTO();
            BeanUtils.copyProperties(dto, singleDto);
            singleDto.setStartTime(dateTime);
            // 假设每次预约时长相同
            long duration = java.time.Duration.between(dto.getStartTime(), dto.getEndTime()).toMinutes();
            singleDto.setEndTime(dateTime.plusMinutes(duration));
            dtoList.add(singleDto);
        }
        
        List<ConflictResult> conflictResults = conflictDetectionService.batchDetectConflict(dtoList);
        
        // 检查是否有冲突
        for (int i = 0; i < conflictResults.size(); i++) {
            if (conflictResults.get(i).getHasConflict()) {
                throw new RuntimeException(
                    String.format("第%d个预约时间冲突: %s", i + 1, conflictResults.get(i).getMessage())
                );
            }
        }
        
        // 创建子预约记录
        List<Reservation> reservations = new ArrayList<>();
        for (ReservationDTO singleDto : dtoList) {
            Reservation reservation = new Reservation();
            BeanUtils.copyProperties(singleDto, reservation);
            reservation.setParentId(parentReservation.getId());
            reservation.setStatus(ReservationStatus.PENDING.name());
            
            reservationMapper.insert(reservation);
            reservations.add(reservation);
        }
        
        log.info("多次预约创建成功: parentId={}, 子预约数量={}", 
            parentReservation.getId(), reservations.size());
        
        return reservations;
    }
    
    /**
     * 创建课程绑定预约
     */
    @Transactional(rollbackFor = Exception.class)
    public List<Reservation> createCourseReservation(ReservationDTO dto, Long userId) {
        log.info("创建课程绑定预约: userId={}, courseId={}", userId, dto.getCourseId());
        
        if (dto.getCourseId() == null) {
            throw new RuntimeException("课程ID不能为空");
        }
        
        if (dto.getDateList() == null || dto.getDateList().isEmpty()) {
            throw new RuntimeException("课程预约日期列表不能为空");
        }
        
        dto.setUserId(userId);
        dto.setType(ReservationType.COURSE.name());
        
        // 批量创建课程预约
        List<Reservation> reservations = new ArrayList<>();
        for (LocalDateTime dateTime : dto.getDateList()) {
            ReservationDTO singleDto = new ReservationDTO();
            BeanUtils.copyProperties(dto, singleDto);
            singleDto.setStartTime(dateTime);
            
            // 计算结束时间
            long duration = java.time.Duration.between(dto.getStartTime(), dto.getEndTime()).toMinutes();
            singleDto.setEndTime(dateTime.plusMinutes(duration));
            
            // 冲突检测
            ConflictResult conflictResult = conflictDetectionService.detectConflict(singleDto);
            if (conflictResult.getHasConflict()) {
                throw new RuntimeException(
                    String.format("课程预约时间冲突 (%s): %s", 
                        dateTime, conflictResult.getMessage())
                );
            }
            
            Reservation reservation = new Reservation();
            BeanUtils.copyProperties(singleDto, reservation);
            reservation.setStatus(ReservationStatus.APPROVED.name()); // 课程预约自动通过
            
            reservationMapper.insert(reservation);
            reservations.add(reservation);
        }
        
        log.info("课程绑定预约创建成功: courseId={}, 预约数量={}", 
            dto.getCourseId(), reservations.size());
        
        return reservations;
    }
    
    /**
     * 审批预约（管理员）
     */
    @Transactional(rollbackFor = Exception.class)
    public Reservation approveReservation(Long id, Long approvalUserId, String remark, boolean approved) {
        log.info("审批预约: id={}, approved={}", id, approved);
        
        Reservation reservation = reservationMapper.selectById(id);
        if (reservation == null) {
            throw new RuntimeException("预约不存在");
        }
        
        if (!ReservationStatus.PENDING.name().equals(reservation.getStatus())) {
            throw new RuntimeException("该预约已审批，无法重复操作");
        }
        
        reservation.setApprovalUserId(approvalUserId);
        reservation.setApprovalTime(LocalDateTime.now());
        reservation.setApprovalRemark(remark);
        reservation.setStatus(approved ? ReservationStatus.APPROVED.name() : ReservationStatus.REJECTED.name());
        
        reservationMapper.updateById(reservation);
        
        // 如果是多次预约的父预约，同步更新所有子预约
        if (reservation.getParentId() == null && ReservationType.MULTIPLE.name().equals(reservation.getType())) {
            LambdaQueryWrapper<Reservation> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(Reservation::getParentId, id);
            List<Reservation> childReservations = reservationMapper.selectList(wrapper);
            
            for (Reservation child : childReservations) {
                child.setStatus(reservation.getStatus());
                child.setApprovalUserId(approvalUserId);
                child.setApprovalTime(LocalDateTime.now());
                reservationMapper.updateById(child);
            }
        }
        
        log.info("预约审批成功: id={}, status={}", id, reservation.getStatus());
        return reservation;
    }
    
    /**
     * 取消预约
     */
    @Transactional(rollbackFor = Exception.class)
    public Reservation cancelReservation(Long id, Long userId) {
        log.info("取消预约: id={}, userId={}", id, userId);
        
        Reservation reservation = reservationMapper.selectById(id);
        if (reservation == null) {
            throw new RuntimeException("预约不存在");
        }
        
        if (!reservation.getUserId().equals(userId)) {
            throw new RuntimeException("只能取消自己的预约");
        }
        
        if (ReservationStatus.COMPLETED.name().equals(reservation.getStatus()) ||
            ReservationStatus.CANCELLED.name().equals(reservation.getStatus())) {
            throw new RuntimeException("该预约已完成或已取消");
        }
        
        reservation.setStatus(ReservationStatus.CANCELLED.name());
        reservationMapper.updateById(reservation);
        
        log.info("预约取消成功: id={}", id);
        return reservation;
    }
    
    /**
     * 签到
     */
    @Transactional(rollbackFor = Exception.class)
    public Reservation checkIn(Long id, Long userId) {
        log.info("签到: id={}, userId={}", id, userId);
        
        Reservation reservation = reservationMapper.selectById(id);
        if (reservation == null) {
            throw new RuntimeException("预约不存在");
        }
        
        if (!reservation.getUserId().equals(userId)) {
            throw new RuntimeException("只能为自己的预约签到");
        }
        
        if (!ReservationStatus.APPROVED.name().equals(reservation.getStatus())) {
            throw new RuntimeException("预约未通过审批，无法签到");
        }
        
        reservation.setCheckInTime(LocalDateTime.now());
        reservationMapper.updateById(reservation);
        
        log.info("签到成功: id={}", id);
        return reservation;
    }
    
    /**
     * 签退
     */
    @Transactional(rollbackFor = Exception.class)
    public Reservation checkOut(Long id, Long userId) {
        log.info("签退: id={}, userId={}", id, userId);
        
        Reservation reservation = reservationMapper.selectById(id);
        if (reservation == null) {
            throw new RuntimeException("预约不存在");
        }
        
        if (!reservation.getUserId().equals(userId)) {
            throw new RuntimeException("只能为自己的预约签退");
        }
        
        if (reservation.getCheckInTime() == null) {
            throw new RuntimeException("请先签到");
        }
        
        reservation.setCheckOutTime(LocalDateTime.now());
        reservation.setStatus(ReservationStatus.COMPLETED.name());
        reservationMapper.updateById(reservation);
        
        log.info("签退成功: id={}", id);
        return reservation;
    }
    
    /**
     * 获取用户的预约列表
     */
    public Page<Reservation> getUserReservations(Long userId, Integer current, Integer size) {
        log.info("查询用户预约: userId={}", userId);
        
        Page<Reservation> page = new Page<>(current, size);
        LambdaQueryWrapper<Reservation> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Reservation::getUserId, userId)
               .orderByDesc(Reservation::getCreatedAt);
        
        return reservationMapper.selectPage(page, wrapper);
    }
}

