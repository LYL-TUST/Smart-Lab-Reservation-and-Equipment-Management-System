package com.lab.management.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.common.Result;
import com.lab.management.dto.ReservationDTO;
import com.lab.management.dto.ReservationQueryDTO;
import com.lab.management.dto.ReservationVO;
import com.lab.management.entity.Laboratory;
import com.lab.management.entity.Reservation;
import com.lab.management.security.UserDetailsImpl;
import com.lab.management.service.LaboratoryService;
import com.lab.management.service.ReservationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;

/**
 * 预约控制器
 */
@Slf4j
@RestController
@RequestMapping("/reservation")
@RequiredArgsConstructor
public class ReservationController {
    
    private final ReservationService reservationService;
    private final LaboratoryService laboratoryService;
    
    /**
     * 分页查询预约
     */
    @GetMapping("/page")
    public Result<Page<ReservationVO>> page(ReservationQueryDTO queryDTO) {
        Page<Reservation> page = reservationService.page(queryDTO);
        
        // 转换为VO并填充实验室名称
        Page<ReservationVO> voPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        voPage.setRecords(page.getRecords().stream().map(reservation -> {
            ReservationVO vo = ReservationVO.from(reservation);
            if (reservation.getLabId() != null) {
                Laboratory laboratory = laboratoryService.getById(reservation.getLabId());
                if (laboratory != null) {
                    vo.setLaboratoryName(laboratory.getName());
                }
            }
            return vo;
        }).collect(java.util.stream.Collectors.toList()));
        
        return Result.success(voPage);
    }
    
    /**
     * 查询预约详情
     */
    @GetMapping("/{id}")
    public Result<Reservation> getById(@PathVariable Long id) {
        Reservation reservation = reservationService.getById(id);
        if (reservation == null) {
            return Result.error("预约不存在");
        }
        return Result.success(reservation);
    }
    
    /**
     * 创建单次预约
     */
    @PostMapping("/single")
    public Result<Reservation> createSingle(
            @Validated @RequestBody ReservationDTO dto,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            log.info("收到创建预约请求: labId={}, startTime={}, endTime={}, type={}, purpose={}, participantCount={}", 
                dto.getLabId(), dto.getStartTime(), dto.getEndTime(), dto.getType(), dto.getPurpose(), dto.getParticipantCount());
            
            // 验证数据
            if (dto.getLabId() == null) {
                return Result.error("实验室不能为空");
            }
            if (dto.getStartTime() == null) {
                return Result.error("开始时间不能为空");
            }
            if (dto.getEndTime() == null) {
                return Result.error("结束时间不能为空");
            }
            if (dto.getStartTime().isAfter(dto.getEndTime())) {
                return Result.error("开始时间不能晚于结束时间");
            }
            
            Reservation reservation = reservationService.createSingleReservation(dto, userDetails.getId());
            return Result.success("预约创建成功，等待审批", reservation);
        } catch (Exception e) {
            log.error("创建单次预约失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 创建多次预约
     */
    @PostMapping("/multiple")
    public Result<List<Reservation>> createMultiple(
            @Validated @RequestBody ReservationDTO dto,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            List<Reservation> reservations = reservationService.createMultipleReservation(dto, userDetails.getId());
            return Result.success("批量预约创建成功，等待审批", reservations);
        } catch (Exception e) {
            log.error("创建多次预约失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 创建课程绑定预约（仅教师和管理员）
     */
    @PostMapping("/course")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public Result<List<Reservation>> createCourse(
            @Validated @RequestBody ReservationDTO dto,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            List<Reservation> reservations = reservationService.createCourseReservation(dto, userDetails.getId());
            return Result.success("课程预约创建成功", reservations);
        } catch (Exception e) {
            log.error("创建课程预约失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 审批预约（教师和管理员）
     */
    @PutMapping("/{id}/approve")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public Result<Reservation> approve(
            @PathVariable Long id,
            @RequestParam boolean approved,
            @RequestParam(required = false) String remark,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            Reservation reservation = reservationService.approveReservation(id, userDetails.getId(), remark, approved);
            return Result.success(approved ? "审批通过" : "审批拒绝", reservation);
        } catch (Exception e) {
            log.error("审批预约失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 取消预约
     */
    @PutMapping("/{id}/cancel")
    public Result<Reservation> cancel(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            Reservation reservation = reservationService.cancelReservation(id, userDetails.getId());
            return Result.success("预约已取消", reservation);
        } catch (Exception e) {
            log.error("取消预约失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 签到
     */
    @PutMapping("/{id}/checkin")
    public Result<Reservation> checkIn(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            Reservation reservation = reservationService.checkIn(id, userDetails.getId());
            return Result.success("签到成功", reservation);
        } catch (Exception e) {
            log.error("签到失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 签退
     */
    @PutMapping("/{id}/checkout")
    public Result<Reservation> checkOut(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            Reservation reservation = reservationService.checkOut(id, userDetails.getId());
            return Result.success("签退成功", reservation);
        } catch (Exception e) {
            log.error("签退失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 更新预约（仅限待审核状态）
     */
    @PutMapping("/{id}")
    public Result<Reservation> update(
            @PathVariable Long id,
            @Validated @RequestBody ReservationDTO dto,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        try {
            Reservation reservation = reservationService.updateReservation(id, dto, userDetails.getId());
            return Result.success("预约更新成功", reservation);
        } catch (Exception e) {
            log.error("更新预约失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 获取当前用户的预约列表
     */
    @GetMapping("/my")
    public Result<Page<Reservation>> getMyReservations(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @AuthenticationPrincipal UserDetailsImpl userDetails) {
        
        Page<Reservation> page = reservationService.getUserReservations(userDetails.getId(), current, size);
        return Result.success(page);
    }
    
    /**
     * 获取日历视图的预约数据
     */
    @GetMapping("/calendar")
    public Result<List<com.lab.management.dto.CalendarReservationDTO>> getCalendarReservations(
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end,
            @RequestParam(required = false) Long labId,
            @RequestParam(required = false) String status) {
        try {
            List<com.lab.management.dto.CalendarReservationDTO> events = 
                reservationService.getCalendarReservations(start, end, labId, status);
            return Result.success(events);
        } catch (Exception e) {
            log.error("获取日历预约数据失败", e);
            return Result.error(e.getMessage());
        }
    }
}

