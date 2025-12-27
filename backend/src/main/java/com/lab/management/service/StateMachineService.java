package com.lab.management.service;

import com.lab.management.enums.EquipmentStatus;
import com.lab.management.enums.LabStatus;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * 状态机服务 - 管理资源状态转换
 */
@Slf4j
@Service
public class StateMachineService {
    
    /**
     * 验证实验室状态转换是否合法
     */
    public boolean validateLabStatusTransition(LabStatus currentStatus, LabStatus targetStatus) {
        if (currentStatus == null || targetStatus == null) {
            log.error("状态不能为空");
            return false;
        }
        
        if (currentStatus == targetStatus) {
            log.warn("目标状态与当前状态相同: {}", currentStatus);
            return true;
        }
        
        boolean canTransition = currentStatus.canTransitionTo(targetStatus);
        if (!canTransition) {
            log.error("实验室状态转换非法: {} -> {}", currentStatus, targetStatus);
        }
        
        return canTransition;
    }
    
    /**
     * 验证设备状态转换是否合法
     */
    public boolean validateEquipmentStatusTransition(EquipmentStatus currentStatus, EquipmentStatus targetStatus) {
        if (currentStatus == null || targetStatus == null) {
            log.error("状态不能为空");
            return false;
        }
        
        if (currentStatus == targetStatus) {
            log.warn("目标状态与当前状态相同: {}", currentStatus);
            return true;
        }
        
        boolean canTransition = currentStatus.canTransitionTo(targetStatus);
        if (!canTransition) {
            log.error("设备状态转换非法: {} -> {}", currentStatus, targetStatus);
        }
        
        return canTransition;
    }
    
    /**
     * 获取实验室状态转换失败原因
     */
    public String getLabStatusTransitionErrorMessage(LabStatus currentStatus, LabStatus targetStatus) {
        if (currentStatus == null || targetStatus == null) {
            return "状态不能为空";
        }
        
        if (currentStatus == targetStatus) {
            return "目标状态与当前状态相同";
        }
        
        return String.format("不允许从 %s 转换到 %s", 
            currentStatus.getDescription(), targetStatus.getDescription());
    }
    
    /**
     * 获取设备状态转换失败原因
     */
    public String getEquipmentStatusTransitionErrorMessage(EquipmentStatus currentStatus, EquipmentStatus targetStatus) {
        if (currentStatus == null || targetStatus == null) {
            return "状态不能为空";
        }
        
        if (currentStatus == targetStatus) {
            return "目标状态与当前状态相同";
        }
        
        if (currentStatus == EquipmentStatus.SCRAPPED) {
            return "设备已报废，无法转换状态";
        }
        
        return String.format("不允许从 %s 转换到 %s", 
            currentStatus.getDescription(), targetStatus.getDescription());
    }
    
    /**
     * 根据预约状态自动更新实验室状态
     */
    public LabStatus getLabStatusByReservation(String reservationStatus) {
        switch (reservationStatus) {
            case "APPROVED":
                return LabStatus.RESERVED;
            case "COMPLETED":
            case "CANCELLED":
            case "REJECTED":
                return LabStatus.IDLE;
            default:
                return null;
        }
    }
    
    /**
     * 根据预约状态自动更新设备状态
     */
    public EquipmentStatus getEquipmentStatusByReservation(String reservationStatus) {
        switch (reservationStatus) {
            case "APPROVED":
                return EquipmentStatus.RESERVED;
            case "COMPLETED":
            case "CANCELLED":
            case "REJECTED":
                return EquipmentStatus.IDLE;
            default:
                return null;
        }
    }
}

