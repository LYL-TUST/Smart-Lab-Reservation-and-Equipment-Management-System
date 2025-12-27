package com.lab.management.controller;

import com.lab.management.common.Result;
import com.lab.management.service.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * 仪表盘控制器
 */
@Slf4j
@RestController
@RequestMapping("/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final ReservationService reservationService;
    private final LaboratoryService laboratoryService;
    private final EquipmentService equipmentService;
    private final UserService userService;

    /**
     * 获取统计数据
     */
    @GetMapping("/stats")
    public Result<Map<String, Object>> getStats() {
        try {
            Map<String, Object> stats = new HashMap<>();
            
            // 总预约数
            long totalReservations = reservationService.count();
            stats.put("totalReservations", totalReservations);
            
            // 实验室数量
            long totalLabs = laboratoryService.count();
            stats.put("totalLabs", totalLabs);
            
            // 设备总数
            long totalEquipment = equipmentService.count();
            stats.put("totalEquipment", totalEquipment);
            
            // 活跃用户数（状态为1的用户）
            long activeUsers = userService.countActive();
            stats.put("activeUsers", activeUsers);
            
            log.info("获取统计数据: reservations={}, labs={}, equipment={}, users={}", 
                totalReservations, totalLabs, totalEquipment, activeUsers);
            
            return Result.success(stats);
        } catch (Exception e) {
            log.error("获取统计数据失败", e);
            return Result.error(e.getMessage());
        }
    }
}

